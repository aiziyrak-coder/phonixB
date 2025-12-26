from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, phone, password=None, **extra_fields):
        """Create and return a regular user"""
        if not phone:
            raise ValueError(_('Phone number is required'))
        
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model"""
    
    ROLE_CHOICES = (
        ('author', 'Author'),
        ('reviewer', 'Reviewer'),
        ('journal_admin', 'Journal Admin'),
        ('super_admin', 'Super Admin'),
        ('accountant', 'Accountant'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(_('phone number'), max_length=20, unique=True)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    patronymic = models.CharField(_('patronymic'), max_length=150, blank=True)
    role = models.CharField(_('role'), max_length=20, choices=ROLE_CHOICES, default='author')
    orcid_id = models.CharField(_('ORCID ID'), max_length=50, blank=True)
    affiliation = models.CharField(_('affiliation'), max_length=255)
    avatar_url = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    telegram_username = models.CharField(_('telegram username'), max_length=100, blank=True)
    
    # Gamification
    gamification_level = models.CharField(_('level'), max_length=50, default='Beginner')
    gamification_badges = models.JSONField(_('badges'), default=list)
    gamification_points = models.IntegerField(_('points'), default=0)
    
    # Reviewer specific fields
    specializations = models.JSONField(_('specializations'), default=list, blank=True)
    reviews_completed = models.IntegerField(_('reviews completed'), default=0)
    average_review_time = models.FloatField(_('average review time (days)'), default=0)
    acceptance_rate = models.FloatField(_('acceptance rate (%)'), default=0)
    
    # Status fields
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    last_login = models.DateTimeField(_('last login'), auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'affiliation']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"
    
    def get_full_name(self):
        """Return full name with patronymic if available"""
        if self.patronymic:
            return f"{self.last_name} {self.first_name} {self.patronymic}"
        return f"{self.last_name} {self.first_name}"
    
    def add_points(self, points):
        """Add gamification points"""
        self.gamification_points += points
        self.save()
    
    def add_badge(self, badge):
        """Add a badge to user"""
        if badge not in self.gamification_badges:
            self.gamification_badges.append(badge)
            self.save()
