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


# class Upload(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     filename = models.CharField(max_length=255)
#     upload_time = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=20, default='processed')  # or 'pending'
#     original_csv_path = models.TextField()  # path to uploaded file (e.g., /uploads/xyz.csv)

#     def __str__(self):
#         return f"{self.filename} ({self.user.email})"


class ViewingData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    show_title = models.TextField()
    watch_date = models.DateField()
    duration_minutes = models.IntegerField()
    genre = models.CharField(max_length=100, blank=True, null=True)
    device = models.CharField(max_length=100, blank=True, null=True)
    metadata = JSONField(default=dict, blank=True)  # for any extra columns

    def __str__(self):
        return f"{self.show_title} on {self.watch_date}"


class WrappedResult(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    top_genres = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    most_watched_show = models.CharField(max_length=255)
    total_watch_time_minutes = models.IntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)
    custom_json = JSONField(default=dict, blank=True)  # for storing arbitrary analytics

    def __str__(self):
        return f"Wrapped for {self.upload}"


class Chart(models.Model):
    result = models.ForeignKey(WrappedResult, on_delete=models.CASCADE)
    type = models.CharField(max_length=50)  # e.g., 'bar', 'pie'
    config = JSONField()  # Recharts or Plotly config + data
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} chart for {self.result}"
