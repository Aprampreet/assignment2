import uuid
from django.conf import settings
from django.db import models


class PatientDoctorMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey("patients.PatientProfile", on_delete=models.PROTECT, related_name="assignments")
    doctor = models.ForeignKey("doctors.DoctorProfile", on_delete=models.PROTECT, related_name="assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="made_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    ended_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="ended_assignments")
    ended_at = models.DateTimeField(null=True, blank=True)
    assignment_reason = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "doctor"], condition=models.Q(ended_at__isnull=True), name="one_active_assignment"),
            models.CheckConstraint(condition=models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=models.F("assigned_at")), name="assignment_end_after_start"),
        ]
        indexes = [
            models.Index(fields=["patient", "ended_at"], name="assignment_patient_end"),
            models.Index(fields=["doctor", "ended_at"], name="assignment_doctor_end"),
        ]
