from django.urls import path, include

urlpatterns = [
    path("api/", include("apps.transactions.urls")),
    path("api/", include("apps.enrichment.urls")),
]
