"""OCR service for document text extraction."""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of an OCR operation."""
    success: bool
    text: str = ''
    structured_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    error: str = ''
    processing_time: float = 0.0


class OCRService:
    """
    Service for extracting text from documents using OCR.
    
    This service wraps the DeepSeek OCR API (or alternative)
    for document text extraction.
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize OCR service.
        
        Args:
            config: Configuration dictionary with API settings
        """
        self.config = config or {}
        self.api_url = self.config.get(
            'api_url',
            getattr(settings, 'OCR_API_URL', 'http://localhost:8080')
        )
        self.api_key = self.config.get(
            'api_key',
            getattr(settings, 'OCR_API_KEY', '')
        )
        self.timeout = self.config.get('timeout', 60)
    
    def extract_text(self, document) -> OCRResult:
        """
        Extract text from a document.
        
        Args:
            document: Document model instance
            
        Returns:
            OCRResult with extracted text and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting OCR for document {document.id}")
            
            # Get file path
            file_path = document.file.path
            
            # Call OCR API
            result = self._call_ocr_api(file_path, document.document_type)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                success=True,
                text=result.get('text', ''),
                structured_data=result.get('structured', {}),
                confidence=result.get('confidence', 0.0),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"OCR extraction failed for document {document.id}: {e}")
            return OCRResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def extract_fields(
        self,
        document,
        field_mappings: Dict[str, list]
    ) -> Dict[str, Any]:
        """
        Extract specific fields from a document.
        
        Args:
            document: Document model instance
            field_mappings: Dict mapping field names to extraction patterns
            
        Returns:
            Dictionary of extracted field values
        """
        result = self.extract_text(document)
        
        if not result.success:
            logger.warning(f"Field extraction failed: {result.error}")
            return {}
        
        # Use structured data if available
        if result.structured_data:
            return self._map_structured_fields(result.structured_data, field_mappings)
        
        # Fall back to pattern-based extraction from raw text
        extracted = {}
        for field_name, patterns in field_mappings.items():
            value = self._extract_field_from_text(result.text, patterns)
            if value:
                extracted[field_name] = value
        
        return extracted
    
    def _call_ocr_api(self, file_path: str, doc_type: str) -> dict:
        """
        Call the OCR API.
        
        This is a placeholder - implement based on your OCR service.
        For now, returns mock data for development.
        """
        # TODO: Implement actual DeepSeek OCR API call
        # For development, return mock data
        
        logger.info(f"OCR API call for {file_path} (mock)")
        
        # Mock response based on document type
        if doc_type == 'national_id':
            return {
                'text': 'REPUBLIC OF KENYA\nNATIONAL IDENTITY CARD\nName: JOHN DOE\nID No: 12345678\nDate of Birth: 15/01/1990',
                'structured': {
                    'full_name': 'JOHN DOE',
                    'id_number': '12345678',
                    'date_of_birth': '1990-01-15',
                    'document_type': 'NATIONAL ID',
                },
                'confidence': 0.95
            }
        elif doc_type == 'passport':
            return {
                'text': 'PASSPORT\nKENYA\nSurname: DOE\nGiven Names: JOHN\nPassport No: A12345678',
                'structured': {
                    'full_name': 'JOHN DOE',
                    'passport_number': 'A12345678',
                    'nationality': 'KENYA',
                },
                'confidence': 0.93
            }
        else:
            return {
                'text': 'Document text extracted',
                'structured': {},
                'confidence': 0.80
            }
    
    def _map_structured_fields(
        self,
        structured: Dict,
        mappings: Dict[str, list]
    ) -> Dict[str, Any]:
        """Map structured OCR output to expected field names."""
        result = {}
        
        for target_field, source_patterns in mappings.items():
            # Try each pattern
            for pattern in source_patterns:
                if pattern in structured:
                    result[target_field] = structured[pattern]
                    break
        
        return result
    
    def _extract_field_from_text(
        self,
        text: str,
        patterns: list
    ) -> Optional[str]:
        """Extract a field value from raw text using patterns."""
        import re
        
        text_lower = text.lower()
        
        for pattern in patterns:
            # Simple pattern matching
            pattern_lower = pattern.lower()
            idx = text_lower.find(pattern_lower)
            
            if idx != -1:
                # Find the value after the pattern
                start = idx + len(pattern)
                # Look for value until newline or end
                remaining = text[start:].strip()
                match = re.match(r'^[:\s]*([^\n]+)', remaining)
                if match:
                    return match.group(1).strip()
        
        return None
