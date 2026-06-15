from django.urls import path
from apps.transactions.views import WebhookView

urlpatterns = [
    path("webhook/", WebhookView.as_view()),
]
