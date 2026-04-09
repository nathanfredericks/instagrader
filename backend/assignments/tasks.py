import logging

from celery import chain, chord, shared_task
from django.db import transaction
from markitdown import MarkItDown

from .models import Assignment, Essay

logger = logging.getLogger(__name__)


@shared_task
def extract_essay_text(essay_id: str) -> str:
    """Extract text from a single essay file using MarkItDown.

    Updates the essay status to PROCESSING, converts the file to text,
    and stores the result in extracted_text. Sets status to FAILED on error.
    """
    try:
        essay = Essay.objects.get(id=essay_id)
    except Essay.DoesNotExist:
        logger.warning("Essay %s does not exist, skipping extraction", essay_id)
        return essay_id

    # sets status to processing immediately to prevent duplicate task pickup
    essay.status = Essay.Status.PROCESSING
    essay.failure_reason = ""
    essay.save(update_fields=["status", "failure_reason"])

    try:
        md = MarkItDown()
        result = md.convert(essay.original_file.path)
        essay.extracted_text = result.text_content
        essay.save(update_fields=["extracted_text"])
    except Exception as exc:
        logger.exception("Failed to extract text from essay %s", essay_id)
        essay.mark_failed(str(exc) or "Text extraction failed.")

    return str(essay.id)


@shared_task
def grade_essay(essay_id: str) -> None:
    """Grade a single essay using AI.

    Called after text extraction completes. Sends the extracted text
    along with the assignment rubric/prompt to an LLM for grading.
    """
    from grading.bedrock import (
        build_model_id_mapping,
        build_prompt,
        build_rubric_json,
        call_bedrock,
        parse_model_response,
    )
    from grading.models import CriterionScore, GradingResult

    try:
        essay = Essay.objects.select_related("assignment", "assignment__rubric").get(
            id=essay_id
        )
    except Essay.DoesNotExist:
        logger.warning("Essay %s does not exist, skipping grading", essay_id)
        return

    if not essay.extracted_text:
        if essay.status == Essay.Status.FAILED and essay.failure_reason:
            return
        logger.error("Essay %s has no extracted text, marking as FAILED", essay_id)
        essay.mark_failed("Essay has no extracted text.")
        return

    assignment = essay.assignment
    rubric = assignment.rubric
    criteria = rubric.criteria.prefetch_related("levels").all()

    try:
        model_id_mapping = build_model_id_mapping(criteria)
        rubric_json = build_rubric_json(model_id_mapping)
        prompt = build_prompt(
            writing_prompt=assignment.prompt,
            source_text=assignment.source_text,
            rubric_json=rubric_json,
            essay_text=essay.extracted_text,
        )

        max_grading_attempts = 3
        score_results = None
        # retries up to 3 times on ValueError (malformed model output), not on other exceptions
        for attempt in range(1, max_grading_attempts + 1):
            try:
                response_text = call_bedrock(prompt)
                score_results = parse_model_response(response_text, model_id_mapping)
                break
            except ValueError as exc:
                if attempt < max_grading_attempts:
                    logger.warning(
                        "Grading attempt %d/%d failed for essay %s: %s. Retrying.",
                        attempt,
                        max_grading_attempts,
                        essay_id,
                        exc,
                    )
                else:
                    raise ValueError(
                        f"Model response validation failed: {exc}"
                    ) from exc

        if score_results is None:
            raise RuntimeError(
                "Grading failed before a parsed score result was produced"
            )

        # creates grading result and all criterion scores in one transaction
        with transaction.atomic():
            grading_result = GradingResult.objects.create(essay=essay)
            for result in score_results:
                CriterionScore.objects.create(
                    grading_result=grading_result,
                    criterion_id=result.criterion_uuid,
                    level_id=result.level_uuid,
                    feedback=result.feedback,
                )
            essay.status = Essay.Status.GRADED
            essay.failure_reason = ""
            essay.save(update_fields=["status", "failure_reason"])

    except Exception as exc:
        logger.exception("Grading failed for essay %s", essay_id)
        essay.mark_failed(str(exc) or "Grading failed.")


@shared_task
def finalize_essay_batch(_results: list[None], assignment_id: str) -> None:
    """Transition assignment status after all essay pipelines finish."""
    try:
        assignment = Assignment.objects.get(id=assignment_id)
    except Assignment.DoesNotExist:
        logger.warning(
            "Assignment %s does not exist, skipping batch finalization", assignment_id
        )
        return

    assignment.check_grading_complete()


@shared_task(bind=True, max_retries=None)
def process_essay_batch(self, essay_ids: list[str]) -> None:
    """Dispatch one extract+grade chain per essay and finalize as a batch."""
    from grading.bedrock import ModelUnavailableError, wait_for_model

    valid_essay_ids: list[str] = []
    assignment = None
    for essay_id in essay_ids:
        try:
            essay = Essay.objects.select_related("assignment").get(id=essay_id)
        except Essay.DoesNotExist:
            logger.warning("Essay %s does not exist (deleted?), skipping", essay_id)
            continue

        if assignment is None:
            assignment = essay.assignment
        valid_essay_ids.append(str(essay.id))

    if not valid_essay_ids or assignment is None:
        return

    # bulk-fails remaining essays if model preflight check fails
    def fail_pending_essays(reason: str) -> int:
        return Essay.objects.filter(
            id__in=valid_essay_ids, status=Essay.Status.PENDING
        ).update(
            status=Essay.Status.FAILED,
            failure_reason=reason,
        )

    try:
        wait_for_model()
    except ModelUnavailableError as exc:
        failure_reason = str(exc) or "Model unavailable during preflight."
        failed_count = fail_pending_essays(failure_reason)
        logger.error(
            (
                "Model preflight unavailable for assignment %s. "
                "Marked %d pending essays as failed. Error: %s"
            ),
            assignment.id,
            failed_count,
            failure_reason,
        )
        assignment.check_grading_complete()
        return
    except Exception as exc:
        failure_reason = str(exc) or "Unexpected preflight failure."
        failed_count = fail_pending_essays(failure_reason)
        logger.exception(
            (
                "Unexpected preflight failure for assignment %s. "
                "Marked %d pending essays as failed."
            ),
            assignment.id,
            failed_count,
        )
        assignment.check_grading_complete()
        raise

    # celery chord, fans out extract+grade chains per essay then runs finalize as callback
    per_essay_workflows = [
        chain(extract_essay_text.s(essay_id), grade_essay.s())
        for essay_id in valid_essay_ids
    ]
    chord(per_essay_workflows)(finalize_essay_batch.s(str(assignment.id)))
