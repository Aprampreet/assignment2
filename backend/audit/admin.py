from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "resource_type", "resource_id", "outcome")
    list_filter = ("action", "resource_type", "outcome", "created_at")
    search_fields = ("actor__name", "actor__email", "resource_id", "request_id")
    list_select_related = ("actor",)
    ordering = ("-created_at",)
    list_per_page = 50
    readonly_fields = ("id", "created_at", "actor", "action", "resource_type", "resource_id", "request_id", "outcome", "metadata")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
