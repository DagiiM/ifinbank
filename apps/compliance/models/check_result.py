"""Compliance check result model."""
from django.db import models
from apps.core.models import BaseModel


class ComplianceCheck(BaseModel):
    """
    Result of a compliance rule evaluation.
    
    Records the outcome of each rule check for audit trail.
    """
    
    verification_request = models.ForeignKey(
        'verification.VerificationRequest',
        on_delete=models.CASCADE,
        related_name='compliance_checks',
        help_text="Related verification request"
    )
    rule = models.ForeignKey(
        'ComplianceRule',
        on_delete=models.SET_NULL,
        null=True,
        related_name='checks',
        help_text="Rule that was evaluated"
    )
    
    passed = models.BooleanField(
        help_text="Whether the check passed"
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Compliance score (0-100)"
    )
    
    # Details
    details = models.JSONField(
        default=dict,
        help_text="Detailed evaluation results"
    )
    message = models.TextField(
        blank=True,
        help_text="Human-readable result message"
    )
    
    checked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the check was performed"
    )
    
    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'Compliance Check'
        verbose_name_plural = 'Compliance Checks'
    
    def __str__(self):
        status = "✓" if self.passed else "✗"
        rule_name = self.rule.name if self.rule else "Unknown"
        return f"{status} {rule_name}: {self.score}%"
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': str(self.id),
            'rule_code': self.rule.code if self.rule else None,
            'rule_name': self.rule.name if self.rule else None,
            'passed': self.passed,
            'score': float(self.score),
            'message': self.message,
            'details': self.details,
            'checked_at': self.checked_at.isoformat(),
        }
