import os
from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")


@setup_logging.connect
def configure_logging(**kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)


app = Celery("triage")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
# include
app.conf.include = ["apps.enrichment.reconciliation"]

app.conf.beat_schedule = {
    "reconcile-pending-enrichments": {
        "task": "apps.enrichment.reconciliation.reconcile_pending",
        "schedule": 300.0,
    },
}
