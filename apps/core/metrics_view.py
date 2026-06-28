import os

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse

import apps.core.metrics
from apps.core.metrics import _CircuitBreakerCollector, _CeleryQueueDepthCollector


def metrics_view(request):

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client.multiprocess import MultiProcessCollector
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()

        # merge
        MultiProcessCollector(registry)
        
        # redis
        registry.register(_CircuitBreakerCollector())
        registry.register(_CeleryQueueDepthCollector())
        return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)

    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
