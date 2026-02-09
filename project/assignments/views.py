import csv
import io
import mimetypes
import os
import uuid
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.db.models import Count
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer  # type: ignore[reportUnknownVariableType]
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from instagrader.schema import DetailResponseSerializer, error_responses

from .models import Assignment, Essay
from .serializers import (
    AssignmentListSerializer,
    AssignmentSerializer,
    EssayListSerializer,
)
from .tasks import process_essay_batch

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _sanitize_filename(filename: str) -> str:
    """Sanitize a filename for use in Content-Disposition headers."""
    sanitized = filename.replace('"', "").replace("\n", "").replace("\r", "")
    sanitized = sanitized.encode("ascii", "ignore").decode("ascii")
    return sanitized or "download"


def _is_valid_zip_entry(name: str) -> bool:
    """Return True if a ZIP entry should be processed."""
    basename = os.path.basename(name)
    if not basename:
        return False
    if basename.startswith("."):
        return False
    if "__MACOSX" in name:
        return False
    _, ext = os.path.splitext(basename)
    return ext.lower() in ALLOWED_EXTENSIONS


class AssignmentListCreateView(APIView):
    """List user's assignments or create a new assignment."""

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_assignment_list",
        description="List all assignments owned by the authenticated user.",
        responses={
            200: AssignmentListSerializer(many=True),
            **error_responses(401),
        },
    )
    def get(self, request: AuthenticatedRequest) -> Response:
        assignments = (
            Assignment.objects.filter(user=request.user)
            .annotate(essay_count=Count("essays"))
            .order_by("-created_at")
        )
        serializer = AssignmentListSerializer(assignments, many=True)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_assignment_create",
        description="Create a new assignment linked to a rubric.",
        request=AssignmentSerializer,
        responses={
            201: AssignmentSerializer,
            **error_responses(400, 401),
        },
        examples=[
            OpenApiExample(
                "Invalid rubric owner",
                value={"rubric": ["You can only use your own rubrics."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request: AuthenticatedRequest) -> Response:
        serializer = AssignmentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class AssignmentDetailView(APIView):
    """Get, update, or delete an assignment."""

    def _get_assignment(
        self, request: AuthenticatedRequest, assignment_id: uuid.UUID
    ) -> Assignment | None:
        try:
            return Assignment.objects.prefetch_related("essays").get(
                id=assignment_id, user=request.user
            )
        except Assignment.DoesNotExist:
            return None

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_assignment_retrieve",
        description="Retrieve an assignment with its nested essays.",
        responses={
            200: AssignmentSerializer,
            **error_responses(401, 404),
        },
    )
    def get(self, request: AuthenticatedRequest, assignment_id: uuid.UUID) -> Response:
        assignment = self._get_assignment(request, assignment_id)
        if assignment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_assignment_partial_update",
        description="Partially update an assignment's title, prompt, source_text, or rubric.",
        request=AssignmentSerializer,
        responses={
            200: AssignmentSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(
        self, request: AuthenticatedRequest, assignment_id: uuid.UUID
    ) -> Response:
        assignment = self._get_assignment(request, assignment_id)
        if assignment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AssignmentSerializer(
            assignment, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_assignment_delete",
        description="Delete an assignment and all its essays.",
        responses={
            204: None,
            **error_responses(401, 404),
        },
    )
    def delete(
        self, request: AuthenticatedRequest, assignment_id: uuid.UUID
    ) -> Response:
        assignment = self._get_assignment(request, assignment_id)
        if assignment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignmentUploadView(APIView):
    """Upload essays (zip file or individual) to an assignment."""

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_essay_upload",
        description=(
            "Upload essay files to an assignment. Accepts individual PDF, DOCX, or TXT files, "
            "or a ZIP archive containing multiple files. Triggers async text extraction."
        ),
        request={
            "multipart/form-data": inline_serializer(
                name="AssignmentUploadRequest",
                fields={
                    "files": drf_serializers.ListField(
                        child=drf_serializers.FileField(),
                        help_text="One or more files (PDF, DOCX, TXT) or a ZIP archive.",
                    ),
                },
            ),
        },
        responses={
            201: EssayListSerializer(many=True),
            400: DetailResponseSerializer,
            **error_responses(401, 404),
        },
        examples=[
            OpenApiExample(
                "No files provided",
                value={"detail": "No files provided."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Invalid ZIP file",
                value={"detail": "Invalid or corrupt ZIP file."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Empty ZIP file",
                value={"detail": "ZIP contains no valid files."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Empty file",
                value={"detail": "Empty file."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Unsupported file type",
                value={"detail": "Unsupported file type: .jpg"},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request: AuthenticatedRequest, assignment_id: uuid.UUID) -> Response:
        try:
            assignment = Assignment.objects.get(id=assignment_id, user=request.user)
        except Assignment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"detail": "No files provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_essays: list[Essay] = []

        for uploaded_file in files:
            _, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower()

            if ext == ".zip":
                essays = self._handle_zip(uploaded_file, assignment)
                if essays is None:
                    return Response(
                        {"detail": "Invalid or corrupt ZIP file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not essays:
                    return Response(
                        {"detail": "ZIP contains no valid files."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                created_essays.extend(essays)
            elif ext in ALLOWED_EXTENSIONS:
                if uploaded_file.size == 0:
                    return Response(
                        {"detail": "Empty file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                essay = Essay.objects.create(
                    assignment=assignment,
                    file_name=uploaded_file.name,
                    original_file=uploaded_file,
                    status=Essay.Status.PENDING,
                )
                created_essays.append(essay)
            else:
                return Response(
                    {"detail": f"Unsupported file type: {ext}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        essay_ids = [str(e.id) for e in created_essays]
        process_essay_batch.delay(essay_ids)

        serializer = EssayListSerializer(created_essays, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]

    def _handle_zip(
        self, uploaded_file: UploadedFile, assignment: Assignment
    ) -> list[Essay] | None:
        """Extract essays from a ZIP file. Returns list of essays or None if corrupt."""
        try:
            zip_bytes = uploaded_file.read()
            zip_buffer = io.BytesIO(zip_bytes)
            zf = zipfile.ZipFile(zip_buffer)
        except Exception:
            return None

        essays: list[Essay] = []
        for entry_name in zf.namelist():
            if not _is_valid_zip_entry(entry_name):
                continue
            content = zf.read(entry_name)
            basename = os.path.basename(entry_name)
            file_obj = SimpleUploadedFile(basename, content)
            essay = Essay.objects.create(
                assignment=assignment,
                file_name=basename,
                original_file=file_obj,
                status=Essay.Status.PENDING,
            )
            essays.append(essay)

        zf.close()
        return essays


class AssignmentEssaysView(APIView):
    """List essays in an assignment."""

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_essay_list",
        description="List all essays in an assignment.",
        responses={
            200: EssayListSerializer(many=True),
            **error_responses(401, 404),
        },
    )
    def get(self, request: AuthenticatedRequest, assignment_id: uuid.UUID) -> Response:
        try:
            assignment = Assignment.objects.get(id=assignment_id, user=request.user)
        except Assignment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        essays = assignment.essays.all()
        serializer = EssayListSerializer(essays, many=True)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]


class AssignmentExportCSVView(APIView):
    """Export grades to CSV."""

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_export_csv",
        description="Export assignment grades as a CSV file download.",
        responses={
            (200, "text/csv"): OpenApiTypes.BINARY,
            **error_responses(401, 404),
        },
    )
    def get(
        self, request: AuthenticatedRequest, assignment_id: uuid.UUID
    ) -> HttpResponse:
        try:
            assignment = Assignment.objects.get(id=assignment_id, user=request.user)
        except Assignment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(content_type="text/csv")
        sanitized_title = _sanitize_filename(assignment.title)
        response["Content-Disposition"] = (
            f'attachment; filename="{sanitized_title}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["file_name", "status"])
        for essay in assignment.essays.all():
            writer.writerow([essay.file_name, essay.status])

        return response


class AssignmentExportPDFView(APIView):
    """Export essay's original uploaded file."""

    @extend_schema(
        tags=["assignments"],
        operation_id="assignments_export_file",
        description="Download an essay's original uploaded file.",
        responses={
            (200, "application/octet-stream"): OpenApiTypes.BINARY,
            **error_responses(401, 404),
        },
    )
    def get(
        self,
        request: AuthenticatedRequest,
        assignment_id: uuid.UUID,
        essay_id: uuid.UUID,
    ) -> HttpResponse:
        try:
            assignment = Assignment.objects.get(id=assignment_id, user=request.user)
        except Assignment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            essay = Essay.objects.get(id=essay_id, assignment=assignment)
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        content_type, _ = mimetypes.guess_type(essay.file_name)
        if content_type is None:
            content_type = "application/octet-stream"

        essay.original_file.open("rb")
        try:
            content = essay.original_file.read()
        finally:
            essay.original_file.close()

        sanitized_name = _sanitize_filename(essay.file_name)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{sanitized_name}"'
        return response
