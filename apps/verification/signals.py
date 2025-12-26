"""Verification signals."""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='verification.VerificationRequest')
def log_verification_status_change(sender, instance, created, **kwargs):
    """Log verification request status changes for audit."""
    if created:
        logger.info(
            f"Verification request created: {instance.reference_number} "
            f"for customer {instance.customer_id}"
        )
    else:
        logger.info(
            f"Verification request updated: {instance.reference_number} "
            f"status={instance.status}"
        )


@receiver(post_save, sender='verification.Discrepancy')
def log_discrepancy_resolution(sender, instance, created, **kwargs):
    """Log discrepancy resolution for audit."""
    if not created and instance.is_resolved:
        logger.info(
            f"Discrepancy resolved: {instance.field_name} "
            f"for request {instance.request.reference_number} "
            f"status={instance.resolution_status}"
        )
