"""
DeepSeek-OCR integration with vLLM for document text extraction.

This service uses DeepSeek-OCR model running on vLLM for high-throughput
document processing with optical character recognition.

References:
- vLLM: https://github.com/vllm-project/vllm
- DeepSeek-OCR: https://github.com/deepseek-ai/DeepSeek-OCR
"""
import logging
import time
import json
import asyncio
import httpx
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from django.conf import settings
from PIL import Image
import base64
import io

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
    model_version: str = ''


@dataclass
class VLLMConfig:
    """Configuration for vLLM server connection."""
    api_url: str = 'http://localhost:8000'
    model_name: str = 'deepseek-ai/DeepSeek-OCR'
    api_key: str = ''
    timeout: int = 120
    max_tokens: int = 8192
    temperature: float = 0.0
    
    @classmethod
    def from_settings(cls) -> 'VLLMConfig':
        """Create config from Django settings."""
        return cls(
            api_url=getattr(settings, 'VLLM_API_URL', 'http://localhost:8000'),
            model_name=getattr(settings, 'VLLM_MODEL_NAME', 'deepseek-ai/DeepSeek-OCR'),
            api_key=getattr(settings, 'VLLM_API_KEY', ''),
            timeout=getattr(settings, 'VLLM_TIMEOUT', 120),
            max_tokens=getattr(settings, 'VLLM_MAX_TOKENS', 8192),
        )


