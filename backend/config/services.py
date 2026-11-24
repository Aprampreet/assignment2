from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from accounts.models import Role, User
from audit.models import AuditLog
from doctors.models import DoctorProfile
from mappings.models import PatientDoctorMapping
from patients.models import PatientProfile
from config.policies import MANAGEMENT, require

Action = AuditLog.Action
PROFILES = {Role.PATIENT: PatientProfile, Role.DOCTOR: DoctorProfile}
AUDITED_FIELDS = frozenset({
    "name", "email", "is_active", "managed_by", "date_of_birth", "gender", "blood_group", "phone",
    "address", "allergies", "medical_history", "specialization", "registration_number",
    "qualifications", "years_of_experience", "biography", "professional_phone",
})


class Conflict(APIException):
    status_code = 409
    default_detail = "This resource conflicts with an existing record."


def integrity_conflict(exc):
    constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", "")
    if constraint in {"user_email_ci_unique", "accounts_user_email_key", "one_active_assignment",
                      "doctors_doctorprofile_registration_number_key", "user_single_super_admin"}:
        raise Conflict() from exc
    raise exc


def audit(request, action, resource, obj=None, fields=(), *, success=True):
    actor = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(
        actor=actor, action=action, resource_type=resource, resource_id=getattr(obj, "pk", None),
        request_id=request.request_id, outcome="success" if success else "failure",
        metadata={"changed_fields": sorted(AUDITED_FIELDS.intersection(fields))} if fields else {},
    )


def check_password(password, user):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from exc


def owner_for(actor, owner_id):
    if owner_id is None:
        return actor if actor.role == Role.SUPERVISOR else None
    if actor.role != Role.SUPER_ADMIN:
        raise ValidationError({"managed_by": "Only the super admin can set ownership."})
    return get_object_or_404(User.objects.select_for_update(), pk=owner_id, role=Role.SUPERVISOR, is_active=True)


def provision(request, role, payload, *, public=False, pending=False):
    data = dict(payload)
    actor = None if public else request.user
    model = PROFILES.get(role)
    if actor and actor.role == Role.SUPERVISOR and "managed_by" in data:
        raise ValidationError({"managed_by": "Only the super admin can set ownership."})
    owner_id = data.pop("managed_by", None)
    name, email, password = (data.pop(field) for field in ("name", "email", "password"))
    user = User(name=name, email=User.objects.normalize_email(email), role=role, created_by=actor,
                must_change_password=not public, is_active=not pending, approval_pending=pending,
                is_staff=role == Role.SUPER_ADMIN, is_superuser=role == Role.SUPER_ADMIN)
    check_password(password, user)
    user.set_password(password)
    try:
        with transaction.atomic():
            owner = owner_for(actor, owner_id) if actor and model else None
            user.save(force_insert=True)
            audit(request, Action.CREATE, "account", user)
            if model is None:
                return user
            profile = model.objects.create(user=user, managed_by=owner, created_by=actor, **data)
            audit(request, Action.CREATE, role, profile)
            return profile
    except IntegrityError as exc:
        integrity_conflict(exc)


def locked_profile(model, pk, actor=None):
    scope = model.objects.select_related("user")
    if actor is not None:
        scope = scope.filter(archived_at__isnull=True)
        if actor.role == Role.SUPERVISOR:
            scope = scope.filter(managed_by=actor)
        elif actor.role != Role.SUPER_ADMIN:
            scope = scope.filter(user=actor)
    return get_object_or_404(scope.select_for_update(of=("self",)), pk=pk)


def profile_access(actor, obj, *, self_edit=False):
    if (actor.role == Role.SUPER_ADMIN
        or (actor.role == Role.SUPERVISOR and obj.managed_by_id == actor.pk)
        or (self_edit and obj.user_id == actor.pk)) and obj.archived_at is None:
        return
    raise NotFound()


def update_profile(request, model, pk, data):
    actor = request.user
    data = dict(data)
    try:
        with transaction.atomic():
            obj = locked_profile(model, pk, actor)
            profile_access(actor, obj, self_edit=True)
            changed = set(data)
            transfer = "managed_by" in data and data["managed_by"] != obj.managed_by_id
            if "managed_by" in data:
                owner_id = data.pop("managed_by")
                if owner_id != obj.managed_by_id:
                    obj.managed_by = owner_for(actor, owner_id)
            if "name" in data:
                obj.user.name = data.pop("name")
                obj.user.save(update_fields=["name", "updated_at"])
            for field, value in data.items():
                setattr(obj, field, value)
            obj.save()
            audit(request, Action.TRANSFER if transfer else Action.UPDATE, obj.user.role, obj, changed)
            return obj
    except IntegrityError as exc:
        integrity_conflict(exc)


