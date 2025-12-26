"""Custom User model for iFin Bank Verification System."""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for the verification system.
    Uses email for authentication instead of username.
    """
    
    ROLE_CHOICES = [
        ('verification_officer', 'Verification Officer'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Administrator'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    username = None  # Remove username field
    email = models.EmailField(
        'email address',
        unique=True,
        help_text="User's email address (used for login)"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="User's phone number"
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='verification_officer',
        help_text="User's role in the system"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's department"
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Employee ID from HR system"
    )
    
    # Profile settings
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )
    timezone = models.CharField(
        max_length=50,
        default='Africa/Nairobi'
    )
    
    # Activity tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.get_full_name() or self.email
    
    def get_full_name(self):
        """Return the first_name plus last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0]
    
    @property
    def is_verification_officer(self):
        return self.role == 'verification_officer'
    
    @property
    def is_supervisor(self):
        return self.role == 'supervisor'
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def has_permission(self, permission):
        """Check if user has a specific permission based on role."""
        permissions = {
            'verification_officer': [
                'view_verification', 'process_verification',
            ],
            'supervisor': [
                'view_verification', 'process_verification',
                'approve_verification', 'reject_verification',
                'assign_verification', 'view_reports',
            ],
            'admin': [
                'view_verification', 'process_verification',
                'approve_verification', 'reject_verification',
                'assign_verification', 'view_reports',
                'manage_users', 'manage_policies', 'manage_settings',
            ],
        }
        return permission in permissions.get(self.role, [])
