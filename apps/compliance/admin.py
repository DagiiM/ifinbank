"""Compliance admin configuration."""
from django.contrib import admin
from apps.core.admin import BaseModelAdmin
from .models import Policy, ComplianceRule, ComplianceCheck


class ComplianceRuleInline(admin.TabularInline):
    """Inline display of compliance rules."""
    model = ComplianceRule
    extra = 0
    fields = ('code', 'name', 'rule_type', 'is_blocking', 'weight', 'is_active')


@admin.register(Policy)
class PolicyAdmin(BaseModelAdmin):
    """Admin for policies."""
    
    list_display = (
        'code', 'name', 'category', 'version',
        'effective_date', 'is_active'
    )
    list_filter = ('category', 'is_active', 'effective_date')
    search_fields = ('code', 'name', 'content')
    
    fieldsets = (
        ('Policy Info', {
            'fields': ('code', 'name', 'category', 'description')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Versioning', {
            'fields': ('version', 'effective_date', 'expiry_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Integration', {
            'fields': ('embedding_id',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ComplianceRuleInline]


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(BaseModelAdmin):
    """Admin for compliance rules."""
    
    list_display = (
        'code', 'name', 'policy', 'rule_type',
        'is_blocking', 'weight', 'is_active'
    )
    list_filter = ('policy', 'rule_type', 'is_blocking', 'is_active')
    search_fields = ('code', 'name', 'policy__code')


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(BaseModelAdmin):
    """Admin for compliance checks."""
    
    list_display = (
        'verification_request', 'rule', 'passed',
        'score', 'checked_at'
    )
    list_filter = ('passed', 'checked_at')
    search_fields = ('verification_request__customer_id', 'rule__code')
    readonly_fields = (
        'verification_request', 'rule', 'passed',
        'score', 'details', 'message', 'checked_at'
    )
