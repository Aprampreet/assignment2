import re
from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers
from accounts.models import Role, User
from doctors.models import DoctorProfile, Specialization
from patients.models import PatientProfile
from mappings.models import PatientDoctorMapping


class Strict(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) or hasattr(data, "keys"):
            unknown = set(data.keys()) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({field: "This field is not allowed." for field in sorted(unknown)})
        return super().to_internal_value(data)


class Identity(Strict):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=12, max_length=128, trim_whitespace=False, write_only=True)


class Signup(Identity):
    role = serializers.ChoiceField(choices=[Role.PATIENT, Role.DOCTOR, Role.SUPERVISOR], required=False, default=Role.PATIENT)
    specialization_slug = serializers.CharField(max_length=100, required=False)
    registration_number = serializers.CharField(max_length=40, required=False)

    def validate(self, attrs):
        if attrs["role"] == Role.DOCTOR:
            if not attrs.get("specialization_slug") or not attrs.get("registration_number"):
                raise serializers.ValidationError("Doctor registration requires specialization and registration number.")
            slug = attrs.pop("specialization_slug")
            specialization = Specialization.objects.filter(is_active=True).filter(
                Q(slug__iexact=slug.strip().lower().replace(" ", "-")) | Q(name__iexact=slug.strip())
            ).first()
            if specialization is None:
                raise serializers.ValidationError({"specialization_slug": "Choose an available specialization."})
            attrs["specialization"] = specialization
            attrs["registration_number"] = DoctorManagement().validate_registration_number(attrs["registration_number"])
        elif attrs.get("specialization_slug") or attrs.get("registration_number"):
            raise serializers.ValidationError("Professional fields require doctor registration.")
        return attrs


class AdminAccountCreate(Identity):
    role = serializers.ChoiceField(choices=[Role.SUPERVISOR, Role.SUPER_ADMIN], required=False, default=Role.SUPERVISOR)


class Login(Strict):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    portal = serializers.ChoiceField(choices=[Role.PATIENT, Role.DOCTOR, Role.SUPERVISOR], required=False)


class Refresh(Strict):
    refresh = serializers.CharField(max_length=4096, trim_whitespace=False, write_only=True)


class PasswordChange(Strict):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    password = serializers.CharField(min_length=12, max_length=128, trim_whitespace=False, write_only=True)


class AccountUpdate(Strict):
    name = serializers.CharField(max_length=150, required=False)
    is_active = serializers.BooleanField(required=False)
    approval_pending = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Supply name or is_active.")
        return attrs


class Account(serializers.ModelSerializer):
    profile_id = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()

    @staticmethod
    def profile(user):
        if user.role == Role.PATIENT:
            return user.patient_profile
        if user.role == Role.DOCTOR:
            return user.doctor_profile
        return None

    def get_profile_id(self, user) -> str | None:
        profile = self.profile(user)
        return str(profile.pk) if profile else None

    def get_is_archived(self, user) -> bool:
        profile = self.profile(user)
        return bool(profile and profile.archived_at)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "is_active", "approval_pending", "is_archived", "must_change_password", "profile_id", "date_joined")


class Phone(serializers.CharField):
    def to_internal_value(self, data):
        value = re.sub(r"[\s().-]", "", super().to_internal_value(data))
        if not re.fullmatch(r"\+?[0-9]{7,15}", value):
            raise serializers.ValidationError("Enter a phone number with 7–15 digits.")
        return value


class Demographics(Strict):
    date_of_birth = serializers.DateField(allow_null=True)
    gender = serializers.ChoiceField(choices=PatientProfile.Gender.choices)
    blood_group = serializers.ChoiceField(choices=PatientProfile.BLOOD_GROUPS, allow_blank=True)
    phone = Phone(allow_blank=True, max_length=30)
    address = serializers.CharField(allow_blank=True, max_length=500)

    def validate_date_of_birth(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class PatientEdit(Demographics):
    name = serializers.CharField(max_length=150)


class PatientManagement(PatientEdit):
    allergies = serializers.CharField(max_length=1000, allow_blank=True)
    medical_history = serializers.CharField(max_length=4000, allow_blank=True)


class PatientAdmin(PatientManagement):
    managed_by = serializers.UUIDField(allow_null=True)


class OptionalProfile:
    def get_fields(self):
        fields = super().get_fields()
        for key, field in fields.items():
            if key not in {"name", "email", "password", "specialization", "registration_number"}:
                field.required = False
        return fields


class PatientCreate(OptionalProfile, PatientAdmin, Identity):
    pass


class DoctorEdit(Strict):
    qualifications = serializers.CharField(max_length=500, allow_blank=True)
    biography = serializers.CharField(max_length=2000, allow_blank=True)
    professional_phone = Phone(max_length=30, allow_blank=True)


class DoctorManagement(DoctorEdit):
    name = serializers.CharField(max_length=150)
    specialization = serializers.PrimaryKeyRelatedField(queryset=Specialization.objects.filter(is_active=True))
    registration_number = serializers.CharField(max_length=40)
    years_of_experience = serializers.IntegerField(min_value=0, max_value=75)

    def validate_registration_number(self, value):
        value = value.upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9/-]{2,39}", value):
            raise serializers.ValidationError("Use 3–40 letters, digits, slashes or hyphens.")
        return value


class DoctorAdmin(DoctorManagement):
    managed_by = serializers.UUIDField(allow_null=True)


class DoctorCreate(OptionalProfile, DoctorAdmin, Identity):
    pass


class PatientRead(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = PatientProfile
        fields = ("id", "name", "date_of_birth", "gender", "blood_group", "allergies", "medical_history")


class PatientSelf(PatientRead):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(PatientRead.Meta):
        fields = PatientRead.Meta.fields + ("email", "phone", "address")


class PatientManaged(PatientSelf):
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta(PatientSelf.Meta):
        fields = PatientSelf.Meta.fields + ("managed_by", "created_by", "is_active", "archived_at", "created_at", "updated_at")


class DoctorDirectory(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    specialization_name = serializers.CharField(source="specialization.name", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = ("id", "name", "specialization", "specialization_name", "years_of_experience", "qualifications", "biography")


class DoctorOwn(DoctorDirectory):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(DoctorDirectory.Meta):
        fields = DoctorDirectory.Meta.fields + ("email", "registration_number", "professional_phone")


class DoctorManaged(DoctorOwn):
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta(DoctorOwn.Meta):
        fields = DoctorOwn.Meta.fields + ("managed_by", "created_by", "is_active", "archived_at", "created_at", "updated_at")


class AssignmentCreate(Strict):
    patient_id = serializers.UUIDField()
    doctor_id = serializers.UUIDField()
    assignment_reason = serializers.CharField(max_length=250, allow_blank=True, required=False)


class AssignmentRead(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.user.name")
    doctor_name = serializers.CharField(source="doctor.user.name")
    doctor_specialization = serializers.CharField(source="doctor.specialization.name")

    class Meta:
        model = PatientDoctorMapping
        fields = ("id", "patient_id", "doctor_id", "patient_name", "doctor_name", "doctor_specialization", "assigned_at", "ended_at")


class AssignmentManaged(AssignmentRead):
    class Meta(AssignmentRead.Meta):
        fields = AssignmentRead.Meta.fields + ("assigned_by", "ended_by", "assignment_reason")
