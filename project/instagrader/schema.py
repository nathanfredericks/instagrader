from drf_spectacular.utils import inline_serializer  # type: ignore[reportUnknownVariableType]
from rest_framework import serializers
from rest_framework.serializers import Serializer


DetailResponseSerializer: Serializer[dict[str, str]] = inline_serializer(  # type: ignore[reportUnknownVariableType]
    name="DetailResponse",
    fields={
        "detail": serializers.CharField(),
    },
)

ValidationErrorResponseSerializer: Serializer[dict[str, list[str]]] = inline_serializer(  # type: ignore[reportUnknownVariableType]
    name="ValidationErrorResponse",
    fields={
        "field_name": serializers.ListField(
            child=serializers.CharField(),
            help_text="Each field maps to a list of validation error strings.",
        ),
    },
)

UnauthorizedResponseSerializer: Serializer[dict[str, str]] = inline_serializer(  # type: ignore[reportUnknownVariableType]
    name="UnauthorizedResponse",
    fields={
        "detail": serializers.CharField(
            default="Authentication credentials were not provided."
        ),
        "code": serializers.CharField(default="not_authenticated"),
    },
)


def error_responses(
    *codes: int,
) -> dict[int, Serializer[dict[str, str]] | Serializer[dict[str, list[str]]]]:
    """Build a dict of common error responses for given HTTP status codes.

    Usage: responses={200: MySerializer, **error_responses(400, 401, 404)}
    """
    mapping: dict[
        int, Serializer[dict[str, str]] | Serializer[dict[str, list[str]]]
    ] = {
        400: ValidationErrorResponseSerializer,
        401: UnauthorizedResponseSerializer,
        404: DetailResponseSerializer,
        501: DetailResponseSerializer,
    }
    return {code: mapping[code] for code in codes if code in mapping}
