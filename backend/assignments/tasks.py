import logging

from celery import shared_task
from markitdown import MarkItDown

from .models import Essay

logger = logging.getLogger(__name__)


@shared_task
def extract_essay_text(essay_id: str) -> str:
    """Extract text from a single essay file using MarkItDown.

    Updates the essay status to PROCESSING, converts the file to text,
    and stores the result in extracted_text. Sets status to FAILED on error.
    """
    essay = Essay.objects.get(id=essay_id)
    essay.status = Essay.Status.PROCESSING
    essay.save(update_fields=["status"])

    try:
        md = MarkItDown()
        result = md.convert(essay.original_file.path)
        essay.extracted_text = result.text_content
        essay.save(update_fields=["extracted_text"])
    except Exception:
        logger.exception("Failed to extract text from essay %s", essay_id)
        essay.status = Essay.Status.FAILED
        essay.save(update_fields=["status"])
        raise

    return str(essay.id)


@shared_task
def grade_essay(essay_id: str) -> None:
    """Grade a single essay using AI.

    Called after text extraction completes. Sends the extracted text
    along with the assignment rubric/prompt to an LLM for grading.
    """
    # TODO: implement AI grading pipeline
    logger.info("grade_essay called for essay %s (not yet implemented)", essay_id)


@shared_task
def process_essay_batch(essay_ids: list[str]) -> None:
    """Orchestrate the essay processing pipeline.

    For each essay in the batch:
      1. Extract text from the uploaded file
      2. Grade the essay using AI

    Each essay is processed independently so one failure doesn't
    block the rest of the batch.
    """
    for essay_id in essay_ids:
        try:
            extract_essay_text(essay_id)
        except Exception:
            logger.exception(
                "Text extraction failed for essay %s, skipping grading", essay_id
            )
            continue

        try:
            grade_essay(essay_id)
        except Exception:
            logger.exception("Grading failed for essay %s", essay_id)
            continue
