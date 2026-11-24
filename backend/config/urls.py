from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from config import views
from config.ninja_api import api
from config.http import error_data

admin.site.site_header = "Medora administration"
admin.site.site_title = "Medora administration"
admin.site.index_title = "Operations and records"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("api/auth/register/", views.Register.as_view()),
    path("api/auth/login/", views.Login.as_view()),
    path("api/auth/refresh/", views.Refresh.as_view()),
    path("api/auth/logout/", views.Logout.as_view()),
    path("api/auth/me/", views.Me.as_view()),
    path("api/patients/", views.PatientList.as_view()),
    path("api/patients/<uuid:id>/", views.PatientDetail.as_view()),
    path("api/doctors/", views.DoctorList.as_view()),
    path("api/doctors/<uuid:id>/", views.DoctorDetail.as_view()),
    path("api/mappings/", views.MappingList.as_view()),
    path("api/mappings/<uuid:id>/", views.MappingDetail.as_view()),
    path("api/users/", views.UserList.as_view()),
    path("api/users/<uuid:id>/", views.UserDetail.as_view()),
]
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    ]


def handler404(request, exception):
    return JsonResponse(error_data(request, 404, "Resource not found."), status=404)


def handler500(request):
    return JsonResponse(error_data(request, 500, "An unexpected error occurred."), status=500)
