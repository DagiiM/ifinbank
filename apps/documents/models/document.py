"""Document model for verification."""
import os
from django.db import models
from apps.core.models import BaseModel


def document_upload_path(instance, filename):
    """Generate upload path for documents."""
    return f'verification_docs/{instance.verification_request.customer_id}/{filename}'


class Document(BaseModel):
    """
    A document submitted for verification.
    
    Documents are uploaded and processed using OCR to extract
    text and structured data for comparison against customer data.
    """
    
    DOC_TYPES = [
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('drivers_license', "Driver's License"),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('application_form', 'Application Form'),
        ('signature_card', 'Signature Card'),
        ('photo', 'Photograph'),
        ('other', 'Other'),
    ]
    
    verification_request = models.ForeignKey(
        'verification.VerificationRequest',
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="Related verification request"
    )
    
    document_type = models.CharField(
        max_length=30,
        choices=DOC_TYPES,
        help_text="Type of document"
    )
    file = models.FileField(
        upload_to=document_upload_path,
        help_text="Uploaded document file"
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded"
    )
    
    # Processing status
    is_processed = models.BooleanField(
        default=False,
        help_text="Whether OCR processing is complete"
    )
    processing_error = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )
    
    # Metadata
    page_count = models.IntegerField(
        default=1,
        help_text="Number of pages in the document"
    )
    file_size = models.IntegerField(
        default=0,
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    # Quality assessment
    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Document quality score (0-100)"
    )
    
    class Meta:
        ordering = ['document_type', '-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.original_filename}"
    
    @property
    def file_extension(self):
        """Get the file extension."""
        _, ext = os.path.splitext(self.original_filename)
        return ext.lower()
    
    @property
    def is_image(self):
        """Check if document is an image."""
        return self.file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
    
    @property
    def is_pdf(self):
        """Check if document is a PDF."""
        return self.file_extension == '.pdf'
    
    @property
    def file_size_display(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata."""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
