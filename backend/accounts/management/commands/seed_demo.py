import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import Role, User
from doctors.models import DoctorProfile, Specialization
from mappings.models import PatientDoctorMapping
from patients.models import PatientProfile
from config.services import check_password


class Command(BaseCommand):
    help = "Seed synthetic reviewers in an explicitly designated development schema."

    @transaction.atomic
    def handle(self, **options):
        schema = os.getenv("DATABASE_SCHEMA", "medora")
        if not settings.DEBUG or os.getenv("ALLOW_DEMO_SEED") != "1" or schema != "medora_demo":
            raise CommandError("Demo seeding requires DEBUG, ALLOW_DEMO_SEED=1 and schema medora_demo.")
        admin = User.objects.filter(role=Role.SUPER_ADMIN).first()
        if not admin:
            raise CommandError("Run bootstrap_admin first.")
        password = os.getenv("DEMO_PASSWORD")
        if not password:
            raise CommandError("Provide DEMO_PASSWORD through your environment.")

        def user(role, name):
            email = f"{role}@medora.example"
            record, created = User.objects.get_or_create(email=email, defaults={
                "role": role, "name": name, "created_by": admin, "must_change_password": True,
            })
            if record.role != role:
                raise CommandError("Existing synthetic email has another role.")
            if created:
                check_password(password, record)
                record.set_password(password)
                record.save(update_fields=["password"])
            return record

        supervisor = user(Role.SUPERVISOR, "Riley Calder")
        doctor, _ = DoctorProfile.objects.get_or_create(user=user(Role.DOCTOR, "Morgan Iyer"), defaults={
            "managed_by": supervisor, "created_by": supervisor, "registration_number": "DEMO-MD-001",
            "specialization": Specialization.objects.get(slug="general-medicine"),
            "qualifications": "Fictional MD", "years_of_experience": 9,
            "biography": "Synthetic demonstration profile for general medicine.",
        })
        patient, _ = PatientProfile.objects.get_or_create(user=user(Role.PATIENT, "Jamie Rao"), defaults={
            "managed_by": supervisor, "created_by": supervisor, "blood_group": "O+",
        })
        if not PatientDoctorMapping.objects.filter(patient=patient, doctor=doctor).exists():
            PatientDoctorMapping.objects.create(patient=patient, doctor=doctor, assigned_by=supervisor)
        self.stdout.write(self.style.SUCCESS("Synthetic supervisor, doctor and patient are ready."))
