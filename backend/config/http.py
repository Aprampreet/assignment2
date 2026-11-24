from uuid import uuid4

from django.http import JsonResponse

from rest_framework.views import exception_handler


def error_data(request, status, detail):
    codes = {400: "validation_error", 401: "authentication_failed", 403: "forbidden",
             404: "not_found", 405: "method_not_allowed", 409: "conflict", 413: "payload_too_large", 415: "unsupported_media_type", 429: "rate_limited"}
    fields = detail if isinstance(detail, (dict, list)) else {}
    message = str(detail.get("detail", "Check the submitted fields.")) if isinstance(detail, dict) else str(detail)
    return {"code": codes.get(status, "request_failed"), "message": message,
            "field_errors": fields, "request_id": str(request.request_id)}


def api_error(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = error_data(context["request"], response.status_code, response.data)
    return response


class RequestContext:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid4()
        api_path = request.path.startswith("/api/")
        length = request.META.get("CONTENT_LENGTH", "")
        too_large = length.isascii() and length.isdigit() and (len(length) > 6 or int(length) > 32768)
        if api_path and too_large:
            response = JsonResponse(error_data(request, 413, "Request body is too large."), status=413)
        else:
            response = self.get_response(request)
        response["X-Request-ID"] = str(request.request_id)
        if api_path:
            response["Cache-Control"] = "no-store"
            response["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
