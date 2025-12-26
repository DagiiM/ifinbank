"""Documents admin configuration."""
from django.contrib import admin
from apps.core.admin import BaseModelAdmin
from .models import Document, DocumentExtraction


class DocumentExtractionInline(admin.TabularInline):
    """Inline display of document extractions."""
    model = DocumentExtraction
    extra = 0
    readonly_fields = (
        'extraction_method', 'overall_confidence',
        'processing_time', 'created_at'
    )


@admin.register(Document)
class DocumentAdmin(BaseModelAdmin):
    """Admin for documents."""
    
    list_display = (
        'original_filename', 'document_type', 'verification_request',
        'is_processed', 'file_size_display', 'created_at'
    )
    list_filter = ('document_type', 'is_processed', 'created_at')
    search_fields = ('original_filename', 'verification_request__customer_id')
    readonly_fields = (
        'id', 'file_size', 'page_count', 'mime_type',
        'is_processed', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Document Info', {
            'fields': ('verification_request', 'document_type', 'file', 'original_filename')
        }),
        ('Processing', {
            'fields': ('is_processed', 'processing_error', 'quality_score')
        }),
        ('Metadata', {
            'fields': ('file_size', 'page_count', 'mime_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    inlines = [DocumentExtractionInline]
    
    def file_size_display(self, obj):
        return obj.file_size_display
    file_size_display.short_description = 'Size'


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(BaseModelAdmin):
    """Admin for document extractions."""
    
    list_display = (
        'document', 'extraction_method', 'overall_confidence',
        'processing_time', 'created_at'
    )
    list_filter = ('extraction_method', 'created_at')
    search_fields = ('document__original_filename',)
    readonly_fields = (
        'id', 'document', 'raw_text', 'structured_data',
        'confidence_scores', 'processing_time', 'created_at', 'updated_at'
    )
