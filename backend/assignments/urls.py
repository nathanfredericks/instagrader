from django.urls import path

from .views import (
    AssignmentDetailView,
    AssignmentEssaysView,
    AssignmentExportCSVView,
    AssignmentExportPDFView,
    AssignmentListCreateView,
    AssignmentUploadView,
)

urlpatterns = [
    path("", AssignmentListCreateView.as_view(), name="assignment_list_create"),
    path(
        "<uuid:assignment_id>/",
        AssignmentDetailView.as_view(),
        name="assignment_detail",
    ),
    path(
        "<uuid:assignment_id>/upload/",
        AssignmentUploadView.as_view(),
        name="assignment_upload",
    ),
    path(
        "<uuid:assignment_id>/essays/",
        AssignmentEssaysView.as_view(),
        name="assignment_essays",
    ),
    path(
        "<uuid:assignment_id>/export/csv/",
        AssignmentExportCSVView.as_view(),
        name="assignment_export_csv",
    ),
    path(
        "<uuid:assignment_id>/export/pdf/<uuid:essay_id>/",
        AssignmentExportPDFView.as_view(),
        name="assignment_export_pdf",
    ),
]
