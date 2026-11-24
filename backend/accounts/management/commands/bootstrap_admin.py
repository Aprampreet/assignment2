import os
from getpass import getpass
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from accounts.models import Role, User


class Command(BaseCommand):
    help = "Create an administrator for the configured email without resetting it."

    def handle(self, **options):
        email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Medora Administrator")
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if not email or not password:
            if not self.stdin_is_interactive():
                raise CommandError("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD.")
            email = email or input("Administrator email: ")
            password = password or getpass("Administrator password: ")
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write("The administrator email already exists.")
            return
        user = User(email=email, name=name, role=Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
        try:
            with transaction.atomic():
                user.set_password(password)
                user.full_clean()
                validate_password(password, user)
                user.save(force_insert=True)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        except IntegrityError as exc:
            if not User.objects.filter(email__iexact=email).exists():
                raise CommandError("Administrator could not be created.") from exc
        self.stdout.write(self.style.SUCCESS("Administrator is ready."))

    @staticmethod
    def stdin_is_interactive():
        import sys
        return sys.stdin.isatty()
