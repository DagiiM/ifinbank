"""Policy service for policy management."""
from typing import List, Optional
import logging
from django.db import models as db_models

from ..models import Policy, ComplianceRule

logger = logging.getLogger(__name__)


class PolicyService:
    """
    Service for policy management and retrieval.
    
    Handles policy CRUD, versioning, and semantic search via ChromaDB.
    """
    
    def __init__(self):
        self.chromadb_client = None  # TODO: Initialize ChromaDB client
    
    def get_active_policies(self, category: Optional[str] = None) -> List[Policy]:
        """
        Get all active policies, optionally filtered by category.
        """
        from django.utils import timezone
        
        today = timezone.now().date()
        
        queryset = Policy.objects.filter(
            is_active=True,
            effective_date__lte=today
        ).filter(
            db_models.Q(expiry_date__isnull=True) |
            db_models.Q(expiry_date__gte=today)
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        return list(queryset)
    
    def get_policy_by_code(self, code: str) -> Optional[Policy]:
        """Get a policy by its unique code."""
        try:
            return Policy.objects.get(code=code, is_active=True)
        except Policy.DoesNotExist:
            return None
    
    def create_policy(
        self,
        code: str,
        name: str,
        category: str,
        content: str,
        effective_date,
        description: str = '',
        version: str = '1.0'
    ) -> Policy:
        """
        Create a new policy.
        """
        policy = Policy.objects.create(
            code=code,
            name=name,
            category=category,
            content=content,
            description=description,
            version=version,
            effective_date=effective_date
        )
        
        # Index in ChromaDB for semantic search
        self._index_policy(policy)
        
        logger.info(f"Created policy: {policy.code}")
        return policy
    
    def update_policy(
        self,
        policy: Policy,
        content: str = None,
        description: str = None,
        bump_version: bool = True
    ) -> Policy:
        """
        Update a policy.
        
        Optionally bumps the version number.
        """
        if content is not None:
            policy.content = content
        if description is not None:
            policy.description = description
        
        if bump_version:
            policy.version = self._increment_version(policy.version)
        
        policy.save()
        
        # Re-index in ChromaDB
        self._index_policy(policy)
        
        logger.info(f"Updated policy: {policy.code} to v{policy.version}")
        return policy
    
    def add_rule(
        self,
        policy: Policy,
        code: str,
        name: str,
        rule_type: str,
        condition: dict,
        is_blocking: bool = False,
        weight: float = 1.0,
        error_message: str = ''
    ) -> ComplianceRule:
        """
        Add a rule to a policy.
        """
        rule = ComplianceRule.objects.create(
            policy=policy,
            code=code,
            name=name,
            rule_type=rule_type,
            condition=condition,
            is_blocking=is_blocking,
            weight=weight,
            error_message=error_message
        )
        
        logger.info(f"Added rule {rule.code} to policy {policy.code}")
        return rule
    
    def search_policies(self, query: str, limit: int = 5) -> List[Policy]:
        """
        Search policies using semantic similarity.
        
        Uses ChromaDB for vector similarity search.
        """
        if self.chromadb_client:
            # TODO: Implement ChromaDB semantic search
            pass
        
        # Fall back to simple text search
        return list(Policy.objects.filter(
            is_active=True,
            content__icontains=query
        )[:limit])
    
    def get_applicable_rules(
        self,
        verification_request,
        blocking_only: bool = False
    ) -> List[ComplianceRule]:
        """
        Get rules applicable to a verification request.
        """
        queryset = ComplianceRule.objects.filter(
            policy__is_active=True,
            is_active=True
        )
        
        if blocking_only:
            queryset = queryset.filter(is_blocking=True)
        
        return list(queryset.order_by('-weight'))
    
    def _index_policy(self, policy: Policy):
        """Index a policy in ChromaDB for semantic search."""
        if not self.chromadb_client:
            return
        
        # TODO: Implement ChromaDB indexing
        # collection = self.chromadb_client.get_or_create_collection("policies")
        # collection.upsert(
        #     ids=[str(policy.id)],
        #     documents=[policy.content],
        #     metadatas=[{
        #         'code': policy.code,
        #         'category': policy.category,
        #         'version': policy.version
        #     }]
        # )
        pass
    
    def _increment_version(self, version: str) -> str:
        """Increment a version string (e.g., 1.0 -> 1.1)."""
        try:
            parts = version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        except Exception:
            return version + '.1'