def revoke_refresh(user):
    for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()).iterator():
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def archive(request, model, pk):
    require(request.user, MANAGEMENT)
    obj = locked_profile(model, pk, request.user)
    profile_access(request.user, obj)
    now = timezone.now()
    obj.archived_at = now
    obj.save(update_fields=["archived_at", "updated_at"])
    obj.user.is_active = False
    obj.user.save(update_fields=["is_active", "updated_at"])
    revoke_refresh(obj.user)
    link = "patient" if model is PatientProfile else "doctor"
    active = PatientDoctorMapping.objects.filter(**{link: obj}, ended_at__isnull=True)
    for assignment in active.select_for_update().order_by("pk").iterator():
        assignment.ended_at = now
        assignment.ended_by = request.user
        assignment.save(update_fields=["ended_at", "ended_by"])
        audit(request, Action.END, "mapping", assignment)
    audit(request, Action.ARCHIVE, obj.user.role, obj)


def assign(request, data):
    require(request.user, MANAGEMENT)
    try:
        with transaction.atomic():
            patient = locked_profile(PatientProfile, data["patient_id"], request.user)
            profile_access(request.user, patient)
            doctor = locked_profile(DoctorProfile, data["doctor_id"])
            if doctor.archived_at or not doctor.user.is_active:
                raise NotFound()
            if not patient.user.is_active:
                raise ValidationError({"patient_id": "This patient is suspended."})
            mapping = PatientDoctorMapping.objects.create(assigned_by=request.user, **data)
            audit(request, Action.ASSIGN, "mapping", mapping)
            return mapping
    except IntegrityError as exc:
        integrity_conflict(exc)


@transaction.atomic
def end_assignment(request, pk):
    require(request.user, MANAGEMENT)
    scope = PatientDoctorMapping.objects.filter(ended_at__isnull=True)
    if request.user.role == Role.SUPERVISOR:
        scope = scope.filter(patient__managed_by=request.user)
    link = get_object_or_404(scope, pk=pk)
    profile_access(request.user, locked_profile(PatientProfile, link.patient_id, request.user))
    locked_profile(DoctorProfile, link.doctor_id)
    link = get_object_or_404(PatientDoctorMapping.objects.select_for_update(), pk=pk, ended_at__isnull=True)
    link.ended_at, link.ended_by = timezone.now(), request.user
    link.save(update_fields=["ended_at", "ended_by"])
    audit(request, Action.END, "mapping", link)


@transaction.atomic
def change_password(request, data):
    user = User.objects.select_for_update().get(pk=request.user.pk)
    if not user.is_active or user.password != request.user.password:
        raise NotFound()
    if not user.check_password(data["current_password"]):
        raise ValidationError({"current_password": "The current password is incorrect."})
    if user.check_password(data["password"]):
        raise ValidationError({"password": "Choose a different password."})
    check_password(data["password"], user)
    user.set_password(data["password"])
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    revoke_refresh(user)
    audit(request, Action.PASSWORD, "account", user)
    return user


@transaction.atomic
def update_account(request, pk, data):
    require(request.user, {Role.SUPER_ADMIN})
    base = get_object_or_404(User, pk=pk)
    if base.role == Role.SUPER_ADMIN:
        raise NotFound()
    profile = None
    if base.role in PROFILES:
        model = PROFILES[base.role]
        profile = model.objects.select_for_update().get(user_id=pk)
    user = get_object_or_404(User.objects.select_for_update(), pk=pk)
    if data.get("is_active") and user.approval_pending and data.get("approval_pending") is not False:
        raise ValidationError({"approval_pending": "Approve the request before activating the account."})
    if data.get("approval_pending") is False:
        if not user.approval_pending or user.role not in {Role.DOCTOR, Role.SUPERVISOR} or data.get("is_active") is not True:
            raise ValidationError({"approval_pending": "Approval requires a pending doctor or supervisor and activation."})
    if data.get("is_active") and profile and profile.archived_at:
        raise Conflict("Archived accounts cannot be reactivated.")
    for field, value in data.items():
        setattr(user, field, value)
    user.save(update_fields=[*data, "updated_at"])
    if data.get("is_active") is False:
        revoke_refresh(user)
    audit(request, Action.UPDATE, "account", user, data)
    return user
