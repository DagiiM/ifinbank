"""Verification admin configuration."""
from django.contrib import admin
from apps.core.admin import BaseModelAdmin
from .models import VerificationRequest, VerificationResult, Discrepancy


class VerificationResultInline(admin.TabularInline):
    """Inline display of verification results."""
    model = VerificationResult
    extra = 0
    readonly_fields = (
        'check_type', 'check_name', 'score', 'confidence',
        'passed', 'message', 'created_at'
    )
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class DiscrepancyInline(admin.TabularInline):
    """Inline display of discrepancies."""
    model = Discrepancy
    extra = 0
    readonly_fields = (
        'field_name', 'entered_value', 'document_value',
        'severity', 'similarity_score', 'resolution_status'
    )


@admin.register(VerificationRequest)
class VerificationRequestAdmin(BaseModelAdmin):
    """Admin for verification requests."""
    
    list_display = (
        'reference_number', 'customer_id', 'status', 'priority',
        'overall_score', 'is_approved', 'created_at'
    )
    list_filter = ('status', 'is_approved', 'priority', 'created_at')
    search_fields = ('customer_id', 'account_reference', 'id')
    readonly_fields = (
        'id', 'reference_number', 'created_at', 'updated_at',
        'started_at', 'completed_at', 'overall_score', 'is_approved'
    )
    
    fieldsets = (
        ('Request Info', {
            'fields': ('reference_number', 'customer_id', 'account_reference', 'status', 'priority')
        }),
        ('Customer Data', {
            'fields': ('customer_data',),
            'classes': ('collapse',)
        }),
        ('Assignment', {
            'fields': ('requested_by', 'assigned_to')
        }),
        ('Results', {
            'fields': ('overall_score', 'is_approved', 'decision_reason')
        }),
        ('Timeline', {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [VerificationResultInline, DiscrepancyInline]
    
    def reference_number(self, obj):
        return obj.reference_number
    reference_number.short_description = 'Reference'


@admin.register(VerificationResult)
class VerificationResultAdmin(BaseModelAdmin):
    """Admin for verification results."""
    
    list_display = (
        'request', 'check_type', 'check_name',
        'score', 'passed', 'created_at'
    )
    list_filter = ('check_type', 'passed')
    search_fields = ('request__customer_id', 'check_name')


@admin.register(Discrepancy)
class DiscrepancyAdmin(BaseModelAdmin):
    """Admin for discrepancies."""
    
    list_display = (
        'request', 'field_name', 'severity',
        'resolution_status', 'created_at'
    )
    list_filter = ('severity', 'resolution_status')
    search_fields = ('request__customer_id', 'field_name')
