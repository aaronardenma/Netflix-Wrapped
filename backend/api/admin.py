from django.contrib import admin
from .models import User, ViewingData, WrappedResult, Chart  # or whatever other models


# Register your models here.

admin.site.register(User)
# admin.site.register(Upload)
admin.site.register(ViewingData)
admin.site.register(WrappedResult)
admin.site.register(Chart)