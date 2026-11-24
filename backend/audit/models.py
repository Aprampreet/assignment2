import uuid
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"
        ARCHIVE = "archive"
        TRANSFER = "transfer"
        ASSIGN = "assign"
        END = "end"
        PASSWORD = "password_change"
        LOGIN = "login"

    class Resource(models.TextChoices):
        ACCOUNT = "account"
        PATIENT = "patient"
        DOCTOR = "doctor"
        MAPPING = "mapping"

    class Outcome(models.TextChoices):
        SUCCESS = "success"
        FAILURE = "failure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=20, choices=Action.choices)
    resource_type = models.CharField(max_length=12, choices=Resource.choices)
    resource_id = models.UUIDField(null=True)
    request_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    outcome = models.CharField(max_length=12, choices=Outcome.choices, default=Outcome.SUCCESS)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["actor", "-created_at"], name="audit_actor_date"),
            models.Index(fields=["resource_type", "resource_id", "-created_at"], name="audit_resource_date"),
        ]
