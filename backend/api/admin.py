from django.contrib import admin
from .models import User, ViewingStat


# Register your models here.

admin.site.register(User)
admin.site.register(ViewingStat)