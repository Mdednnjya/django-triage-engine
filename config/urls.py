from django.urls import path, include
from apps.core.metrics_view import metrics_view

urlpatterns = [
    path("api/", include("apps.transactions.urls")),
    path("api/", include("apps.enrichment.urls")),
    path("metrics", metrics_view),
]
