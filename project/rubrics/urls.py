from django.urls import path

from .views import (
    CriterionDetailView,
    CriterionListCreateView,
    CriterionReorderView,
    LevelDetailView,
    LevelListCreateView,
    RubricDetailView,
    RubricListCreateView,
)

urlpatterns = [
    path("", RubricListCreateView.as_view(), name="rubric_list_create"),
    path("<uuid:rubric_id>/", RubricDetailView.as_view(), name="rubric_detail"),
    path(
        "<uuid:rubric_id>/criteria/",
        CriterionListCreateView.as_view(),
        name="criterion_list_create",
    ),
    path(
        "<uuid:rubric_id>/criteria/reorder/",
        CriterionReorderView.as_view(),
        name="criterion_reorder",
    ),
    path(
        "<uuid:rubric_id>/criteria/<uuid:criterion_id>/",
        CriterionDetailView.as_view(),
        name="criterion_detail",
    ),
    path(
        "<uuid:rubric_id>/criteria/<uuid:criterion_id>/levels/",
        LevelListCreateView.as_view(),
        name="level_list_create",
    ),
    path(
        "<uuid:rubric_id>/criteria/<uuid:criterion_id>/levels/<uuid:level_id>/",
        LevelDetailView.as_view(),
        name="level_detail",
    ),
]
