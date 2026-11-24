from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.utils import get_md5_hash_password

from accounts.models import Role, User
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from config import policies, serializers as s, services
from config.limits import limit
from config.selectors import listing
from config.schema import list_parameters, page_of

MANAGEMENT = policies.MANAGEMENT
PROFILE_SORT = {"recent": "-created_at", "name": "user__name", "-name": "-user__name", "oldest": "created_at"}
DATE_SORT = {"recent": "-assigned_at", "oldest": "assigned_at"}


def payload(request, serializer):
    value = serializer(data=request.data)
    value.is_valid(raise_exception=True)
    return value.validated_data


class Public(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return "Bearer"


class Register(Public):
    @extend_schema(request=s.Signup, responses={201: s.Account})
    def post(self, request):
        limit("registration", request.META.get("REMOTE_ADDR"), 10, 3600)
        data = payload(request, s.Signup)
        role = data.pop("role")
        obj = services.provision(request, role, data, public=True, pending=role != Role.PATIENT)
        user = obj.user if role != Role.SUPERVISOR else obj
        return Response(s.PatientSelf(obj).data if role == Role.PATIENT else {"id": str(user.pk), "role": role, "approval_pending": True}, status=201)


class TokenPair(s.Strict):
    access = s.serializers.CharField()
    refresh = s.serializers.CharField()


class Login(Public):
    @extend_schema(request=s.Login, responses=TokenPair)
    def post(self, request):
        limit("login_ip", request.META.get("REMOTE_ADDR"), 30, 300)
        data = payload(request, s.Login)
        email = User.objects.normalize_email(data["email"])
        limit("login_email", email, 8, 300)
        user = authenticate(request, email=email, password=data["password"])
        portal = data.get("portal")
        if user and portal and user.role not in ({Role.SUPERVISOR, Role.SUPER_ADMIN} if portal == Role.SUPERVISOR else {portal}):
            user = None
        if user is None:
            services.audit(request, services.Action.LOGIN, "account", success=False)
            raise AuthenticationFailed("Invalid email or password.")
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


def locked_token(raw, *, owner=None):
    try:
        token = RefreshToken(raw)
        user = User.objects.select_for_update().filter(pk=token[api_settings.USER_ID_CLAIM], is_active=True).first()
        if (user is None or (owner is not None and user.pk != owner.pk)
                or token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password)):
            raise TokenError("Invalid session")
        token.check_blacklist()
        return token, user
    except (TokenError, KeyError, ValueError) as exc:
        raise AuthenticationFailed("Invalid or expired session.") from exc


class Refresh(Public):
    @extend_schema(request=s.Refresh, responses=TokenPair)
    @transaction.atomic
    def post(self, request):
        limit("refresh", request.META.get("REMOTE_ADDR"), 240, 60)
        token, user = locked_token(payload(request, s.Refresh)["refresh"])
        token.blacklist()
        replacement = RefreshToken.for_user(user)
        return Response({"access": str(replacement.access_token), "refresh": str(replacement)})


class Logout(APIView):
    @extend_schema(request=s.Refresh, responses={204: None})
    @transaction.atomic
    def post(self, request):
        token, _ = locked_token(payload(request, s.Refresh)["refresh"], owner=request.user)
        token.blacklist()
        return Response(status=204)


class Me(APIView):
    @extend_schema(responses=s.Account)
    def get(self, request):
        return Response(s.Account(request.user).data)


class PatientList(APIView):
    @extend_schema(operation_id="patients_list", parameters=[list_parameters("PatientFilters", "search", "active", "assignable")], responses=page_of(s.PatientManaged))
    def get(self, request):
        policies.require(request.user)
        role = request.user.role
        serializer = s.PatientManaged if role in MANAGEMENT else s.PatientRead if role == Role.DOCTOR else s.PatientSelf
        filters = {"active": "user__is_active"} if role == Role.SUPER_ADMIN else {}
        if role in MANAGEMENT:
            filters["assignable"] = "user__is_active"
        return listing(request, policies.patients(request.user), serializer, sort=PROFILE_SORT, search=("user__name",), filters=filters)

    @extend_schema(request=s.PatientCreate, responses={201: s.PatientManaged})
    def post(self, request):
        policies.require(request.user, MANAGEMENT)
        obj = services.provision(request, Role.PATIENT, payload(request, s.PatientCreate))
        return Response(s.PatientManaged(obj).data, status=201)


class PatientDetail(APIView):
    @extend_schema(responses=s.PatientManaged)
    def get(self, request, id):
        policies.require(request.user)
        obj = get_object_or_404(policies.patients(request.user), pk=id)
        role = request.user.role
        serializer = s.PatientManaged if role in MANAGEMENT else s.PatientRead if role == Role.DOCTOR else s.PatientSelf
        return Response(serializer(obj).data)

    @extend_schema(request=PolymorphicProxySerializer(component_name="PatientPut", serializers=[s.PatientAdmin, s.PatientManagement, s.PatientEdit], resource_type_field_name=None), responses=s.PatientManaged)
    def put(self, request, id):
        policies.require(request.user, MANAGEMENT | {Role.PATIENT})
        role = request.user.role
        serializer = {Role.SUPER_ADMIN: s.PatientAdmin, Role.SUPERVISOR: s.PatientManagement, Role.PATIENT: s.PatientEdit}[role]
        obj = services.update_profile(request, PatientProfile, id, payload(request, serializer))
        return Response((s.PatientManaged if role in MANAGEMENT else s.PatientSelf)(obj).data)

    @extend_schema(responses={204: None})
    def delete(self, request, id):
        services.archive(request, PatientProfile, id)
        return Response(status=204)


