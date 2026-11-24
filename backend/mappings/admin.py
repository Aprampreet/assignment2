from django.contrib import admin

from .models import PatientDoctorMapping


@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "doctor_name", "assigned_by", "assigned_at", "ended_at")
    list_filter = ("assigned_at", "ended_at")
    search_fields = ("patient__user__name", "doctor__user__name")
    list_select_related = ("patient__user", "doctor__user", "assigned_by")
    ordering = ("-assigned_at",)
    list_per_page = 30
    readonly_fields = ("id", "patient", "doctor", "assigned_by", "assigned_at", "ended_by", "ended_at", "assignment_reason")

    @admin.display(description="Patient", ordering="patient__user__name")
    def patient_name(self, obj):
        return obj.patient.user.name

    @admin.display(description="Doctor", ordering="doctor__user__name")
    def doctor_name(self, obj):
        return obj.doctor.user.name

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
