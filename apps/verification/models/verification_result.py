"""Verification result model."""
from django.db import models
from apps.core.models import BaseModel


class VerificationResult(BaseModel):
    """
    Detailed results for a single verification check.
    
    Each verification request can have multiple results,
    one for each type of check performed (identity, document, compliance, etc.)
    """
    
    CHECK_TYPES = [
        ('identity', 'Identity Verification'),
        ('address', 'Address Verification'),
        ('document', 'Document Authenticity'),
        ('compliance', 'Regulatory Compliance'),
        ('policy', 'Policy Compliance'),
    ]
    
    request = models.ForeignKey(
        'VerificationRequest',
        on_delete=models.CASCADE,
        related_name='results',
        help_text="Parent verification request"
    )
    
    check_type = models.CharField(
        max_length=20,
        choices=CHECK_TYPES,
        help_text="Category of verification check"
    )
    check_name = models.CharField(
        max_length=100,
        help_text="Specific check identifier"
    )
    
    # Scores
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Check score (0-100)"
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="AI confidence level (0-1)"
    )
    
    # Status
    passed = models.BooleanField(
        help_text="Whether the check passed"
    )
    message = models.TextField(
        blank=True,
        help_text="Human-readable result message"
    )
    
    # Evidence
    evidence = models.JSONField(
        default=dict,
        help_text="Supporting evidence and raw data"
    )
    
    class Meta:
        ordering = ['check_type', 'check_name']
        verbose_name = 'Verification Result'
        verbose_name_plural = 'Verification Results'
    
    def __str__(self):
        status = "✓" if self.passed else "✗"
        return f"{status} {self.check_name}: {self.score}%"
    
    @property
    def score_percentage(self):
        """Return score as a formatted percentage."""
        return f"{self.score:.1f}%"
    
    @property
    def confidence_percentage(self):
        """Return confidence as a formatted percentage."""
        return f"{float(self.confidence) * 100:.1f}%"
    
    @property
    def status_icon(self):
        """Return an appropriate icon based on score."""
        if self.passed:
            return "✓"
        elif float(self.score) >= 70:
            return "⚠"
        else:
            return "✗"
    
    @property
    def status_class(self):
        """Return CSS class based on status."""
        if self.passed:
            return "success"
        elif float(self.score) >= 70:
            return "warning"
        else:
            return "danger"
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': str(self.id),
            'check_type': self.check_type,
            'check_name': self.check_name,
            'score': float(self.score),
            'confidence': float(self.confidence),
            'passed': self.passed,
            'message': self.message,
            'evidence': self.evidence,
        }