class DoctorList(APIView):
    @extend_schema(operation_id="doctors_list", parameters=[list_parameters("DoctorFilters", "search", "active", "managed", "specialization")], responses=page_of(s.DoctorDirectory))
    def get(self, request):
        policies.require(request.user)
        role = request.user.role
        qs = policies.doctors(request.user)
        filters = {"specialization": "specialization_id"}
        if role == Role.SUPER_ADMIN:
            filters["active"] = "user__is_active"
        if role == Role.SUPERVISOR:
            filters["managed"] = "managed_by_id"
            if request.query_params.get("managed", "").lower() not in {"true", "1"}:
                qs = qs.filter(user__is_active=True, archived_at__isnull=True)
        return listing(request, qs, s.DoctorDirectory, sort=PROFILE_SORT, search=("user__name",), filters=filters)

    @extend_schema(request=s.DoctorCreate, responses={201: s.DoctorManaged})
    def post(self, request):
        policies.require(request.user, MANAGEMENT)
        obj = services.provision(request, Role.DOCTOR, payload(request, s.DoctorCreate))
        return Response(s.DoctorManaged(obj).data, status=201)


def doctor_serializer(user, obj):
    if user.role == Role.SUPER_ADMIN or (user.role == Role.SUPERVISOR and obj.managed_by_id == user.pk):
        return s.DoctorManaged
    return s.DoctorOwn if user.pk == obj.user_id else s.DoctorDirectory


class DoctorDetail(APIView):
    @extend_schema(responses=s.DoctorManaged)
    def get(self, request, id):
        policies.require(request.user)
        obj = get_object_or_404(policies.doctors(request.user, detail=True), pk=id)
        return Response(doctor_serializer(request.user, obj)(obj).data)

    @extend_schema(request=PolymorphicProxySerializer(component_name="DoctorPut", serializers=[s.DoctorAdmin, s.DoctorManagement, s.DoctorEdit], resource_type_field_name=None), responses=s.DoctorManaged)
    def put(self, request, id):
        policies.require(request.user, MANAGEMENT | {Role.DOCTOR})
        role = request.user.role
        serializer = {Role.SUPER_ADMIN: s.DoctorAdmin, Role.SUPERVISOR: s.DoctorManagement, Role.DOCTOR: s.DoctorEdit}[role]
        obj = services.update_profile(request, DoctorProfile, id, payload(request, serializer))
        return Response(doctor_serializer(request.user, obj)(obj).data)

    @extend_schema(responses={204: None})
    def delete(self, request, id):
        services.archive(request, DoctorProfile, id)
        return Response(status=204)


def assignment_list(request, qs):
    managed = request.user.role in MANAGEMENT
    return listing(request, qs, s.AssignmentManaged if managed else s.AssignmentRead, sort=DATE_SORT,
                   search=("patient__user__name", "doctor__user__name"),
                   filters={"patient_id": "patient_id", "doctor_id": "doctor_id",
                            **({"active": "ended_at__isnull"} if managed else {})})


class MappingList(APIView):
    @extend_schema(operation_id="mappings_list", parameters=[list_parameters("MappingFilters", "search", "active", "patient_id", "doctor_id")], responses=page_of(s.AssignmentRead))
    def get(self, request):
        policies.require(request.user)
        return assignment_list(request, policies.mappings(request.user))

    @extend_schema(request=s.AssignmentCreate, responses={201: s.AssignmentManaged})
    def post(self, request):
        policies.require(request.user, MANAGEMENT)
        obj = services.assign(request, payload(request, s.AssignmentCreate))
        return Response(s.AssignmentManaged(obj).data, status=201)


class MappingDetail(APIView):
    @extend_schema(description="The path UUID is a patient ID for GET.", parameters=[list_parameters("PatientMappingFilters", "search", "active", "doctor_id")], responses=page_of(s.AssignmentRead))
    def get(self, request, id):
        policies.require(request.user)
        get_object_or_404(policies.patients(request.user), pk=id)
        return assignment_list(request, policies.mappings(request.user).filter(patient_id=id))

    @extend_schema(description="The path UUID is a mapping ID for DELETE.", responses={204: None})
    def delete(self, request, id):
        services.end_assignment(request, id)
        return Response(status=204)


class UserList(APIView):
    @extend_schema(parameters=[list_parameters("AccountFilters", "search", "role", "active")], responses=page_of(s.Account))
    def get(self, request):
        policies.require(request.user, {Role.SUPER_ADMIN})
        return listing(request, User.objects.select_related("patient_profile", "doctor_profile"), s.Account,
                       sort={"recent": "-date_joined", "name": "name", "-name": "-name"}, search=("name", "email"),
                       filters={"role": "role", "active": "is_active"})

    @extend_schema(request=s.AdminAccountCreate, responses={201: s.Account})
    def post(self, request):
        policies.require(request.user, {Role.SUPER_ADMIN})
        data = payload(request, s.AdminAccountCreate)
        role = data.pop("role")
        return Response(s.Account(services.provision(request, role, data)).data, status=201)


class UserDetail(APIView):
    @extend_schema(request=PolymorphicProxySerializer(component_name="AccountPatch", serializers=[s.AccountUpdate, s.PasswordChange], resource_type_field_name=None), responses=s.Account)
    def patch(self, request, id):
        if request.user.pk == id:
            obj = services.change_password(request, payload(request, s.PasswordChange))
        else:
            policies.require(request.user, {Role.SUPER_ADMIN})
            obj = services.update_account(request, id, payload(request, s.AccountUpdate))
        return Response(s.Account(obj).data)
