import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    SUPERVISOR = "supervisor", "Supervisor"
    DOCTOR = "doctor", "Doctor"
    PATIENT = "patient", "Patient"


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).strip().lower()

    def create_user(self, email, password=None, **fields):
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=self.normalize_email(email), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **fields):
        fields.update(role=Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
        return self.create_user(email, password, **fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = first_name = last_name = None
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_accounts")
    must_change_password = models.BooleanField(default=False)
    approval_pending = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = UserManager.normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split()[0] if self.name else self.email

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.CheckConstraint(condition=Q(role__in=Role.values), name="user_role_valid"),
            models.CheckConstraint(condition=Q(role=Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
                                   | (~Q(role=Role.SUPER_ADMIN) & Q(is_staff=False, is_superuser=False)),
                                   name="user_admin_flags_match"),
        ]
        indexes = [models.Index(fields=["role", "is_active"], name="user_role_active_idx")]
