from django.urls import path
from apps.enrichment.views import DashboardView

urlpatterns = [
    path("dashboard/", DashboardView.as_view()),
]
