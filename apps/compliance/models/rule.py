"""Compliance rule model."""
from django.db import models
from apps.core.models import BaseModel


class ComplianceRule(BaseModel):
    """
    Specific compliance rule derived from a policy.
    
    Rules are the executable checks that validate
    verification requests against policy requirements.
    """
    
    RULE_TYPES = [
        ('required_document', 'Required Document'),
        ('field_validation', 'Field Validation'),
        ('threshold', 'Threshold Check'),
        ('watchlist', 'Watchlist Check'),
        ('age_verification', 'Age Verification'),
        ('custom', 'Custom Rule'),
    ]
    
    policy = models.ForeignKey(
        'Policy',
        on_delete=models.CASCADE,
        related_name='rules',
        help_text="Parent policy"
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Rule name"
    )
    code = models.CharField(
        max_length=50,
        help_text="Unique rule code within policy"
    )
    description = models.TextField(
        blank=True,
        help_text="Rule description"
    )
    
    rule_type = models.CharField(
        max_length=30,
        choices=RULE_TYPES,
        help_text="Type of rule"
    )
    
    # Rule definition
    condition = models.JSONField(
        default=dict,
        help_text="Rule condition definition (JSON)"
    )
    
    # Importance
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="Importance weight for scoring"
    )
    is_blocking = models.BooleanField(
        default=False,
        help_text="Whether failure blocks approval"
    )
    
    # Error configuration
    error_message = models.TextField(
        blank=True,
        help_text="Message to display when rule fails"
    )
    
    class Meta:
        ordering = ['-is_blocking', '-weight', 'name']
        verbose_name = 'Compliance Rule'
        verbose_name_plural = 'Compliance Rules'
        unique_together = ['policy', 'code']
    
    def __str__(self):
        return f"{self.policy.code}.{self.code} - {self.name}"
    
    def evaluate(self, verification_request) -> bool:
        """
        Evaluate this rule against a verification request.
        
        Returns True if the rule passes.
        """
        evaluator = RuleEvaluator(self)
        return evaluator.evaluate(verification_request)


class RuleEvaluator:
    """
    Evaluates compliance rules against verification requests.
    """
    
    def __init__(self, rule: ComplianceRule):
        self.rule = rule
    
    def evaluate(self, verification_request) -> bool:
        """
        Evaluate the rule based on its type.
        """
        evaluators = {
            'required_document': self._evaluate_required_document,
            'field_validation': self._evaluate_field_validation,
            'age_verification': self._evaluate_age_verification,
            'threshold': self._evaluate_threshold,
            'watchlist': self._evaluate_watchlist,
            'custom': self._evaluate_custom,
        }
        
        evaluator = evaluators.get(self.rule.rule_type, self._evaluate_custom)
        return evaluator(verification_request)
    
    def _evaluate_required_document(self, request) -> bool:
        """Check if required documents are present."""
        condition = self.rule.condition
        required_types = condition.get('document_types', [])
        
        for doc_type in required_types:
            if not request.documents.filter(document_type=doc_type).exists():
                return False
        return True
    
    def _evaluate_field_validation(self, request) -> bool:
        """Validate required fields are present and non-empty."""
        condition = self.rule.condition
        required_fields = condition.get('required_fields', [])
        customer_data = request.customer_data
        
        for field in required_fields:
            if not customer_data.get(field):
                return False
        return True
    
    def _evaluate_age_verification(self, request) -> bool:
        """Verify customer meets age requirements."""
        from datetime import datetime
        
        condition = self.rule.condition
        min_age = condition.get('min_age', 18)
        
        dob_str = request.customer_data.get('date_of_birth', '')
        if not dob_str:
            return False
        
        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    dob = datetime.strptime(dob_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return False
            
            today = datetime.now()
            age = (today - dob).days // 365
            return age >= min_age
        except Exception:
            return False
    
    def _evaluate_threshold(self, request) -> bool:
        """Check if a value meets threshold requirements."""
        condition = self.rule.condition
        field = condition.get('field')
        min_value = condition.get('min_value')
        max_value = condition.get('max_value')
        
        value = request.customer_data.get(field)
        if value is None:
            return False
        
        try:
            value = float(value)
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True
        except (TypeError, ValueError):
            return False
    
    def _evaluate_watchlist(self, request) -> bool:
        """Check against watchlist (placeholder)."""
        # TODO: Implement actual watchlist checking
        return True
    
    def _evaluate_custom(self, request) -> bool:
        """Evaluate custom rule (placeholder)."""
        # TODO: Implement custom rule evaluation
        return True
