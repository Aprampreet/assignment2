from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from accounts.models import Role
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from mappings.models import PatientDoctorMapping

MANAGEMENT = {Role.SUPER_ADMIN, Role.SUPERVISOR}


def require(user, roles=None, *, temporary=False):
    if not temporary and user.must_change_password:
        raise PermissionDenied("Change your temporary password first.")
    if roles is not None and user.role not in roles:
        raise PermissionDenied("This operation is unavailable for your role.")


def patients(user):
    qs = PatientProfile.objects.select_related("user")
    if user.role == Role.SUPER_ADMIN:
        return qs
    qs = qs.filter(archived_at__isnull=True)
    if user.role == Role.SUPERVISOR:
        return qs.filter(managed_by=user)
    if user.role == Role.DOCTOR:
        return qs.filter(user__is_active=True, assignments__doctor__user=user,
                         assignments__doctor__archived_at__isnull=True, assignments__ended_at__isnull=True)
    return qs.filter(user=user)


def doctors(user, *, detail=False):
    qs = DoctorProfile.objects.select_related("user", "specialization")
    if user.role == Role.SUPER_ADMIN:
        return qs
    scope = Q(archived_at__isnull=True, user__is_active=True)
    if user.role == Role.SUPERVISOR:
        scope |= Q(archived_at__isnull=True, managed_by=user)
    if detail:
        scope |= Q(archived_at__isnull=True, user=user)
    return qs.filter(scope)


def mappings(user):
    qs = PatientDoctorMapping.objects.select_related("patient__user", "doctor__user", "doctor__specialization")
    if user.role == Role.SUPER_ADMIN:
        return qs
    if user.role == Role.SUPERVISOR:
        return qs.filter(patient__managed_by=user)
    qs = qs.filter(ended_at__isnull=True, patient__archived_at__isnull=True, patient__user__is_active=True,
                   doctor__archived_at__isnull=True, doctor__user__is_active=True)
    return qs.filter(doctor__user=user) if user.role == Role.DOCTOR else qs.filter(patient__user=user)
