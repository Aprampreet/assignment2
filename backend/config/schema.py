from functools import lru_cache

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers
from config.selectors import ListQuery


@lru_cache
def page_of(serializer):
    return inline_serializer(
        name=f"{serializer.__name__}Page",
        fields={
            "count": serializers.IntegerField(min_value=0),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": serializer(many=True),
        },
    )


def list_parameters(name, *keys):
    fields = ListQuery().fields
    return inline_serializer(name=name, fields={key: fields[key] for key in ("page", "page_size", "sort", *keys)})
