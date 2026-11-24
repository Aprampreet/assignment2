from django.contrib import admin

from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "patient_email", "managed_by", "gender", "archived_at", "created_at")
    list_filter = ("gender", "archived_at", "created_at")
    search_fields = ("user__name", "user__email", "phone")
    list_select_related = ("user", "managed_by")
    ordering = ("-created_at",)
    list_per_page = 30
    readonly_fields = ("id", "user", "managed_by", "created_by", "date_of_birth", "gender", "blood_group",
                       "phone", "address", "allergies", "medical_history", "archived_at", "created_at", "updated_at")

    @admin.display(description="Patient", ordering="user__name")
    def patient_name(self, obj):
        return obj.user.name

    @admin.display(description="Email", ordering="user__email")
    def patient_email(self, obj):
        return obj.user.email

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
