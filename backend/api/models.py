import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


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


class NetflixProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="netflix_profiles")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_profile_per_user"),
        ]
        indexes = [
            models.Index(fields=["user", "name"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name}"


class Upload(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads", null=True, blank=True)
    source_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_anonymous = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "uploaded_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        owner = self.user.email if self.user else "anonymous"
        return f"{owner} - {self.source_filename or self.id}"


class Title(models.Model):
    class MediaType(models.TextChoices):
        MOVIE = "movie", "Movie"
        TV_SHOW = "tv_show", "TV Show"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, unique=True)
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.UNKNOWN)
    release_year = models.IntegerField(null=True, blank=True)
    runtime_minutes = models.IntegerField(null=True, blank=True)
    rating = models.CharField(max_length=50, blank=True)
    poster_url = models.URLField(max_length=1000, blank=True)
    tmdb_id = models.CharField(max_length=100, blank=True)
    omdb_id = models.CharField(max_length=100, blank=True)
    metadata_source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_name"]),
            models.Index(fields=["media_type"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return self.name


class ViewingEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="viewing_events")
    profile = models.ForeignKey(NetflixProfile, on_delete=models.CASCADE, related_name="viewing_events")
    title = models.ForeignKey(Title, on_delete=models.SET_NULL, related_name="viewing_events", null=True, blank=True)
    title_raw = models.CharField(max_length=1000)
    started_at = models.DateTimeField()
    duration_seconds = models.PositiveIntegerField(default=0)
    device_type = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    supplemental_video_type = models.CharField(max_length=255, blank=True)
    row_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "started_at"]),
            models.Index(fields=["title", "started_at"]),
            models.Index(fields=["upload"]),
            models.Index(fields=["duration_seconds"]),
            models.Index(fields=["row_hash"]),
        ]

    def __str__(self):
        return f"{self.profile.name} - {self.title_raw} - {self.started_at}"
