from django.contrib import admin

from .models import DoctorProfile, Specialization


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    list_per_page = 30

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("doctor_name", "registration_number", "specialization", "managed_by", "archived_at")
    list_filter = ("specialization", "archived_at", "created_at")
    search_fields = ("user__name", "user__email", "registration_number")
    list_select_related = ("user", "specialization", "managed_by")
    ordering = ("-created_at",)
    list_per_page = 30
    readonly_fields = ("id", "user", "specialization", "managed_by", "created_by", "registration_number",
                       "qualifications", "years_of_experience", "biography", "professional_phone",
                       "archived_at", "created_at", "updated_at")

    @admin.display(description="Doctor", ordering="user__name")
    def doctor_name(self, obj):
        return obj.user.name

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
