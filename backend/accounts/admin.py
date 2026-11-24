from uuid import uuid4

from django.contrib import admin, messages
from rest_framework.exceptions import APIException

from config.services import update_account
from .models import Role, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "account_status", "approval_pending", "date_joined")
    list_filter = ("role", "approval_pending", "is_active", "date_joined")
    search_fields = ("name", "email")
    ordering = ("-date_joined",)
    list_per_page = 30
    list_select_related = ("created_by",)
    actions = ("approve_registration",)
    fieldsets = (
        ("Identity", {"fields": ("id", "name", "email", "role")}),
        ("Access", {"fields": ("is_active", "approval_pending", "must_change_password", "is_staff", "is_superuser")}),
        ("History", {"fields": ("created_by", "date_joined", "last_login", "updated_at")}),
    )

    def get_readonly_fields(self, request, obj=None):
        return ("id", "name", "email", "role", "is_active", "approval_pending", "must_change_password",
                "is_staff", "is_superuser", "created_by", "date_joined", "last_login", "updated_at")

    @admin.display(description="Status")
    def account_status(self, obj):
        return "Awaiting approval" if obj.approval_pending else "Active" if obj.is_active else "Inactive"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_approve_permission(self, request):
        return request.user.is_authenticated and request.user.role == Role.SUPER_ADMIN

    @admin.action(description="Approve selected doctor and supervisor registrations", permissions=["approve"])
    def approve_registration(self, request, queryset):
        approved = 0
        for account in queryset.filter(role__in=(Role.DOCTOR, Role.SUPERVISOR), approval_pending=True):
            request.request_id = uuid4()
            try:
                update_account(request, account.pk, {"approval_pending": False, "is_active": True})
                approved += 1
            except APIException as exc:
                self.message_user(request, f"Could not approve {account.email}: {exc.detail}", messages.ERROR)
        self.message_user(request, f"Approved {approved} registration(s).", messages.SUCCESS)
