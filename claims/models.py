from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver

class Society(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    starting_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Societies"

from django.core.validators import RegexValidator
#from django.contrib.auth.models import User

class SocietyMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='membership')
    society = models.ForeignKey(Society, on_delete=models.CASCADE)
    is_committee_member = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'society')


#class UserProfile(models.Model):
#    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#    societies = models.ManyToManyField(Society, related_name='members', blank=True)
#
#    def __str__(self):
#        return f"{self.user.username}'s Profile"

from encrypted_field.fields import EncryptedField

class BankDetails(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    nickname = models.CharField(max_length=100, help_text="A name to identify this bank account")
    account_name = EncryptedField(max_length=100)
    account_number = EncryptedField(
        max_length=8,
        validators=[
            RegexValidator(
                regex='^[0-9]{8}$',
                message='Account number must be 8 digits'
            )
        ]
    )
    sort_code = EncryptedField(
        max_length=6,
        validators=[
            RegexValidator(
                regex='^[0-9]{6}$',
                message='Sort code must be 6 digits (without hyphens)'
            )
        ]
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Bank Details"
        unique_together = [['user', 'nickname']]

    def __str__(self):
        return f"{self.user.username}'s account: {self.nickname}"

    def save(self, *args, **kwargs):
        # If this is being set as default, unset any other defaults for this user
        if self.is_default:
            BankDetails.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Claim(models.Model):
    STATUS_CHOICES = [
        ('PENDING_COMMITTEE', 'Pending Committee'),
        ('PENDING_SU', 'Pending SU'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]

    submitter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='claims')
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_COMMITTEE')

    # Bank details can either be stored as a reference or as one-time use details
    saved_bank_details = models.ForeignKey(
        BankDetails, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='claims'
    )
    # One-time use bank details (used when saved_bank_details is None)
    account_name = EncryptedField(max_length=100, null=True, blank=True)
    account_number = EncryptedField(
        max_length=8,
        null=True, 
        blank=True,
        validators=[
            RegexValidator(
                regex='^[0-9]{8}$',
                message='Account number must be 8 digits'
            )
        ]
    )
    sort_code = EncryptedField(
        max_length=6,
        null=True, 
        blank=True,
        validators=[
            RegexValidator(
                regex='^[0-9]{6}$',
                message='Sort code must be 6 digits (without hyphens)'
            )
        ]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Claim #{self.id} - {self.submitter.username} - {self.total_amount}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Ensure either saved bank details OR one-time bank details are provided
        if not self.saved_bank_details and not (self.account_name and self.account_number and self.sort_code):
            raise ValidationError("Either saved bank details or one-time bank details must be provided")

        if self.saved_bank_details and (self.account_name or self.account_number or self.sort_code):
            raise ValidationError("Cannot provide both saved bank details and one-time bank details")

    def get_bank_details(self):
        """Return a dictionary with the bank details to use for this claim"""
        if self.saved_bank_details:
            return {
                'account_name': self.saved_bank_details.account_name,
                'account_number': self.saved_bank_details.account_number,
                'sort_code': self.saved_bank_details.sort_code,
                'is_saved': True
            }
        else:
            return {
                'account_name': self.account_name,
                'account_number': self.account_number,
                'sort_code': self.sort_code,
                'is_saved': False
            }

class Receipt(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='receipts')
    file = models.FileField(upload_to='receipts/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt for Claim #{self.claim.id}"

class Approval(models.Model):
    STAGE_CHOICES = [
        ('COMMITTEE', 'Committee Approval'),
        ('SU', 'SU Staff Approval'),
    ]

    DECISION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals')
    approval_stage = models.CharField(max_length=10, choices=STAGE_CHOICES)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.approval_stage} - {self.decision} by {self.approver.username}"

