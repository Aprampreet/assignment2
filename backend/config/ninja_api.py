from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from django.conf import settings
from ninja import NinjaAPI, Query, Schema
from ninja.errors import AuthenticationError, HttpError, ValidationError as NinjaValidationError
from ninja.security import HttpBearer
from pydantic import ConfigDict, Field
from rest_framework.exceptions import APIException, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from accounts.models import Role
from assistant.services import reply
from config.http import error_data
from config.limits import limit
from config.policies import require
from dashboard.selectors import audit_rows, dashboard


class Bearer(HttpBearer):
    def authenticate(self, request, token):
        authenticator = JWTAuthentication()
        user = authenticator.get_user(authenticator.get_validated_token(token))
        request.user = user
        require(user)
        return user


api = NinjaAPI(title="Medora Healthcare Workspace", version="1", auth=Bearer(),
              docs_url="/docs/" if settings.DEBUG else None,
              openapi_url="/openapi.json" if settings.DEBUG else None)


@api.exception_handler(AuthenticationError)
def auth_error(request, exc):
    response = api.create_response(request, error_data(request, 401, "Bearer authentication is required."), status=401)
    response["WWW-Authenticate"] = "Bearer"
    return response


@api.exception_handler(HttpError)
def http_error(request, exc):
    return api.create_response(request, error_data(request, exc.status_code, str(exc)), status=exc.status_code)


@api.exception_handler(APIException)
def api_error(request, exc):
    response = api.create_response(request, error_data(request, exc.status_code, exc.detail), status=exc.status_code)
    if exc.status_code == 401:
        response["WWW-Authenticate"] = "Bearer"
    if getattr(exc, "wait", None):
        response["Retry-After"] = str(exc.wait)
    return response


@api.exception_handler(NinjaValidationError)
def validation_error(request, exc):
    fields = {".".join(map(str, error["loc"])): error["msg"] for error in exc.errors}
    return api.create_response(request, error_data(request, 400, fields), status=400)


class Specialty(Schema):
    id: UUID
    name: str


class Activity(Schema):
    id: UUID
    actor_id: UUID | None
    resource_id: UUID | None
    request_id: UUID
    action: str
    resource_type: str
    outcome: str
    created_at: datetime
    metadata: dict[str, list[str]]


class Dashboard(Schema):
    counts: dict[str, int]
    specializations: list[Specialty]
    recent_activity: list[Activity]


class AuditQuery(Schema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    start: date | None = None
    end: date | None = None
    sort: Literal["recent", "oldest"] = "recent"


class AuditPage(Schema):
    count: int
    next: int | None
    previous: int | None
    results: list[Activity]


class Chat(Schema):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)


class ChatReply(Schema):
    reply: str
    source: Literal["workspace", "groq", "help"]


@api.get("/dashboard/", response=Dashboard)
def get_dashboard(request):
    return dashboard(request.auth)


@api.get("/audit-logs/", response=AuditPage)
def get_audit(request, filters: Query[AuditQuery]):
    require(request.auth, {Role.SUPER_ADMIN})
    if filters.start and filters.end and filters.start > filters.end:
        raise ValidationError({"end": "End date must be on or after the start date."})
    qs = audit_rows(request.auth)
    if filters.start:
        qs = qs.filter(created_at__gte=datetime.fromisoformat(f"{filters.start}T00:00:00+00:00"))
    if filters.end and filters.end < date.max:
        qs = qs.filter(created_at__lt=datetime.fromisoformat(f"{filters.end + timedelta(days=1)}T00:00:00+00:00"))
    if filters.sort == "oldest":
        qs = qs.order_by("created_at", "id")
    count = qs.count()
    offset = (filters.page - 1) * filters.page_size
    rows = list(qs[offset:offset + filters.page_size]) if offset < count else []
    return {"count": count, "next": filters.page + 1 if offset + filters.page_size < count else None,
            "previous": filters.page - 1 if filters.page > 1 else None, "results": rows}


@api.post("/assistant/chat/", response=ChatReply)
def chat(request, body: Chat):
    limit("assistant", request.auth.pk, 12)
    return reply(request.auth, body.message)
