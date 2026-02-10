import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        logger.error(
            f"Unhandled exception on {request.method} {request.path}: "
            f"{exception}",
            exc_info=True,
        )
        detail = str(exception) if settings.DEBUG else 'An internal error occurred.'
        return JsonResponse(
            {'error': 'Internal server error', 'detail': detail},
            status=500,
        )
