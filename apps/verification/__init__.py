"""Verification app - Core verification engine for iFin Bank."""
from django.apps import AppConfig


class VerificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.verification'
    verbose_name = 'Verification Center'

    def ready(self):
        from . import signals  # noqa
