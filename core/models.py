from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """Multi-tenant organization model"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email is required'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email authentication"""
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class TenantMembership(models.Model):
    """Links users to tenants with specific roles"""

    class Role(models.TextChoices):
        MANAGER = 'MANAGER', _('Manager')
        MEMBER = 'MEMBER', _('Member')

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tenant_memberships'
        unique_together = [['tenant', 'user']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.role})"


class TenantSettings(models.Model):
    """Per-tenant settings for AI features and other configurations"""

    class AIMode(models.TextChoices):
        FIX = 'fix', _('Fix Language')
        TRANSLATE = 'translate', _('Translate')

    class Language(models.TextChoices):
        EN = 'en', _('English')
        TR = 'tr', _('Turkish')
        DE = 'de', _('German')
        FR = 'fr', _('French')
        ES = 'es', _('Spanish')

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='settings')
    ai_enabled = models.BooleanField(default=False)
    ai_system_prompt = models.TextField(
        max_length=500,
        default='You are a helpful assistant that improves task descriptions. Keep responses clear and concise.'
    )
    ai_default_mode = models.CharField(
        max_length=20,
        choices=AIMode.choices,
        default=AIMode.FIX
    )
    ai_default_language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.EN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_settings'

    def __str__(self):
        return f"Settings for {self.tenant.name}"
