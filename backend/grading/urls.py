from django.urls import path

from .views import (
    EssayDeleteView,
    EssayDetailView,
    EssayGradingApproveView,
    EssayGradingView,
)

urlpatterns = [
    path("<uuid:essay_id>/", EssayDetailView.as_view(), name="essay_detail"),
    path("<uuid:essay_id>/delete/", EssayDeleteView.as_view(), name="essay_delete"),
    path("<uuid:essay_id>/grading/", EssayGradingView.as_view(), name="essay_grading"),
    path(
        "<uuid:essay_id>/grading/approve/",
        EssayGradingApproveView.as_view(),
        name="essay_grading_approve",
    ),
]
