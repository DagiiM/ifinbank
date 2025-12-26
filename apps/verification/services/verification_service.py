"""Core verification service - Orchestrates the verification workflow."""
from django.utils import timezone
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class VerificationOutcome:
    """Result of a verification process."""
    approved: Optional[bool]
    score: float
    results: List[Dict]
    discrepancies: List[Dict]
    decision_reason: str
    requires_review: bool = False


class VerificationService:
    """
    Service for orchestrating verification workflows.
    
    This is the main entry point for processing verification requests.
    It coordinates document processing, data comparison, and compliance checks.
    """
    
    # Score thresholds
    THRESHOLD_AUTO_APPROVE = 85.0
    THRESHOLD_REVIEW = 70.0
    
    def __init__(self, user=None):
        """
        Initialize the verification service.
        
        Args:
            user: The user performing the verification (for audit trail)
        """
        self.user = user
    
    def create_request(
        self,
        customer_id: str,
        customer_data: dict,
        priority: int = 5,
        account_reference: str = ''
    ):
        """
        Create a new verification request.
        
        Args:
            customer_id: Customer ID from core banking
            customer_data: Customer data snapshot
            priority: Processing priority (1-10)
            account_reference: Optional account reference
            
        Returns:
            VerificationRequest instance
        """
        from ..models import VerificationRequest
        
        request = VerificationRequest.objects.create(
            customer_id=customer_id,
            customer_data=customer_data,
            account_reference=account_reference,
            requested_by=self.user,
            priority=priority,
            status='pending'
        )
        
        logger.info(f"Created verification request {request.reference_number}")
        return request
    
    def process_request(self, request) -> VerificationOutcome:
        """
        Process a verification request through all checks.
        
        This is the main processing pipeline:
        1. Extract data from documents
        2. Compare against customer data
        3. Run compliance checks
        4. Calculate overall score
        5. Determine outcome
        
        Args:
            request: VerificationRequest to process
            
        Returns:
            VerificationOutcome with results
        """
        from .comparison_service import ComparisonService
        from .scoring_service import ScoringService
        from ..models import VerificationResult
        
        logger.info(f"Starting processing for {request.reference_number}")
        
        # Mark as processing
        request.start_processing()
        
        try:
            all_results = []
            all_discrepancies = []
            
            # Step 1: Process documents and extract data
            documents = request.documents.all()
            if documents.exists():
                # Extract and compare document data
                comparison = ComparisonService()
                comparison_results, discrepancies = comparison.compare_all(
                    request.customer_data,
                    documents
                )
                all_results.extend(comparison_results)
                all_discrepancies.extend(discrepancies)
            else:
                # No documents - add a warning result
                result = VerificationResult.objects.create(
                    request=request,
                    check_type='document',
                    check_name='document_presence',
                    score=0,
                    confidence=1.0,
                    passed=False,
                    message='No documents uploaded for verification'
                )
                all_results.append(result)
            
            # Step 2: Run compliance checks
            compliance_results = self._run_compliance_checks(request)
            all_results.extend(compliance_results)
            
            # Step 3: Calculate overall score
            scoring = ScoringService()
            overall_score = scoring.calculate_weighted_score(all_results)
            
            # Step 4: Determine outcome
            outcome = self._determine_outcome(
                overall_score,
                all_results,
                all_discrepancies
            )
            
            # Step 5: Update request with results
            if outcome.requires_review:
                request.require_review(outcome.decision_reason)
            else:
                request.complete(
                    approved=outcome.approved,
                    score=overall_score,
                    reason=outcome.decision_reason
                )
            
            logger.info(
                f"Completed processing for {request.reference_number}: "
                f"score={overall_score:.1f}, approved={outcome.approved}"
            )
            
            return outcome
            
        except Exception as e:
            logger.error(f"Verification failed for {request.reference_number}: {e}")
            request.fail(str(e))
            raise
    
    def _run_compliance_checks(self, request) -> List:
        """Run compliance checks on the request."""
        from ..models import VerificationResult
        
        results = []
        customer = request.customer_data
        
        # KYC: Valid ID document check
        id_docs = request.documents.filter(
            document_type__in=['national_id', 'passport']
        )
        has_valid_id = id_docs.exists()
        
        results.append(VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='kyc_id_document',
            score=100 if has_valid_id else 0,
            confidence=1.0,
            passed=has_valid_id,
            message='Valid ID document provided' if has_valid_id else 'No valid ID document found'
        ))
        
        # KYC: Required fields check
        required_fields = ['full_name', 'id_number', 'date_of_birth']
        missing_fields = [f for f in required_fields if not customer.get(f)]
        fields_complete = len(missing_fields) == 0
        
        results.append(VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='kyc_required_fields',
            score=100 if fields_complete else (100 - len(missing_fields) * 20),
            confidence=1.0,
            passed=fields_complete,
            message='All required fields present' if fields_complete else f'Missing fields: {", ".join(missing_fields)}',
            evidence={'missing_fields': missing_fields}
        ))
        
        # Add more compliance checks here...
        
        return results
    
    def _determine_outcome(
        self,
        score: float,
        results: List,
        discrepancies: List
    ) -> VerificationOutcome:
        """
        Determine the verification outcome based on score and results.
        
        Logic:
        - Score >= 85: Auto-approve (if no critical discrepancies)
        - Score 70-85: Manual review required
        - Score < 70: Auto-reject
        """
        # Check for critical discrepancies that block auto-approval
        has_critical = any(
            d.severity == 'critical' and not d.is_resolved
            for d in discrepancies
        )
        
        # Check for any failed checks
        failed_checks = [r for r in results if not r.passed]
        
        if score >= self.THRESHOLD_AUTO_APPROVE and not has_critical:
            return VerificationOutcome(
                approved=True,
                score=score,
                results=[r.to_dict() for r in results],
                discrepancies=[d.to_dict() for d in discrepancies],
                decision_reason="All verification checks passed",
                requires_review=False
            )
        elif score >= self.THRESHOLD_REVIEW:
            reason = "Manual review required"
            if has_critical:
                reason += " - Critical discrepancy detected"
            elif failed_checks:
                reason += f" - {len(failed_checks)} check(s) did not pass"
            
            return VerificationOutcome(
                approved=None,
                score=score,
                results=[r.to_dict() for r in results],
                discrepancies=[d.to_dict() for d in discrepancies],
                decision_reason=reason,
                requires_review=True
            )
        else:
            return VerificationOutcome(
                approved=False,
                score=score,
                results=[r.to_dict() for r in results],
                discrepancies=[d.to_dict() for d in discrepancies],
                decision_reason=f"Verification failed - score {score:.1f}% below threshold",
                requires_review=False
            )
    
    def approve_request(self, request, reason: str = '', user=None):
        """Manually approve a verification request."""
        request.is_approved = True
        request.status = 'completed'
        request.completed_at = timezone.now()
        request.decision_reason = reason or "Manually approved"
        request.reviewed_by = user or self.user
        request.reviewed_at = timezone.now()
        request.save()
        
        logger.info(f"Request {request.reference_number} manually approved by {user}")
    
    def reject_request(self, request, reason: str, user=None):
        """Manually reject a verification request."""
        request.is_approved = False
        request.status = 'completed'
        request.completed_at = timezone.now()
        request.decision_reason = reason
        request.reviewed_by = user or self.user
        request.reviewed_at = timezone.now()
        request.save()
        
        logger.info(f"Request {request.reference_number} manually rejected by {user}")
