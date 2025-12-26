"""Documents services package."""
from .ocr_service import OCRService
from .extraction_service import ExtractionService
from .vllm_ocr_service import DeepSeekOCRService, VLLMConfig, get_ocr_service

__all__ = [
    'OCRService',
    'ExtractionService',
    'DeepSeekOCRService',
    'VLLMConfig',
    'get_ocr_service',
]
