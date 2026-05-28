from django.contrib import admin
from .models import NetflixProfile, Title, Upload, User, ViewingEvent


# Register your models here.

admin.site.register(User)
admin.site.register(NetflixProfile)
admin.site.register(Upload)
admin.site.register(Title)
admin.site.register(ViewingEvent)
