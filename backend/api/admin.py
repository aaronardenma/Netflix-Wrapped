from django.contrib import admin
from .models import (
    ExternalCatalogTitle,
    NetflixProfile,
    Recommendation,
    RecommendationFeedback,
    RecommendationSet,
    Title,
    Upload,
    User,
    ViewingEvent,
)


# Register your models here.

admin.site.register(User)
admin.site.register(NetflixProfile)
admin.site.register(Upload)
admin.site.register(Title)
admin.site.register(ViewingEvent)
admin.site.register(ExternalCatalogTitle)
admin.site.register(RecommendationSet)
admin.site.register(Recommendation)
admin.site.register(RecommendationFeedback)
