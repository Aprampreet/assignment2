from django.conf import settings
from django.db import models
from config.models import TimestampedModel


class PatientProfile(TimestampedModel):
    class Gender(models.TextChoices):
        UNSPECIFIED = "unspecified", "Unspecified"
        WOMAN = "woman", "Woman"
        MAN = "man", "Man"
        NON_BINARY = "non_binary", "Non-binary"

    BLOOD_GROUPS = [(f"{group}{rh}", f"{group}{rh}") for group in ("A", "B", "AB", "O") for rh in ("+", "-")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patient_profile")
    managed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="managed_patients")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_patients")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, default=Gender.UNSPECIFIED)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(max_length=500, blank=True)
    allergies = models.TextField(max_length=1000, blank=True)
    medical_history = models.TextField(max_length=4000, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["managed_by", "archived_at", "created_at"], name="patient_owner_archive_date")]
