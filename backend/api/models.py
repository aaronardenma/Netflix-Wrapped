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

    class EnrichmentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        MATCHED = "matched", "Matched"
        UNKNOWN = "unknown", "Unknown"
        NEEDS_REVIEW = "needs_review", "Needs review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500)
    normalized_name = models.CharField(max_length=500, unique=True)
    canonical_name = models.CharField(max_length=500, blank=True)
    original_name = models.CharField(max_length=500, blank=True)
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.UNKNOWN)
    genres = models.JSONField(default=list, blank=True)
    origin_countries = models.JSONField(default=list, blank=True)
    original_language = models.CharField(max_length=20, blank=True)
    popularity = models.FloatField(default=0)
    release_year = models.IntegerField(null=True, blank=True)
    runtime_minutes = models.IntegerField(null=True, blank=True)
    rating = models.CharField(max_length=50, blank=True)
    poster_url = models.URLField(max_length=1000, blank=True)
    tmdb_id = models.CharField(max_length=100, blank=True)
    omdb_id = models.CharField(max_length=100, blank=True)
    metadata_source = models.CharField(max_length=100, blank=True)
    metadata_confidence = models.FloatField(default=0)
    enrichment_status = models.CharField(
        max_length=20,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.PENDING,
    )
    last_enriched_at = models.DateTimeField(null=True, blank=True)
    retry_after = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_name"]),
            models.Index(fields=["media_type"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["enrichment_status"]),
            models.Index(fields=["last_enriched_at"]),
        ]

    def __str__(self):
        return self.name


class ViewingEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="viewing_events")
    profile = models.ForeignKey(NetflixProfile, on_delete=models.CASCADE, related_name="viewing_events")
    title = models.ForeignKey(Title, on_delete=models.SET_NULL, related_name="viewing_events", null=True, blank=True)
    title_raw = models.CharField(max_length=1000)
    series_title = models.CharField(max_length=1000, blank=True)
    season_label = models.CharField(max_length=255, blank=True)
    episode_title = models.CharField(max_length=1000, blank=True)
    episode_number = models.PositiveIntegerField(null=True, blank=True)
    is_episode = models.BooleanField(default=False)
    parsed_media_type = models.CharField(max_length=50, blank=True)
    classification_confidence = models.FloatField(default=0)
    classification_source = models.CharField(max_length=100, blank=True)
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
            models.Index(fields=["parsed_media_type"]),
            models.Index(fields=["is_episode"]),
        ]

    def __str__(self):
        return f"{self.profile.name} - {self.title_raw} - {self.started_at}"


class YearlyRecap(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="yearly_recaps")
    profile = models.ForeignKey(NetflixProfile, on_delete=models.CASCADE, related_name="yearly_recaps")
    year = models.CharField(max_length=16)
    data = models.JSONField(default=dict)
    event_count = models.PositiveIntegerField(default=0)
    latest_event_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "profile", "year"], name="unique_yearly_recap"),
        ]
        indexes = [
            models.Index(fields=["user", "profile", "year"]),
            models.Index(fields=["generated_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.profile.name} - {self.year}"


class ExternalCatalogTitle(models.Model):
    class MediaType(models.TextChoices):
        MOVIE = "movie", "Movie"
        TV = "tv", "TV Show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=50, default="tmdb")
    external_id = models.CharField(max_length=100)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, blank=True)
    overview = models.TextField(blank=True)
    genres = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    origin_countries = models.JSONField(default=list, blank=True)
    original_language = models.CharField(max_length=20, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    runtime_minutes = models.IntegerField(null=True, blank=True)
    rating = models.CharField(max_length=50, blank=True)
    popularity = models.FloatField(default=0)
    vote_average = models.FloatField(default=0)
    vote_count = models.PositiveIntegerField(default=0)
    poster_url = models.URLField(max_length=1000, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "media_type", "external_id"],
                name="unique_external_catalog_title",
            ),
        ]
        indexes = [
            models.Index(fields=["source", "media_type"]),
            models.Index(fields=["last_refreshed_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.media_type})"


class RecommendationSet(models.Model):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        NetflixProfile,
        on_delete=models.CASCADE,
        related_name="recommendation_sets",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    algorithm_version = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.READY)
    profile_summary = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "period_start", "period_end", "algorithm_version"],
                name="unique_profile_recommendation_period",
            ),
        ]
        indexes = [
            models.Index(fields=["profile", "generated_at"]),
            models.Index(fields=["period_end", "algorithm_version"]),
        ]

    def __str__(self):
        return f"{self.profile.name}: {self.period_start} to {self.period_end}"


class Recommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommendation_set = models.ForeignKey(
        RecommendationSet,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    catalog_title = models.ForeignKey(
        ExternalCatalogTitle,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    rank = models.PositiveIntegerField()
    score = models.FloatField()
    segment = models.CharField(max_length=50, default="top_match")
    explanation = models.CharField(max_length=500)
    contributing_signals = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation_set", "catalog_title"],
                name="unique_title_per_recommendation_set",
            ),
            models.UniqueConstraint(
                fields=["recommendation_set", "rank"],
                name="unique_rank_per_recommendation_set",
            ),
        ]
        ordering = ["rank"]

    def __str__(self):
        return f"{self.rank}. {self.catalog_title.title}"
