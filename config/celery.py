import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("triage")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.include = ["apps.enrichment.reconciliation"]

app.conf.beat_schedule = {
    "reconcile-pending-enrichments": {
        "task": "apps.enrichment.reconciliation.reconcile_pending",
        "schedule": 300.0,
    },
}
