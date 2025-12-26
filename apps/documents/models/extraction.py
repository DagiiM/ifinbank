"""Document extraction model."""
from django.db import models
from apps.core.models import BaseModel


class DocumentExtraction(BaseModel):
    """
    Extracted data from a document.
    
    Stores both raw OCR text and structured/parsed data.
    """
    
    EXTRACTION_METHODS = [
        ('ocr', 'OCR'),
        ('ai', 'AI/LLM'),
        ('manual', 'Manual Entry'),
    ]
    
    document = models.ForeignKey(
        'Document',
        on_delete=models.CASCADE,
        related_name='extractions',
        help_text="Source document"
    )
    
    # Raw extraction
    raw_text = models.TextField(
        blank=True,
        help_text="Full text extracted from document"
    )
    
    # Structured data
    structured_data = models.JSONField(
        default=dict,
        help_text="Parsed field values (e.g., name, id_number, etc.)"
    )
    
    # Confidence scores per field
    confidence_scores = models.JSONField(
        default=dict,
        help_text="Confidence score for each extracted field"
    )
    
    # Extraction metadata
    extraction_method = models.CharField(
        max_length=20,
        choices=EXTRACTION_METHODS,
        default='ocr'
    )
    model_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version of OCR/AI model used"
    )
    processing_time = models.FloatField(
        default=0.0,
        help_text="Processing time in seconds"
    )
    
    # Quality metrics
    overall_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Overall extraction confidence (0-1)"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document Extraction'
        verbose_name_plural = 'Document Extractions'
    
    def __str__(self):
        return f"Extraction for {self.document}"
    
    def get_field(self, field_name: str, default=''):
        """Get a field value from structured data."""
        return self.structured_data.get(field_name, default)
    
    def get_confidence(self, field_name: str, default=0.0):
        """Get confidence score for a field."""
        return self.confidence_scores.get(field_name, default)
    
    @property
    def has_high_confidence(self):
        """Check if extraction has high overall confidence."""
        return float(self.overall_confidence) >= 0.85
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'document_id': str(self.document_id),
            'raw_text': self.raw_text[:500] + '...' if len(self.raw_text) > 500 else self.raw_text,
            'structured_data': self.structured_data,
            'confidence_scores': self.confidence_scores,
            'overall_confidence': float(self.overall_confidence),
            'extraction_method': self.extraction_method,
        }
