import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import Tenant, TenantMembership


class Invitation(models.Model):
    """Invitation model for user onboarding"""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=TenantMembership.Role.choices,
        default=TenantMembership.Role.MEMBER
    )
    token = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations'
    )
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invitations'
        unique_together = [['tenant', 'email']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'accepted']),
        ]

    def __str__(self):
        return f"Invitation for {self.email} to {self.tenant.name}"

    def save(self, *args, **kwargs):
        # Generate token if not set
        if not self.token:
            self.token = secrets.token_urlsafe(48)

        # Set expiration if not set (7 days from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if invitation is valid (not accepted and not expired)"""
        return not self.accepted and not self.is_expired()


class TelegramLinkToken(models.Model):
    """Token for linking Telegram account to user"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_link_token'
    )
    code = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'telegram_link_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Telegram link code for {self.user.email}"

    def save(self, *args, **kwargs):
        # Generate code if not set
        if not self.code:
            self.code = secrets.token_hex(4).upper()  # 8 character hex code

        # Set expiration if not set (24 hours from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if token has expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if token is valid (not expired)"""
        return not self.is_expired()
