"""Discrepancy tracking model."""
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel


class Discrepancy(BaseModel):
    """
    A detected discrepancy between entered data and source documents.
    
    Discrepancies are flagged during verification and may need
    manual resolution before approval.
    """
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('info', 'Informational'),
    ]
    
    RESOLUTION_STATUS = [
        ('unresolved', 'Unresolved'),
        ('accepted', 'Accepted'),
        ('corrected', 'Corrected'),
        ('dismissed', 'Dismissed'),
    ]
    
    request = models.ForeignKey(
        'VerificationRequest',
        on_delete=models.CASCADE,
        related_name='discrepancies',
        help_text="Parent verification request"
    )
    
    field_name = models.CharField(
        max_length=100,
        help_text="Name of the field with discrepancy"
    )
    entered_value = models.TextField(
        help_text="Value as entered in the system"
    )
    document_value = models.TextField(
        help_text="Value extracted from the document"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        help_text="Impact level of this discrepancy"
    )
    description = models.TextField(
        help_text="Detailed description of the discrepancy"
    )
    
    # Match information
    similarity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Similarity score between values (0-100)"
    )
    
    # Resolution tracking
    resolution_status = models.CharField(
        max_length=20,
        choices=RESOLUTION_STATUS,
        default='unresolved'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_discrepancies'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(
        blank=True,
        help_text="Explanation of how discrepancy was resolved"
    )
    
    class Meta:
        ordering = ['-severity', 'field_name']
        verbose_name = 'Discrepancy'
        verbose_name_plural = 'Discrepancies'
    
    def __str__(self):
        return f"{self.field_name}: '{self.entered_value}' vs '{self.document_value}'"
    
    @property
    def is_resolved(self):
        return self.resolution_status != 'unresolved'
    
    @property
    def is_critical(self):
        return self.severity == 'critical'
    
    @property
    def is_blocking(self):
        """Check if this discrepancy blocks auto-approval."""
        return self.severity in ['critical', 'major'] and not self.is_resolved
    
    @property
    def severity_icon(self):
        """Return an icon based on severity."""
        icons = {
            'critical': '🔴',
            'major': '🟠',
            'minor': '🟡',
            'info': '🔵',
        }
        return icons.get(self.severity, '⚪')
    
    @property
    def severity_class(self):
        """Return CSS class based on severity."""
        classes = {
            'critical': 'danger',
            'major': 'warning',
            'minor': 'info',
            'info': 'secondary',
        }
        return classes.get(self.severity, 'secondary')
    
    def resolve(self, user, status: str, note: str = ''):
        """Mark discrepancy as resolved."""
        self.resolution_status = status
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save(update_fields=[
            'resolution_status', 'resolved_by',
            'resolved_at', 'resolution_note', 'updated_at'
        ])
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': str(self.id),
            'field_name': self.field_name,
            'entered_value': self.entered_value,
            'document_value': self.document_value,
            'severity': self.severity,
            'description': self.description,
            'similarity_score': float(self.similarity_score),
            'resolution_status': self.resolution_status,
            'is_resolved': self.is_resolved,
        }
