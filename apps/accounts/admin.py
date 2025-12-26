"""Accounts admin configuration."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""
    
    list_display = (
        'email', 'first_name', 'last_name', 'role',
        'department', 'is_active', 'date_joined'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'department')
    search_fields = ('email', 'first_name', 'last_name', 'employee_id')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': (
            'first_name', 'last_name', 'phone', 'avatar'
        )}),
        ('Work Info', {'fields': ('role', 'department', 'employee_id')}),
        ('Settings', {'fields': ('timezone',)}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'last_activity')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'password1', 'password2', 'role'
            ),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'last_activity')
