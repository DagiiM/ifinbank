"""Verification request model."""
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel


class VerificationRequest(BaseModel):
    """
    A request to verify customer data against source documents.
    
    This is the main entity that tracks the verification workflow
    from request to final decision.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('review_required', 'Review Required'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Medium-High'),
        (5, 'Normal'),
        (7, 'Low'),
        (10, 'Lowest'),
    ]
    
    # Customer reference from core banking system
    customer_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Customer ID from core banking system"
    )
    account_reference = models.CharField(
        max_length=50,
        blank=True,
        help_text="Account number if applicable"
    )
    
    # Request metadata
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_requests',
        help_text="User who initiated this verification request"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_verifications',
        help_text="Verification officer assigned to this request"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=5,
        help_text="Processing priority (1=highest, 10=lowest)"
    )
    
    # Customer data snapshot (from core banking)
    customer_data = models.JSONField(
        default=dict,
        help_text="Snapshot of customer data from core banking system"
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing began"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing completed"
    )
    
    # Results
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Overall verification score (0-100)"
    )
    is_approved = models.BooleanField(
        null=True,
        help_text="Final approval decision (null = pending)"
    )
    decision_reason = models.TextField(
        blank=True,
        help_text="Explanation for the decision"
    )
    
    # Review tracking
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications',
        help_text="User who performed manual review"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    review_notes = models.TextField(
        blank=True,
        help_text="Notes from manual review"
    )
    
    class Meta:
        ordering = ['priority', '-created_at']
        indexes = [
            models.Index(fields=['customer_id', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]
        verbose_name = 'Verification Request'
        verbose_name_plural = 'Verification Requests'
    
    def __str__(self):
        return f"VR-{str(self.id)[:8].upper()} - {self.customer_id}"
    
    @property
    def reference_number(self):
        """Generate a human-readable reference number."""
        return f"VR-{str(self.id)[:8].upper()}"
    
    @property
    def processing_time(self):
        """Calculate time taken for verification in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_processing(self):
        return self.status == 'processing'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def needs_review(self):
        return self.status == 'review_required'
    
    def start_processing(self):
        """Mark request as processing."""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete(self, approved: bool, score: float, reason: str):
        """Mark request as completed with results."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.is_approved = approved
        self.overall_score = score
        self.decision_reason = reason
        self.save(update_fields=[
            'status', 'completed_at', 'is_approved',
            'overall_score', 'decision_reason', 'updated_at'
        ])
    
    def require_review(self, reason: str):
        """Mark request as requiring manual review."""
        self.status = 'review_required'
        self.decision_reason = reason
        self.save(update_fields=['status', 'decision_reason', 'updated_at'])
    
    def fail(self, reason: str):
        """Mark request as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.decision_reason = reason
        self.save(update_fields=['status', 'completed_at', 'decision_reason', 'updated_at'])
    
    def get_customer_field(self, field_name: str, default=''):
        """Safely get a field from customer_data."""
        return self.customer_data.get(field_name, default)
