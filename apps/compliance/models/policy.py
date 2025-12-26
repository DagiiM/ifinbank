"""Policy model for compliance."""
from django.db import models
from apps.core.models import BaseModel


class Policy(BaseModel):
    """
    Institutional policy document for compliance checking.
    
    Policies define the rules and requirements that must be
    met for customer verification to pass.
    """
    
    CATEGORY_CHOICES = [
        ('kyc', 'Know Your Customer'),
        ('aml', 'Anti-Money Laundering'),
        ('institutional', 'Institutional Policy'),
        ('regulatory', 'Regulatory Requirement'),
    ]
    
    name = models.CharField(
        max_length=200,
        help_text="Policy name"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique policy code"
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        help_text="Policy category"
    )
    description = models.TextField(
        blank=True,
        help_text="Brief description of the policy"
    )
    content = models.TextField(
        help_text="Full policy text"
    )
    
    # Versioning
    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Policy version"
    )
    effective_date = models.DateField(
        help_text="When this policy takes effect"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this policy expires (if applicable)"
    )
    
    # Embedding for semantic search (ChromaDB)
    embedding_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID in ChromaDB for semantic search"
    )
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Policy'
        verbose_name_plural = 'Policies'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_current(self):
        """Check if policy is currently effective."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if today < self.effective_date:
            return False
        if self.expiry_date and today > self.expiry_date:
            return False
        return self.is_active
