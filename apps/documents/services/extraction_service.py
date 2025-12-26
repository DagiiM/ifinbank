"""Document extraction service."""
import logging
from typing import Dict, Any
from ..models import Document, DocumentExtraction
from .ocr_service import OCRService

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Service for managing document extraction workflow.
    
    Coordinates OCR processing and stores results.
    """
    
    # Field mappings for different document types
    FIELD_MAPPINGS = {
        'national_id': {
            'full_name': ['name', 'full name', 'names'],
            'id_number': ['id no', 'id number', 'id'],
            'date_of_birth': ['date of birth', 'dob', 'birth date'],
            'gender': ['sex', 'gender'],
        },
        'passport': {
            'full_name': ['name', 'given names', 'surname'],
            'passport_number': ['passport no', 'passport number'],
            'date_of_birth': ['date of birth', 'dob'],
            'nationality': ['nationality', 'country'],
            'expiry_date': ['expiry', 'date of expiry'],
        },
        'drivers_license': {
            'full_name': ['name', 'holder name'],
            'license_number': ['license no', 'dl no'],
            'date_of_birth': ['date of birth', 'dob'],
            'expiry_date': ['expiry', 'valid until'],
        },
        'application_form': {
            'full_name': ['name', 'full name', 'applicant name'],
            'id_number': ['id no', 'national id', 'id number'],
            'date_of_birth': ['date of birth', 'dob'],
            'phone': ['phone', 'mobile', 'tel', 'telephone'],
            'email': ['email', 'e-mail'],
            'address': ['address', 'postal address', 'residential address'],
            'signature': ['signature'],
        },
    }
    
    def __init__(self, ocr_service: OCRService = None):
        """
        Initialize extraction service.
        
        Args:
            ocr_service: OCR service instance (created if not provided)
        """
        self.ocr_service = ocr_service or OCRService()
    
    def process_document(self, document: Document) -> DocumentExtraction:
        """
        Process a document and extract data.
        
        Args:
            document: Document to process
            
        Returns:
            DocumentExtraction with results
        """
        logger.info(f"Processing document {document.id} ({document.document_type})")
        
        try:
            # Get appropriate field mappings
            mappings = self.FIELD_MAPPINGS.get(
                document.document_type,
                self.FIELD_MAPPINGS.get('application_form', {})
            )
            
            # Run OCR
            ocr_result = self.ocr_service.extract_text(document)
            
            if not ocr_result.success:
                document.processing_error = ocr_result.error
                document.save(update_fields=['processing_error', 'updated_at'])
                raise Exception(ocr_result.error)
            
            # Extract fields
            structured_data = ocr_result.structured_data or {}
            if not structured_data:
                # Fall back to pattern extraction
                structured_data = self.ocr_service.extract_fields(document, mappings)
            
            # Calculate confidence scores per field
            confidence_scores = {}
            for field in structured_data:
                # Use overall confidence as default
                confidence_scores[field] = ocr_result.confidence
            
            # Create extraction record
            extraction = DocumentExtraction.objects.create(
                document=document,
                raw_text=ocr_result.text,
                structured_data=structured_data,
                confidence_scores=confidence_scores,
                overall_confidence=ocr_result.confidence,
                processing_time=ocr_result.processing_time,
                extraction_method='ocr',
            )
            
            # Mark document as processed
            document.is_processed = True
            document.processing_error = ''
            document.save(update_fields=['is_processed', 'processing_error', 'updated_at'])
            
            logger.info(
                f"Document {document.id} processed successfully. "
                f"Extracted {len(structured_data)} fields."
            )
            
            return extraction
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            document.is_processed = False
            document.processing_error = str(e)
            document.save(update_fields=['is_processed', 'processing_error', 'updated_at'])
            raise
    
    def process_all_documents(self, verification_request) -> int:
        """
        Process all documents for a verification request.
        
        Args:
            verification_request: VerificationRequest instance
            
        Returns:
            Number of documents successfully processed
        """
        documents = verification_request.documents.filter(is_processed=False)
        processed = 0
        
        for document in documents:
            try:
                self.process_document(document)
                processed += 1
            except Exception as e:
                logger.warning(f"Failed to process document {document.id}: {e}")
                continue
        
        return processed
    
    def reprocess_document(self, document: Document) -> DocumentExtraction:
        """
        Reprocess a document (e.g., with new OCR model).
        
        Deletes existing extractions and creates new ones.
        """
        # Delete existing extractions
        document.extractions.all().delete()
        
        # Reset processing status
        document.is_processed = False
        document.processing_error = ''
        document.save(update_fields=['is_processed', 'processing_error', 'updated_at'])
        
        # Process again
        return self.process_document(document)
    
    def validate_extraction(self, extraction: DocumentExtraction) -> Dict[str, Any]:
        """
        Validate extracted data quality.
        
        Returns validation results with any issues found.
        """
        issues = []
        
        # Check required fields based on document type
        doc_type = extraction.document.document_type
        required_fields = self._get_required_fields(doc_type)
        
        for field in required_fields:
            if field not in extraction.structured_data:
                issues.append({
                    'field': field,
                    'issue': 'missing',
                    'message': f'Required field "{field}" not extracted'
                })
            elif not extraction.structured_data[field]:
                issues.append({
                    'field': field,
                    'issue': 'empty',
                    'message': f'Field "{field}" is empty'
                })
        
        # Check confidence scores
        low_confidence_fields = [
            field for field, conf in extraction.confidence_scores.items()
            if conf < 0.7
        ]
        for field in low_confidence_fields:
            issues.append({
                'field': field,
                'issue': 'low_confidence',
                'message': f'Low confidence ({extraction.confidence_scores[field]:.0%}) for "{field}"'
            })
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'fields_extracted': len(extraction.structured_data),
            'overall_confidence': float(extraction.overall_confidence),
        }
    
    def _get_required_fields(self, doc_type: str) -> list:
        """Get required fields for a document type."""
        required = {
            'national_id': ['full_name', 'id_number'],
            'passport': ['full_name', 'passport_number'],
            'drivers_license': ['full_name', 'license_number'],
            'application_form': ['full_name'],
        }
        return required.get(doc_type, [])
