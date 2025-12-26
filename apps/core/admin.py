"""Core admin configuration."""
from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """Base admin class with common configurations."""
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        """Make id, created_at, updated_at always readonly."""
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.extend(['id', 'created_at', 'updated_at'])
        return list(set(readonly))
