import uuid
from apps.core.logging import request_id_var


class RequestIdMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request_id = str(uuid.uuid4())
        request.request_id = request_id
        token = request_id_var.set(request_id)

        response = self.get_response(request)

        request_id_var.reset(token)
        return response
