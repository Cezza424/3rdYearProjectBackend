from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import BankDetails, Claim, Approval
import logging
import json

# Set up a dedicated logger for security audit
logger = logging.getLogger('security_audit')

@receiver(post_save, sender=BankDetails)
def log_bank_details_changes(sender, instance, created, **kwargs):
    """Log when bank details are created or modified"""
    action = 'created' if created else 'updated'
    logger.info(
        f"BANK_DETAILS_{action.upper()}: "
        f"User {instance.user.username} {action} bank details "
        f"(ID: {instance.id}, Nickname: {instance.nickname})"
    )

@receiver(post_delete, sender=BankDetails)
def log_bank_details_deletion(sender, instance, **kwargs):
    """Log when bank details are deleted"""
    logger.warning(
        f"BANK_DETAILS_DELETED: "
        f"User {instance.user.username} deleted bank details "
        f"(ID: {instance.id}, Nickname: {instance.nickname})"
    )

@receiver(post_save, sender=Claim)
def log_claim_changes(sender, instance, created, **kwargs):
    """Log when claims are created or status changes"""
    if created:
        logger.info(
            f"CLAIM_CREATED: "
            f"User {instance.submitter.username} created claim "
            f"(ID: {instance.id}, Amount: {instance.total_amount}, Society: {instance.society.name})"
        )
    else:
        logger.info(
            f"CLAIM_UPDATED: "
            f"Claim ID {instance.id} updated "
            f"(Status: {instance.status}, Amount: {instance.total_amount})"
        )

@receiver(post_save, sender=Approval)
def log_approval_actions(sender, instance, created, **kwargs):
    """Log approval actions for claims"""
    if created:
        logger.info(
            f"CLAIM_APPROVAL: "
            f"User {instance.approver.username} {instance.decision.lower()} claim {instance.claim.id} "
            f"at {instance.approval_stage} stage"
        )

# This function can be used to create an audit record for sensitive data access
def log_sensitive_data_access(user, data_type, instance_id, action):
    """
    Log when sensitive data like bank details or encrypted fields are accessed
    
    Args:
        user: User object who accessed the data
        data_type: Type of data accessed (e.g., 'bank_details', 'claim')
        instance_id: ID of the object accessed
        action: Action performed ('viewed', 'exported', etc.)
    """
    logger.warning(
        f"SENSITIVE_DATA_ACCESS: "
        f"User {user.username} {action} {data_type} with ID {instance_id}"
    )
