"""Accounts signals."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='accounts.User')
def update_last_activity(sender, instance, created, **kwargs):
    """Update last activity on user save if needed."""
    pass  # Placeholder for future activity tracking
