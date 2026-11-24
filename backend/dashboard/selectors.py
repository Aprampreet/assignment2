from django.db.models import Q
from accounts.models import Role, User
from audit.models import AuditLog
from config import policies
from doctors.models import Specialization


def statistics(user):
    counts = {}
    if user.role != Role.PATIENT:
        counts["patients"] = policies.patients(user).filter(user__is_active=True, archived_at__isnull=True).count()
    if user.role in policies.MANAGEMENT:
        doctors = policies.doctors(user).filter(user__is_active=True, archived_at__isnull=True)
        if user.role == Role.SUPERVISOR:
            doctors = doctors.filter(managed_by=user)
        counts["doctors"] = doctors.count()
    if user.role == Role.SUPER_ADMIN:
        counts["supervisors"] = User.objects.filter(role=Role.SUPERVISOR, is_active=True).count()
    counts["assignments"] = policies.mappings(user).filter(
        ended_at__isnull=True, patient__user__is_active=True, doctor__user__is_active=True,
    ).count()
    return counts


def audit_rows(user):
    base = AuditLog.objects.order_by("-created_at", "-id")
    if user.role == Role.SUPER_ADMIN:
        return base
    patient_ids = policies.patients(user).order_by().values("pk")
    doctor_ids = policies.doctors(user).filter(managed_by=user).order_by().values("pk")
    mapping_ids = policies.mappings(user).order_by().values("pk")
    return base.filter(
        Q(resource_type="patient", resource_id__in=patient_ids)
        | Q(resource_type="doctor", resource_id__in=doctor_ids)
        | Q(resource_type="mapping", resource_id__in=mapping_ids)
    )


def dashboard(user):
    return {
        "counts": statistics(user),
        "specializations": list(Specialization.objects.filter(is_active=True).values("id", "name")),
        "recent_activity": list(audit_rows(user)[:6]) if user.role in policies.MANAGEMENT else [],
    }
