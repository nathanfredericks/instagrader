from django.urls import path

from .views import (
    CriterionDetailView,
    CriterionListCreateView,
    CriterionReorderView,
    LevelDetailView,
    LevelListCreateView,
    RubricDetailView,
    RubricDuplicateView,
    RubricListCreateView,
    RubricStructureView,
    RubricTemplateInstantiateView,
    RubricTemplateListView,
)

urlpatterns = [
    path("templates/", RubricTemplateListView.as_view(), name="rubric_template_list"),
    path(
        "templates/<str:template_key>/instantiate/",
        RubricTemplateInstantiateView.as_view(),
        name="rubric_template_instantiate",
    ),
    path("", RubricListCreateView.as_view(), name="rubric_list_create"),
    path("<uuid:rubric_id>/", RubricDetailView.as_view(), name="rubric_detail"),
    path(
        "<uuid:rubric_id>/duplicate/",
        RubricDuplicateView.as_view(),
        name="rubric_duplicate",
    ),
    path(
        "<uuid:rubric_id>/structure/",
        RubricStructureView.as_view(),
        name="rubric_structure_update",
    ),
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
