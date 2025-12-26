"""Compliance checking service."""
from typing import List
import logging

from apps.verification.models import VerificationRequest, VerificationResult
from ..models import Policy, ComplianceRule, ComplianceCheck

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service for regulatory and policy compliance checking.
    
    Evaluates verification requests against all applicable
    compliance rules and policies.
    """
    
    def __init__(self):
        self.policy_service = PolicyService()
    
    def check_compliance(self, request: VerificationRequest) -> List[VerificationResult]:
        """
        Run all compliance checks on a verification request.
        
        Args:
            request: VerificationRequest to check
            
        Returns:
            List of VerificationResult objects
        """
        results = []
        
        # KYC checks
        results.extend(self._check_kyc(request))
        
        # AML checks
        results.extend(self._check_aml(request))
        
        # Policy checks
        results.extend(self._check_policies(request))
        
        return results
    
    def _check_kyc(self, request: VerificationRequest) -> List[VerificationResult]:
        """
        Perform Know Your Customer verification.
        """
        checks = []
        customer = request.customer_data
        
        # ID document check
        id_docs = request.documents.filter(
            document_type__in=['national_id', 'passport']
        )
        has_valid_id = id_docs.exists()
        
        result = VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='kyc_id_document',
            score=100 if has_valid_id else 0,
            confidence=1.0,
            passed=has_valid_id,
            message='Valid ID document provided' if has_valid_id else 'No valid ID document found',
            evidence={'document_count': id_docs.count()}
        )
        checks.append(result)
        
        # Required fields check
        required_fields = ['full_name', 'id_number', 'date_of_birth']
        missing_fields = [f for f in required_fields if not customer.get(f)]
        fields_complete = len(missing_fields) == 0
        
        score = 100 - (len(missing_fields) * (100 // len(required_fields)))
        
        result = VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='kyc_required_fields',
            score=max(0, score),
            confidence=1.0,
            passed=fields_complete,
            message='All KYC fields present' if fields_complete else f'Missing: {", ".join(missing_fields)}',
            evidence={'missing_fields': missing_fields}
        )
        checks.append(result)
        
        # Age verification (18+)
        age_verified = self._verify_age(customer.get('date_of_birth', ''), min_age=18)
        
        result = VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='kyc_age_verification',
            score=100 if age_verified else 0,
            confidence=1.0 if customer.get('date_of_birth') else 0.0,
            passed=age_verified,
            message='Customer is 18 or older' if age_verified else 'Age verification failed'
        )
        checks.append(result)
        
        return checks
    
    def _check_aml(self, request: VerificationRequest) -> List[VerificationResult]:
        """
        Perform Anti-Money Laundering screening.
        
        This includes watchlist checks and risk assessment.
        """
        checks = []
        
        # Watchlist screening (placeholder - would integrate with real watchlist API)
        watchlist_clear = self._screen_watchlist(request.customer_data)
        
        result = VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='aml_watchlist',
            score=100 if watchlist_clear else 0,
            confidence=0.95,
            passed=watchlist_clear,
            message='No watchlist matches found' if watchlist_clear else 'Potential watchlist match - review required'
        )
        checks.append(result)
        
        # PEP check (Politically Exposed Persons)
        pep_clear = self._check_pep(request.customer_data)
        
        result = VerificationResult.objects.create(
            request=request,
            check_type='compliance',
            check_name='aml_pep_check',
            score=100 if pep_clear else 50,  # 50 for PEP, not failed but flagged
            confidence=0.90,
            passed=pep_clear,
            message='Not a PEP' if pep_clear else 'Potential PEP - enhanced due diligence required'
        )
        checks.append(result)
        
        return checks
    
    def _check_policies(self, request: VerificationRequest) -> List[VerificationResult]:
        """
        Check against institutional policies.
        """
        results = []
        
        # Get all active policies and their rules
        policies = Policy.objects.filter(is_active=True)
        
        for policy in policies:
            for rule in policy.rules.filter(is_active=True):
                passed = rule.evaluate(request)
                score = 100 if passed else 0
                
                # Create compliance check record
                ComplianceCheck.objects.create(
                    verification_request=request,
                    rule=rule,
                    passed=passed,
                    score=score,
                    message=rule.error_message if not passed else 'Rule passed'
                )
                
                # Also create verification result
                result = VerificationResult.objects.create(
                    request=request,
                    check_type='policy',
                    check_name=f'policy_{rule.code}',
                    score=score,
                    confidence=1.0,
                    passed=passed,
                    message=rule.error_message if not passed else f'{rule.name} passed',
                    evidence={'rule_id': str(rule.id), 'is_blocking': rule.is_blocking}
                )
                results.append(result)
        
        return results
    
    def _verify_age(self, date_of_birth: str, min_age: int = 18) -> bool:
        """Verify customer meets minimum age requirement."""
        from datetime import datetime
        
        if not date_of_birth:
            return False
        
        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y%m%d']:
                try:
                    dob = datetime.strptime(date_of_birth, fmt)
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
    
    def _screen_watchlist(self, customer_data: dict) -> bool:
        """
        Screen customer against watchlists.
        
        This is a placeholder - in production, this would
        integrate with actual watchlist APIs (UN, OFAC, etc.)
        """
        # TODO: Implement actual watchlist integration
        return True
    
    def _check_pep(self, customer_data: dict) -> bool:
        """
        Check if customer is a Politically Exposed Person.
        
        This is a placeholder - in production, this would
        integrate with PEP databases.
        """
        # TODO: Implement actual PEP checking
        return True


class PolicyService:
    """
    Service for policy management and semantic search.
    """
    
    def get_applicable_policies(self, request: VerificationRequest) -> List[Policy]:
        """Get policies applicable to a verification request."""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        return Policy.objects.filter(
            is_active=True,
            effective_date__lte=today
        ).filter(
            models.Q(expiry_date__isnull=True) |
            models.Q(expiry_date__gte=today)
        )
    
    def find_relevant_policies(self, query: str) -> List[Policy]:
        """
        Find policies relevant to a query using semantic search.
        
        This would use ChromaDB for vector similarity search.
        """
        # TODO: Implement ChromaDB semantic search
        # For now, return simple text search
        return Policy.objects.filter(
            is_active=True,
            content__icontains=query
        )


# Import models for the PolicyService
from django.db import models
