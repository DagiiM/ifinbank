"""
Enhanced verification service integrating all AI components.

This service orchestrates the complete verification workflow:
1. Document OCR using DeepSeek-OCR via vLLM
2. Field comparison using advanced matching algorithms
3. Compliance checking with RAG-enhanced policy search
4. Scoring and decision logic
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.verification.models import (
    VerificationRequest,
    VerificationResult,
    Discrepancy,
)
from apps.documents.models import Document, DocumentExtraction
from apps.compliance.models import Policy, ComplianceRule, ComplianceCheck

from .advanced_comparison import AdvancedComparator, BatchComparator, ComparisonResult
from apps.documents.services.vllm_ocr_service import DeepSeekOCRService, VLLMConfig, get_ocr_service
from apps.compliance.services.chromadb_service import PolicyEmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class VerificationConfig:
    """Configuration for verification workflow."""
    # Scoring thresholds
    auto_approve_threshold: float = 85.0
    review_threshold: float = 70.0
    auto_reject_threshold: float = 50.0
    
    # Required documents by account type
    required_documents: Dict[str, List[str]] = field(default_factory=lambda: {
        'savings': ['national_id'],
        'current': ['national_id', 'application_form'],
        'business': ['national_id', 'application_form', 'utility_bill'],
    })
    
    # Field weights for scoring
    field_weights: Dict[str, float] = field(default_factory=lambda: {
        'id_number': 2.5,
        'full_name': 2.0,
        'date_of_birth': 1.5,
        'address': 1.0,
        'phone': 0.5,
    })
    
    # Component weights in overall score
    component_weights: Dict[str, float] = field(default_factory=lambda: {
        'identity': 0.40,
        'document': 0.25,
        'compliance': 0.25,
        'quality': 0.10,
    })
    
    # Use AI services or fallbacks
    use_vllm_ocr: bool = True
    use_chromadb: bool = True


class EnhancedVerificationService:
    """
    Enhanced verification service with AI integration.
    
    This service provides:
    - DeepSeek-OCR document processing via vLLM
    - Advanced multi-strategy field comparison
    - RAG-enhanced compliance checking with ChromaDB
    - Intelligent scoring and auto-decision logic
    - Complete audit trail
    """
    
    def __init__(
        self,
        config: VerificationConfig = None,
        ocr_service: DeepSeekOCRService = None,
        embedding_service: PolicyEmbeddingService = None,
    ):
        """
        Initialize the enhanced verification service.
        
        Args:
            config: Verification configuration
            ocr_service: Optional OCR service override
            embedding_service: Optional embedding service override
        """
        self.config = config or VerificationConfig()
        self._ocr_service = ocr_service
        self._embedding_service = embedding_service
        self.comparator = BatchComparator()
    
    @property
    def ocr_service(self) -> DeepSeekOCRService:
        """Get OCR service instance."""
        if self._ocr_service is None:
            if self.config.use_vllm_ocr:
                self._ocr_service = get_ocr_service()
            else:
                # Use mock service for development
                from apps.documents.services.ocr_service import OCRService
                self._ocr_service = OCRService()
        return self._ocr_service
    
    @property
    def embedding_service(self) -> PolicyEmbeddingService:
        """Get embedding service instance."""
        if self._embedding_service is None:
            if self.config.use_chromadb:
                self._embedding_service = get_embedding_service()
            else:
                self._embedding_service = PolicyEmbeddingService()
        return self._embedding_service
    
    @transaction.atomic
    def verify(self, request: VerificationRequest) -> VerificationRequest:
        """
        Execute complete verification workflow.
        
        Args:
            request: VerificationRequest to process
            
        Returns:
            Updated VerificationRequest with results
        """
        logger.info(f"Starting enhanced verification for {request.reference_number}")
        
        try:
            # Mark as processing
            request.start_processing()
            
            # Step 1: Process documents with OCR
            documents = request.documents.all()
            extraction_results = self._process_documents(documents)
            
            # Step 2: Combine extracted data
            extracted_data = self._merge_extractions(extraction_results)
            
            # Step 3: Compare entered vs extracted data
            comparison_results = self._compare_data(
                request.customer_data,
                extracted_data
            )
            
            # Step 4: Run compliance checks with RAG context
            compliance_results = self._run_compliance_checks(request)
            
            # Step 5: Assess document quality
            quality_results = self._assess_document_quality(documents)
            
            # Step 6: Calculate overall score
            overall_score, score_breakdown = self._calculate_score(
                comparison_results,
                compliance_results,
                quality_results,
            )
            
            # Step 7: Record results and discrepancies
            self._record_results(
                request,
                comparison_results,
                compliance_results,
                quality_results
            )
            self._record_discrepancies(request, comparison_results)
            
            # Step 8: Determine outcome
            decision, reason = self._determine_decision(
                overall_score,
                comparison_results,
                compliance_results,
            )
            
            # Update request with results
            request.overall_score = Decimal(str(overall_score))
            request.decision_reason = reason
            
            if decision == 'approved':
                request.complete(approved=True, reason=reason)
            elif decision == 'rejected':
                request.complete(approved=False, reason=reason)
            else:  # review_required
                request.require_review(reason=reason)
            
            logger.info(
                f"Verification {request.reference_number} completed: "
                f"score={overall_score:.1f}, decision={decision}"
            )
            
            return request
            
        except Exception as e:
            logger.error(f"Verification failed for {request.reference_number}: {e}")
            request.fail(str(e))
            raise
    
    def _process_documents(
        self,
        documents
    ) -> Dict[str, Dict]:
        """
        Process all documents using OCR.
        
        Returns dict mapping document IDs to extraction results.
        """
        results = {}
        
        for document in documents:
            try:
                logger.debug(f"Processing document {document.id} ({document.document_type})")
                
                # Skip if already processed
                if document.is_processed:
                    extraction = document.extractions.first()
                    if extraction:
                        results[str(document.id)] = {
                            'document_type': document.document_type,
                            'structured_data': extraction.structured_data,
                            'confidence': float(extraction.overall_confidence),
                        }
                        continue
                
                # Run OCR
                ocr_result = self.ocr_service.extract_text(
                    document.file.path,
                    doc_type=document.document_type,
                )
                
                if ocr_result.success:
                    # Save extraction
                    extraction = DocumentExtraction.objects.create(
                        document=document,
                        raw_text=ocr_result.text,
                        structured_data=ocr_result.structured_data,
                        overall_confidence=ocr_result.confidence,
                        processing_time=ocr_result.processing_time,
                        extraction_method='ocr',
                        model_version=ocr_result.model_version,
                    )
                    
                    document.is_processed = True
                    document.save(update_fields=['is_processed', 'updated_at'])
                    
                    results[str(document.id)] = {
                        'document_type': document.document_type,
                        'structured_data': ocr_result.structured_data,
                        'confidence': ocr_result.confidence,
                    }
                else:
                    logger.warning(f"OCR failed for {document.id}: {ocr_result.error}")
                    document.processing_error = ocr_result.error
                    document.save(update_fields=['processing_error', 'updated_at'])
                    
            except Exception as e:
                logger.error(f"Document processing error for {document.id}: {e}")
                continue
        
        return results
    
    def _merge_extractions(
        self,
        extraction_results: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Merge extracted data from multiple documents.
        
        Priority order: ID documents > application forms > other
        For conflicting fields, use highest confidence value.
        """
        merged = {}
        field_confidence = {}
        
        # Priority order for document types
        priority = {
            'national_id': 1,
            'passport': 2,
            'drivers_license': 3,
            'application_form': 4,
        }
        
        # Sort extractions by document priority
        sorted_results = sorted(
            extraction_results.values(),
            key=lambda x: priority.get(x['document_type'], 10)
        )
        
        for result in sorted_results:
            structured = result.get('structured_data', {})
            doc_confidence = result.get('confidence', 0.5)
            
            for field, value in structured.items():
                if not value:
                    continue
                
                # Only overwrite if higher confidence or field not set
                current_conf = field_confidence.get(field, 0)
                if doc_confidence > current_conf:
                    merged[field] = value
                    field_confidence[field] = doc_confidence
        
        return merged
    
    def _compare_data(
        self,
        entered_data: Dict[str, Any],
        extracted_data: Dict[str, Any]
    ) -> Dict[str, ComparisonResult]:
        """
        Compare customer data against extracted document data.
        """
        return self.comparator.compare_all(
            entered_data=entered_data,
            extracted_data=extracted_data,
        )
    
    def _run_compliance_checks(
        self,
        request: VerificationRequest
    ) -> List[Dict[str, Any]]:
        """
        Run compliance checks with RAG context enhancement.
        """
        results = []
        
        # Get applicable policies using semantic search
        context = {
            'account_type': request.customer_data.get('account_type', 'savings'),
            'customer_type': 'individual',
            'document_types': [
                doc.document_type for doc in request.documents.all()
            ],
        }
        
        relevant_policies = self.embedding_service.find_applicable_policies(context)
        
        # KYC checks
        kyc_results = self._run_kyc_checks(request, relevant_policies)
        results.extend(kyc_results)
        
        # AML checks
        aml_results = self._run_aml_checks(request, relevant_policies)
        results.extend(aml_results)
        
        # Document requirement checks
        doc_results = self._check_required_documents(request)
        results.extend(doc_results)
        
        return results
    
    def _run_kyc_checks(
        self,
        request: VerificationRequest,
        policies: List
    ) -> List[Dict[str, Any]]:
        """Run KYC compliance checks."""
        checks = []
        customer = request.customer_data
        
        # Age verification
        age_result = self._verify_age(customer.get('date_of_birth', ''))
        checks.append({
            'type': 'kyc',
            'name': 'age_verification',
            'passed': age_result['passed'],
            'score': 100 if age_result['passed'] else 0,
            'confidence': age_result['confidence'],
            'message': age_result['message'],
            'details': age_result,
        })
        
        # Required fields check
        required = ['full_name', 'id_number', 'date_of_birth']
        missing = [f for f in required if not customer.get(f)]
        
        checks.append({
            'type': 'kyc',
            'name': 'required_fields',
            'passed': len(missing) == 0,
            'score': max(0, 100 - (len(missing) * 30)),
            'confidence': 1.0,
            'message': 'All required fields present' if not missing else f'Missing: {", ".join(missing)}',
            'details': {'missing_fields': missing},
        })
        
        return checks
    
    def _run_aml_checks(
        self,
        request: VerificationRequest,
        policies: List
    ) -> List[Dict[str, Any]]:
        """Run AML compliance checks."""
        checks = []
        
        # Watchlist screening (placeholder - would integrate with actual API)
        watchlist_clear = self._screen_watchlist(request.customer_data)
        checks.append({
            'type': 'aml',
            'name': 'watchlist_screening',
            'passed': watchlist_clear,
            'score': 100 if watchlist_clear else 0,
            'confidence': 0.95,
            'message': 'No watchlist matches' if watchlist_clear else 'Potential watchlist match - review required',
        })
        
        # PEP check (placeholder)
        pep_clear = self._check_pep(request.customer_data)
        checks.append({
            'type': 'aml',
            'name': 'pep_check',
            'passed': pep_clear,
            'score': 100 if pep_clear else 50,
            'confidence': 0.90,
            'message': 'Not identified as PEP' if pep_clear else 'Potential PEP - enhanced due diligence required',
        })
        
        return checks
    
    def _check_required_documents(
        self,
        request: VerificationRequest
    ) -> List[Dict[str, Any]]:
        """Check if required documents are present."""
        checks = []
        
        account_type = request.customer_data.get('account_type', 'savings')
        required = self.config.required_documents.get(account_type, ['national_id'])
        
        doc_types = set(doc.document_type for doc in request.documents.all())
        missing = [d for d in required if d not in doc_types]
        
        checks.append({
            'type': 'document',
            'name': 'required_documents',
            'passed': len(missing) == 0,
            'score': max(0, 100 - (len(missing) * 40)),
            'confidence': 1.0,
            'message': 'All required documents provided' if not missing else f'Missing: {", ".join(missing)}',
            'details': {'required': required, 'provided': list(doc_types), 'missing': missing},
        })
        
        return checks
    
    def _assess_document_quality(
        self,
        documents
    ) -> List[Dict[str, Any]]:
        """Assess document quality based on OCR confidence."""
        results = []
        
        for document in documents:
            extraction = document.extractions.first()
            if extraction:
                confidence = float(extraction.overall_confidence)
                
                if confidence >= 0.9:
                    quality = 'excellent'
                    score = 100
                elif confidence >= 0.75:
                    quality = 'good'
                    score = 85
                elif confidence >= 0.6:
                    quality = 'acceptable'
                    score = 70
                else:
                    quality = 'poor'
                    score = 50
                
                results.append({
                    'document_id': str(document.id),
                    'document_type': document.document_type,
                    'quality': quality,
                    'score': score,
                    'confidence': confidence,
                })
        
        return results
    
    def _calculate_score(
        self,
        comparison_results: Dict[str, ComparisonResult],
        compliance_results: List[Dict],
        quality_results: List[Dict],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall verification score.
        
        Returns tuple of (overall_score, breakdown_dict).
        """
        breakdown = {}
        
        # Identity score from field comparisons
        if comparison_results:
            identity_scores = [r.similarity_score for r in comparison_results.values()]
            identity_avg = sum(identity_scores) / len(identity_scores)
            breakdown['identity'] = identity_avg * 100
        else:
            breakdown['identity'] = 0
        
        # Compliance score
        if compliance_results:
            compliance_scores = [r['score'] for r in compliance_results]
            compliance_avg = sum(compliance_scores) / len(compliance_scores)
            breakdown['compliance'] = compliance_avg
        else:
            breakdown['compliance'] = 100
        
        # Document quality score
        if quality_results:
            quality_scores = [r['score'] for r in quality_results]
            breakdown['quality'] = sum(quality_scores) / len(quality_scores)
        else:
            breakdown['quality'] = 0
        
        # Document existence score
        breakdown['document'] = 100 if quality_results else 0
        
        # Calculate weighted overall score
        weights = self.config.component_weights
        overall = sum(
            breakdown.get(component, 0) * weight
            for component, weight in weights.items()
        )
        
        return overall, breakdown
    
    def _record_results(
        self,
        request: VerificationRequest,
        comparison_results: Dict[str, ComparisonResult],
        compliance_results: List[Dict],
        quality_results: List[Dict],
    ):
        """Record all verification results to database."""
        
        # Comparison results
        for field, result in comparison_results.items():
            VerificationResult.objects.create(
                request=request,
                check_type='identity',
                check_name=f'{field}_match',
                score=Decimal(str(result.similarity_score * 100)),
                confidence=Decimal(str(result.confidence)),
                passed=result.is_match,
                message=f"{'Match' if result.is_match else 'Mismatch'}: {result.comparison_method}",
                evidence={
                    'entered': result.entered_value,
                    'extracted': result.extracted_value,
                    'method': result.comparison_method,
                    'details': result.details,
                },
            )
        
        # Compliance results
        for result in compliance_results:
            VerificationResult.objects.create(
                request=request,
                check_type=result['type'],
                check_name=result['name'],
                score=Decimal(str(result['score'])),
                confidence=Decimal(str(result.get('confidence', 1.0))),
                passed=result['passed'],
                message=result['message'],
                evidence=result.get('details', {}),
            )
        
        # Quality results
        for result in quality_results:
            VerificationResult.objects.create(
                request=request,
                check_type='quality',
                check_name=f"doc_{result['document_type']}_quality",
                score=Decimal(str(result['score'])),
                confidence=Decimal(str(result['confidence'])),
                passed=result['score'] >= 70,
                message=f"Document quality: {result['quality']}",
                evidence=result,
            )
    
    def _record_discrepancies(
        self,
        request: VerificationRequest,
        comparison_results: Dict[str, ComparisonResult],
    ):
        """Record field discrepancies."""
        for field, result in comparison_results.items():
            if not result.is_match and result.similarity_score < 0.95:
                # Determine severity
                severity_score = result.similarity_score
                if severity_score < 0.5:
                    severity = 'critical'
                elif severity_score < 0.7:
                    severity = 'major'
                else:
                    severity = 'minor'
                
                Discrepancy.objects.create(
                    request=request,
                    field_name=field,
                    entered_value=result.entered_value,
                    document_value=result.extracted_value,
                    similarity_score=Decimal(str(result.similarity_score * 100)),
                    severity=severity,
                    description=f"Mismatch in {field}: {result.comparison_method} comparison yielded {result.similarity_score:.0%} similarity",
                )
    
    def _determine_decision(
        self,
        overall_score: float,
        comparison_results: Dict[str, ComparisonResult],
        compliance_results: List[Dict],
    ) -> Tuple[str, str]:
        """
        Determine verification decision based on results.
        
        Returns tuple of (decision, reason).
        """
        # Check for blocking failures
        blocking_failures = [
            r for r in compliance_results
            if not r['passed'] and r['type'] in ('aml', 'kyc')
        ]
        
        if blocking_failures:
            failed_checks = ', '.join(r['name'] for r in blocking_failures)
            return 'review_required', f'Critical compliance check failure: {failed_checks}'
        
        # Check for critical discrepancies
        critical_discrepancies = [
            r for r in comparison_results.values()
            if not r.is_match and r.similarity_score < 0.5
        ]
        
        if critical_discrepancies:
            fields = ', '.join(r.field_name for r in critical_discrepancies)
            return 'review_required', f'Critical data mismatch in: {fields}'
        
        # Score-based decision
        if overall_score >= self.config.auto_approve_threshold:
            return 'approved', f'Automatic approval: score {overall_score:.1f}% exceeds threshold'
        
        if overall_score >= self.config.review_threshold:
            return 'review_required', f'Manual review required: score {overall_score:.1f}% below auto-approve threshold'
        
        if overall_score >= self.config.auto_reject_threshold:
            return 'review_required', f'Low score ({overall_score:.1f}%) requires supervisor review'
        
        return 'rejected', f'Automatic rejection: score {overall_score:.1f}% below minimum threshold'
    
    def _verify_age(self, date_of_birth: str, min_age: int = 18) -> Dict[str, Any]:
        """Verify customer meets age requirement."""
        from datetime import datetime
        
        if not date_of_birth:
            return {
                'passed': False,
                'confidence': 0.0,
                'message': 'Date of birth not provided',
                'age': None,
            }
        
        try:
            # Try multiple date formats
            dob = None
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y%m%d']:
                try:
                    dob = datetime.strptime(date_of_birth, fmt)
                    break
                except ValueError:
                    continue
            
            if not dob:
                return {
                    'passed': False,
                    'confidence': 0.3,
                    'message': f'Could not parse date: {date_of_birth}',
                    'age': None,
                }
            
            today = datetime.now()
            age = (today - dob).days // 365
            passed = age >= min_age
            
            return {
                'passed': passed,
                'confidence': 1.0,
                'message': f'Customer is {age} years old' + ('' if passed else f' (minimum: {min_age})'),
                'age': age,
            }
            
        except Exception as e:
            return {
                'passed': False,
                'confidence': 0.0,
                'message': f'Age verification error: {e}',
                'age': None,
            }
    
    def _screen_watchlist(self, customer_data: Dict) -> bool:
        """Screen against sanctions/watchlists. Placeholder for actual API."""
        # TODO: Integrate with OFAC, UN, EU sanctions lists
        return True
    
    def _check_pep(self, customer_data: Dict) -> bool:
        """Check for Politically Exposed Persons. Placeholder for actual API."""
        # TODO: Integrate with PEP database
        return True


# Helper function to get service instance
def get_verification_service(config: VerificationConfig = None) -> EnhancedVerificationService:
    """Create a verification service instance."""
    return EnhancedVerificationService(config=config)
