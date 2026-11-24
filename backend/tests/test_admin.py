from uuid import uuid4

import pytest
from django.test import Client

from accounts.models import Role, User
from audit.models import AuditLog
from doctors.models import DoctorProfile, Specialization

pytestmark = pytest.mark.django_db


def make_user(role, **extra):
    flags = {"is_staff": True, "is_superuser": True} if role == Role.SUPER_ADMIN else {}
    return User.objects.create_user(f"{uuid4().hex}@example.test", "local-test-password-123", name="Test User",
                                    role=role, **flags, **extra)


def test_admin_approval_uses_account_service_and_audits():
    administrator = make_user(Role.SUPER_ADMIN)
    doctor = make_user(Role.DOCTOR, is_active=False, approval_pending=True)
    specialty = Specialization.objects.create(name="Family Medicine", slug="family-medicine")
    DoctorProfile.objects.create(user=doctor, specialization=specialty, registration_number="TEST-0001")
    client = Client()
    client.force_login(administrator)

    response = client.post("/admin/accounts/user/", {
        "action": "approve_registration", "_selected_action": [str(doctor.pk)], "index": "0",
    })

    assert response.status_code == 302
    doctor.refresh_from_db()
    assert doctor.is_active and not doctor.approval_pending
    event = AuditLog.objects.get(actor=administrator, resource_id=doctor.pk, action=AuditLog.Action.UPDATE)
    assert event.metadata["changed_fields"] == ["is_active"]


def test_non_admin_cannot_open_django_admin():
    client = Client()
    client.force_login(make_user(Role.SUPERVISOR))
    response = client.get("/admin/")
    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")
