from django.db.models import Q
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from accounts.models import Role
from config.serializers import Strict


class ListQuery(Strict):
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)
    search = serializers.CharField(max_length=150, required=False, allow_blank=True)
    sort = serializers.CharField(max_length=24, required=False)
    active = serializers.BooleanField(required=False)
    specialization = serializers.UUIDField(required=False)
    patient_id = serializers.UUIDField(required=False)
    doctor_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    managed = serializers.BooleanField(required=False)
    assignable = serializers.BooleanField(required=False)


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def listing(request, queryset, serializer, *, sort, search=(), filters=None):
    filters = filters or {}
    allowed = {"page", "page_size", "sort", *filters}
    if search:
        allowed.add("search")
    query = ListQuery(data=request.query_params.dict())
    query.is_valid(raise_exception=True)
    data = query.validated_data
    if set(data) - allowed:
        raise serializers.ValidationError({field: "Filter unavailable." for field in sorted(set(data) - allowed)})
    if data.get("search"):
        predicate = Q()
        for field in search:
            predicate |= Q(**{f"{field}__icontains": data["search"]})
        queryset = queryset.filter(predicate)
    for parameter, field in filters.items():
        if parameter in data:
            value = data[parameter]
            if parameter == "assignable":
                if value:
                    queryset = queryset.filter(user__is_active=True, archived_at__isnull=True)
                continue
            if parameter == "managed":
                if value:
                    queryset = queryset.filter(managed_by=request.user)
                continue
            queryset = queryset.filter(**{field: value})
    ordering = data.get("sort", next(iter(sort)))
    if ordering not in sort:
        raise serializers.ValidationError({"sort": "Unsupported sort order."})
    queryset = queryset.order_by(sort[ordering], "id")
    paginator = Pagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer(page, many=True).data)