class DeepSeekOCRService:
    """
    Service for document OCR using DeepSeek-OCR model via vLLM.
    
    DeepSeek-OCR is a vision-language model optimized for document understanding
    and optical character recognition. It supports multiple modes:
    - Free OCR: Extract all text without layout
    - Document to Markdown: Convert documents preserving structure  
    - Figure parsing: Understand charts and diagrams
    - Grounded OCR: Locate specific text in images
    
    This service connects to a vLLM server running the DeepSeek-OCR model.
    """
    
    # Supported prompt modes
    PROMPTS = {
        'free_ocr': '<image>\nFree OCR.',
        'document': '<image>\n<|grounding|>Convert the document to markdown.',
        'figure': '<image>\nParse the figure.',
        'describe': '<image>\nDescribe this image in detail.',
        'locate': '<image>\nLocate <|ref|>{query}<|/ref|> in the image.',
    }
    
    # Document type to prompt mapping
    DOC_TYPE_PROMPTS = {
        'national_id': 'document',
        'passport': 'document',
        'drivers_license': 'document',
        'application_form': 'document',
        'utility_bill': 'document',
        'bank_statement': 'document',
        'signature_card': 'free_ocr',
        'photo': 'describe',
    }
    
    def __init__(self, config: VLLMConfig = None):
        """
        Initialize the DeepSeek-OCR service.
        
        Args:
            config: VLLMConfig instance (created from settings if None)
        """
        self.config = config or VLLMConfig.from_settings()
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {'Content-Type': 'application/json'}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            self._client = httpx.Client(
                base_url=self.config.api_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API transmission."""
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    
    def _get_prompt(self, doc_type: str, mode: str = None) -> str:
        """Get appropriate prompt for document type."""
        if mode:
            return self.PROMPTS.get(mode, self.PROMPTS['document'])
        
        prompt_key = self.DOC_TYPE_PROMPTS.get(doc_type, 'document')
        return self.PROMPTS[prompt_key]
    
    def extract_text(
        self,
        image_path: str,
        doc_type: str = 'document',
        mode: str = None,
    ) -> OCRResult:
        """
        Extract text from an image using DeepSeek-OCR.
        
        Args:
            image_path: Path to the image file
            doc_type: Document type for prompt selection
            mode: Override prompt mode ('free_ocr', 'document', etc.)
            
        Returns:
            OCRResult with extracted text and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting DeepSeek-OCR extraction for {image_path}")
            
            # Validate image exists
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Encode image
            image_base64 = self._encode_image(image_path)
            
            # Get appropriate prompt
            prompt = self._get_prompt(doc_type, mode)
            
            # Prepare request payload (OpenAI-compatible format for vLLM)
            payload = {
                'model': self.config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': prompt.replace('<image>', ''),
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{image_base64}',
                                },
                            },
                        ],
                    },
                ],
                'max_tokens': self.config.max_tokens,
                'temperature': self.config.temperature,
            }
            
            # Make API request
            response = self.client.post('/v1/chat/completions', json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract text from response
            extracted_text = result['choices'][0]['message']['content']
            
            # Parse structured data from markdown
            structured_data = self._parse_document_text(extracted_text, doc_type)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"DeepSeek-OCR completed in {processing_time:.2f}s, "
                f"extracted {len(extracted_text)} chars"
            )
            
            return OCRResult(
                success=True,
                text=extracted_text,
                structured_data=structured_data,
                confidence=0.95,  # DeepSeek-OCR typically has high accuracy
                processing_time=processing_time,
                model_version=self.config.model_name,
            )
            
        except httpx.ConnectError as e:
            logger.error(f"vLLM server connection failed: {e}")
            return OCRResult(
                success=False,
                error=f"Cannot connect to vLLM server at {self.config.api_url}",
                processing_time=time.time() - start_time,
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"vLLM API error: {e.response.status_code} - {e.response.text}")
            return OCRResult(
                success=False,
                error=f"API error: {e.response.status_code}",
                processing_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"DeepSeek-OCR extraction failed: {e}")
            return OCRResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )
    
    async def extract_text_async(
        self,
        image_path: str,
        doc_type: str = 'document',
        mode: str = None,
    ) -> OCRResult:
        """
        Async version of text extraction.
        
        Useful for batch processing multiple documents concurrently.
        """
        start_time = time.time()
        
        try:
            image_base64 = self._encode_image(image_path)
            prompt = self._get_prompt(doc_type, mode)
            
            payload = {
                'model': self.config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt.replace('<image>', '')},
                            {
                                'type': 'image_url',
                                'image_url': {'url': f'data:image/jpeg;base64,{image_base64}'},
                            },
                        ],
                    },
                ],
                'max_tokens': self.config.max_tokens,
                'temperature': self.config.temperature,
            }
            
            headers = {'Content-Type': 'application/json'}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            
            async with httpx.AsyncClient(
                base_url=self.config.api_url,
                headers=headers,
                timeout=self.config.timeout,
            ) as client:
                response = await client.post('/v1/chat/completions', json=payload)
                response.raise_for_status()
                result = response.json()
            
            extracted_text = result['choices'][0]['message']['content']
            structured_data = self._parse_document_text(extracted_text, doc_type)
            
            return OCRResult(
                success=True,
                text=extracted_text,
                structured_data=structured_data,
                confidence=0.95,
                processing_time=time.time() - start_time,
                model_version=self.config.model_name,
            )
            
        except Exception as e:
            return OCRResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )
    
    def extract_batch(
        self,
        image_paths: List[str],
        doc_types: List[str] = None,
    ) -> List[OCRResult]:
        """
        Process multiple images in batch using async for concurrency.
        
        Args:
            image_paths: List of image file paths
            doc_types: Optional list of document types (same length as image_paths)
            
        Returns:
            List of OCRResult objects
        """
        if doc_types is None:
            doc_types = ['document'] * len(image_paths)
        
        async def process_all():
            tasks = [
                self.extract_text_async(path, dtype)
                for path, dtype in zip(image_paths, doc_types)
            ]
            return await asyncio.gather(*tasks)
        
        return asyncio.run(process_all())
    
    def _parse_document_text(
        self,
        text: str,
        doc_type: str
    ) -> Dict[str, Any]:
        """
        Parse extracted text into structured fields.
        
        Uses pattern matching and heuristics based on document type.
        """
        structured = {}
        
        # Common patterns for ID documents
        patterns = {
            'national_id': self._parse_national_id,
            'passport': self._parse_passport,
            'drivers_license': self._parse_drivers_license,
            'application_form': self._parse_application_form,
        }
        
        parser = patterns.get(doc_type, self._parse_generic)
        return parser(text)
    
    def _parse_national_id(self, text: str) -> Dict[str, Any]:
        """Parse national ID card text."""
        import re
        
        data = {}
        text_upper = text.upper()
        
        # Extract name patterns
        name_patterns = [
            r'NAME[:\s]+([A-Z\s]+)',
            r'NAMES?[:\s]+([A-Z\s]+)',
            r'FULL\s+NAME[:\s]+([A-Z\s]+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data['full_name'] = match.group(1).strip()
                break
        
        # Extract ID number
        id_patterns = [
            r'ID\s*(?:NO|NUMBER)?[.:\s]+(\d{5,})',
            r'(?:NATIONAL\s+)?ID[:\s]+(\d{5,})',
            r'\b(\d{8})\b',  # 8-digit ID common in many countries
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data['id_number'] = match.group(1).strip()
                break
        
        # Extract date of birth
        dob_patterns = [
            r'(?:DATE\s+OF\s+)?BIRTH[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'DOB[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'BORN[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data['date_of_birth'] = self._normalize_date(match.group(1))
                break
        
        # Extract gender
        if 'MALE' in text_upper:
            data['gender'] = 'M' if 'FEMALE' not in text_upper else 'F'
        elif 'SEX' in text_upper:
            sex_match = re.search(r'SEX[:\s]+([MF])', text_upper)
            if sex_match:
                data['gender'] = sex_match.group(1)
        
        return data
    
    def _parse_passport(self, text: str) -> Dict[str, Any]:
        """Parse passport text."""
        import re
        
        data = {}
        text_upper = text.upper()
        
        # Passport number (usually alphanumeric)
        passport_patterns = [
            r'PASSPORT\s*(?:NO|NUMBER)?[.:\s]+([A-Z]\d{7,8})',
            r'PASSPORT[:\s]+([A-Z0-9]{6,12})',
        ]
        for pattern in passport_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data['passport_number'] = match.group(1).strip()
                break
        
        # Names (surname and given names)
        surname_match = re.search(r'SURNAME[:\s]+([A-Z\s]+)', text_upper)
        given_match = re.search(r'GIVEN\s+NAMES?[:\s]+([A-Z\s]+)', text_upper)
        
        if surname_match and given_match:
            data['full_name'] = f"{given_match.group(1).strip()} {surname_match.group(1).strip()}"
        elif surname_match:
            data['full_name'] = surname_match.group(1).strip()
        
        # Nationality
        nationality_match = re.search(r'NATIONALITY[:\s]+([A-Z]+)', text_upper)
        if nationality_match:
            data['nationality'] = nationality_match.group(1).strip()
        
        # Date of birth
        dob_match = re.search(
            r'(?:DATE\s+OF\s+)?BIRTH[:\s]+(\d{1,2}\s*[A-Z]{3}\s*\d{4})',
            text_upper
        )
        if dob_match:
            data['date_of_birth'] = self._normalize_date(dob_match.group(1))
        
        # Expiry date
        expiry_match = re.search(
            r'(?:DATE\s+OF\s+)?EXPIRY[:\s]+(\d{1,2}\s*[A-Z]{3}\s*\d{4})',
            text_upper
        )
        if expiry_match:
            data['expiry_date'] = self._normalize_date(expiry_match.group(1))
        
        return data
    
    def _parse_drivers_license(self, text: str) -> Dict[str, Any]:
        """Parse driver's license text."""
        import re
        
        data = {}
        text_upper = text.upper()
        
        # License number
        license_patterns = [
            r'(?:LICENSE|DL|DRIVING)\s*(?:NO|NUMBER)?[.:\s]+([A-Z0-9]+)',
            r'LIC(?:ENCE)?[:\s]+([A-Z0-9]+)',
        ]
        for pattern in license_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data['license_number'] = match.group(1).strip()
                break
        
        # Name
        name_match = re.search(r'NAME[:\s]+([A-Z\s]+)', text_upper)
        if name_match:
            data['full_name'] = name_match.group(1).strip()
        
        return data
    
    def _parse_application_form(self, text: str) -> Dict[str, Any]:
        """Parse application form text."""
        import re
        
        data = {}
        text_upper = text.upper()
        lines = text_upper.split('\n')
        
        # Common form fields
        field_patterns = {
            'full_name': [r'NAME[:\s]+(.+)', r'APPLICANT[:\s]+(.+)'],
            'id_number': [r'ID\s*(?:NO|NUMBER)?[:\s]+(\d+)', r'NATIONAL\s+ID[:\s]+(\d+)'],
            'phone': [r'(?:PHONE|TEL|MOBILE)[:\s]+([+\d\s\-]+)'],
            'email': [r'E?-?MAIL[:\s]+([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})'],
            'address': [r'ADDRESS[:\s]+(.+)'],
            'date_of_birth': [r'(?:DATE\s+OF\s+)?BIRTH[:\s]+(.+)', r'DOB[:\s]+(.+)'],
        }
        
        for field, patterns in field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_upper, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if field == 'date_of_birth':
                        value = self._normalize_date(value)
                    data[field] = value
                    break
        
        return data
    
    def _parse_generic(self, text: str) -> Dict[str, Any]:
        """Generic text parsing for unknown document types."""
        return {'raw_text': text}
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format."""
        import re
        from datetime import datetime
        
        date_str = date_str.strip()
        
        # Try various formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%Y/%m/%d', '%Y-%m-%d',
            '%d %b %Y', '%d %B %Y',
            '%b %d %Y', '%B %d %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str
    
    def check_server_health(self) -> bool:
        """Check if vLLM server is running and healthy."""
        try:
            response = self.client.get('/health')
            return response.status_code == 200
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        try:
            response = self.client.get('/v1/models')
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}


# Singleton instance for use across the application
_ocr_service: Optional[DeepSeekOCRService] = None


def get_ocr_service() -> DeepSeekOCRService:
    """Get or create the singleton OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = DeepSeekOCRService()
    return _ocr_service
