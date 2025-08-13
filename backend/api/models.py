import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField


# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, firstName=None, lastName=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not firstName:
            raise ValueError('The firstName field must be set')
        if not lastName:
            raise ValueError('The lastName field must be set')
            
        email = self.normalize_email(email)
        user = self.model(
            email=email, 
            firstName=firstName, 
            lastName=lastName, 
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    firstName = models.CharField(default="")
    lastName = models.CharField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['firstName', 'lastName', ]

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class ViewingStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewing_stats')
    profile_name = models.CharField()
    year = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()  # Store all 4 arrays here as one dictionary

    def __str__(self):
        return f"{self.user.email} - {self.profile_name} - {self.year}"