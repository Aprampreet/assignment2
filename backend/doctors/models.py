import uuid
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from config.models import TimestampedModel


class Specialization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(Lower("name"), name="specialization_name_ci")]


class DoctorProfile(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctor_profile")
    specialization = models.ForeignKey(Specialization, on_delete=models.PROTECT, related_name="doctors")
    managed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="managed_doctors")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_doctors")
    registration_number = models.CharField(max_length=40, unique=True)
    qualifications = models.TextField(max_length=500, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    biography = models.TextField(max_length=2000, blank=True)
    professional_phone = models.CharField(max_length=20, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["specialization", "archived_at"], name="doctor_specialty_archive"),
            models.Index(fields=["managed_by", "archived_at", "created_at"], name="doctor_owner_archive_date"),
        ]
        constraints = [models.CheckConstraint(condition=models.Q(years_of_experience__lte=75), name="doctor_max_experience")]
