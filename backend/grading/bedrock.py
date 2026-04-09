"""AWS Bedrock client for AI essay grading.

Adapted from model-poc/main.py. Handles:
- Prompt building with XML tags
- Bedrock API calls
- Response parsing
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Iterable

import boto3
import json_repair
from botocore.exceptions import ClientError
from django.conf import settings

from rubrics.models import RubricCriterion

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 60
PROBE_INTERVAL_SECONDS = 5
PROBE_TIMEOUT_SECONDS = 5 * 60
PROBE_MAX_ATTEMPTS = (PROBE_TIMEOUT_SECONDS // PROBE_INTERVAL_SECONDS) + 1
RETRYABLE_PROBE_ERROR_CODES = {"ModelNotReadyException", "ModelErrorException"}


def _is_anthropic_model(model_id: str) -> bool:
    """Check if the model ID refers to an Anthropic model on Bedrock."""
    return "anthropic" in model_id.lower()


class ModelNotReadyError(Exception):
    """Raised when the Bedrock model is still not ready after all retries."""


class ModelUnavailableError(Exception):
    """Raised when Bedrock probe retries are exhausted for retryable errors."""


@dataclass(frozen=True)
class ModelIDMapping:
    """Mapping between DB UUID IDs and numeric model IDs."""

    rubric: list[dict[str, object]]
    criterion_uuid_to_numeric: dict[uuid.UUID, int]
    criterion_numeric_to_uuid: dict[int, uuid.UUID]
    level_uuid_to_numeric_by_criterion: dict[int, dict[uuid.UUID, int]]
    level_numeric_to_uuid_by_criterion: dict[int, dict[int, uuid.UUID]]


def build_model_id_mapping(criteria: Iterable[RubricCriterion]) -> ModelIDMapping:
    """maps uuid criterion/level ids to integers, the model expects numeric ids in its output schema"""
    rubric_list: list[dict[str, object]] = []
    criterion_uuid_to_numeric: dict[uuid.UUID, int] = {}
    criterion_numeric_to_uuid: dict[int, uuid.UUID] = {}
    level_uuid_to_numeric_by_criterion: dict[int, dict[uuid.UUID, int]] = {}
    level_numeric_to_uuid_by_criterion: dict[int, dict[int, uuid.UUID]] = {}

    for criterion_idx, criterion in enumerate(criteria, start=1):
        criterion_uuid_to_numeric[criterion.id] = criterion_idx
        criterion_numeric_to_uuid[criterion_idx] = criterion.id

        level_uuid_to_numeric: dict[uuid.UUID, int] = {}
        level_numeric_to_uuid: dict[int, uuid.UUID] = {}
        levels_payload: list[dict[str, object]] = []

        for level_idx, level in enumerate(criterion.levels.all(), start=1):
            level_uuid_to_numeric[level.id] = level_idx
            level_numeric_to_uuid[level_idx] = level.id
            levels_payload.append(
                {
                    "id": level_idx,
                    "score": level.score,
                    "descriptor": level.descriptor,
                }
            )

        level_uuid_to_numeric_by_criterion[criterion_idx] = level_uuid_to_numeric
        level_numeric_to_uuid_by_criterion[criterion_idx] = level_numeric_to_uuid
        rubric_list.append(
            {
                "id": criterion_idx,
                "name": criterion.name,
                "levels": levels_payload,
            }
        )

    return ModelIDMapping(
        rubric=rubric_list,
        criterion_uuid_to_numeric=criterion_uuid_to_numeric,
        criterion_numeric_to_uuid=criterion_numeric_to_uuid,
        level_uuid_to_numeric_by_criterion=level_uuid_to_numeric_by_criterion,
        level_numeric_to_uuid_by_criterion=level_numeric_to_uuid_by_criterion,
    )


def build_rubric_json(model_id_mapping: ModelIDMapping) -> str:
    """Serialize the numeric rubric schema that the fine-tuned model expects."""
    return json.dumps(model_id_mapping.rubric)


def build_prompt(
    writing_prompt: str,
    source_text: str,
    rubric_json: str,
    essay_text: str,
) -> str:
    """xml-tagged prompt format matches the fine-tuning training data"""
    source_text_section = ""
    if source_text:
        source_text_section = f"""<source_text>
{source_text}
</source_text>

"""

    rubric_data = json.loads(rubric_json)
    expected_scores = []
    for criterion in rubric_data:
        expected_scores.append(
            {
                "criteria_id": criterion["id"],
                "level_id": "<integer level_id from this criterion's levels>",
                "feedback": (
                    "<feedback explaining the score with specific examples"
                    " from the essay>"
                ),
            }
        )
    # tells the model exactly what json structure to return
    output_schema = json.dumps({"scores": expected_scores}, indent=2)

    system_instructions = """\
<system>
You are an expert essay grader. Score the essay according \
to the rubric and provide constructive feedback for each \
criterion.

For each criterion in the rubric, provide:
1. The criteria_id -- copy the exact integer "id" value \
from the criterion in the rubric
2. The level_id -- copy the exact integer "id" value from \
one of the criterion's levels in the rubric
3. Feedback explaining why this score was given, citing \
specific examples from the essay

IMPORTANT:
- IDs must be integers copied exactly from the rubric JSON.
- Return exactly one score item per criterion.
- The output must be a JSON object with a single top-level key "scores".
- Do not use UUID values.
- Do not wrap the JSON in markdown code fences.
- Do not include any text outside the JSON object.

Your response must be valid JSON matching the expected schema.
</system>

"""

    prompt = f"""{system_instructions}{source_text_section}<writing_prompt>
{writing_prompt}
</writing_prompt>

<rubric>
{rubric_json}
</rubric>

<essay>
{essay_text}
</essay>

Your response must be valid JSON that matches this exact schema:

<output_schema>
{output_schema}
</output_schema>

Provide your grading with specific feedback for each \
criterion. Your entire response should be only the JSON \
output with no additional text, commentary, or explanation \
outside the JSON structure."""

    return prompt


def call_bedrock(prompt_text: str) -> str:
    """Call AWS Bedrock API and return the model's response text.

    Retries up to MAX_RETRIES times on ModelNotReadyException, waiting
    RETRY_DELAY_SECONDS between attempts to handle imported model cold starts.
    """
    bedrock_config = settings.BEDROCK

    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=bedrock_config["REGION"],
    )

    model_id = bedrock_config["MODEL_ID"]
    is_anthropic = _is_anthropic_model(model_id)

    request_body = {
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": bedrock_config["TEMPERATURE"],
    }
    if is_anthropic:
        request_body["anthropic_version"] = "bedrock-2023-05-31"
        request_body["max_tokens"] = bedrock_config["MAX_COMPLETION_TOKENS"]
    else:
        request_body["max_completion_tokens"] = bedrock_config["MAX_COMPLETION_TOKENS"]

    # handles ModelNotReadyException during cold start, backs off between attempts
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
            )
            break
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code != "ModelNotReadyException":
                raise
            if attempt == MAX_RETRIES:
                logger.error(
                    "Model not ready after %d attempts, giving up", MAX_RETRIES
                )
                raise ModelNotReadyError(
                    f"Model not ready after {MAX_RETRIES} retries"
                ) from exc
            logger.warning(
                "Model not ready (attempt %d/%d), retrying in %ds",
                attempt,
                MAX_RETRIES,
                RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)

    response_body = json.loads(response["body"].read())
    logger.debug("Bedrock raw response body: %s", response_body)

    # anthropic models use content array, openai-compatible use choices array, reasoning models use reasoning_content
    if is_anthropic:
        content_blocks = response_body.get("content", [])
        output_text = "".join(
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        )
    else:
        message = response_body["choices"][0]["message"]
        output_text = message.get("content", "") or ""

        if not output_text.strip():
            output_text = message.get("reasoning_content", "") or ""

    output_text = output_text.strip()

    if not output_text:
        logger.error(
            "Model returned empty response. Raw response: %s",
            response_body,
        )
        raise ValueError("Model returned empty response")

    return output_text


def wait_for_model() -> None:
    """preflight probe ensures model is warm before starting a batch"""
    bedrock_config = settings.BEDROCK

    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=bedrock_config["REGION"],
    )

    model_id = bedrock_config["MODEL_ID"]
    is_anthropic = _is_anthropic_model(model_id)

    probe_body = {
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0,
    }
    if is_anthropic:
        probe_body["anthropic_version"] = "bedrock-2023-05-31"
        probe_body["max_tokens"] = 1
    else:
        probe_body["max_completion_tokens"] = 1

    for attempt in range(1, PROBE_MAX_ATTEMPTS + 1):
        try:
            bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(probe_body),
            )
            return
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code not in RETRYABLE_PROBE_ERROR_CODES:
                raise
            if attempt == PROBE_MAX_ATTEMPTS:
                raw_error = str(exc)
                logger.error(
                    (
                        "Model unavailable after probing every %ds for %ds "
                        "(%d/%d attempts), giving up. Last error: %s"
                    ),
                    PROBE_INTERVAL_SECONDS,
                    PROBE_TIMEOUT_SECONDS,
                    attempt,
                    PROBE_MAX_ATTEMPTS,
                    raw_error,
                )
                raise ModelUnavailableError(raw_error) from exc
            logger.warning(
                (
                    "Model unavailable on probe (attempt %d/%d, code=%s), "
                    "retrying in %ds"
                ),
                attempt,
                PROBE_MAX_ATTEMPTS,
                error_code,
                PROBE_INTERVAL_SECONDS,
            )
            time.sleep(PROBE_INTERVAL_SECONDS)


@dataclass
class CriterionScoreResult:
    """Parsed score for a single criterion."""

    criterion_uuid: uuid.UUID
    level_uuid: uuid.UUID
    feedback: str


def _parse_numeric_id(value: object, field_name: str) -> int:
    """model sometimes returns ids as strings, coerce to int"""
    parsed: int | None = None

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            parsed = int(stripped)
        else:
            raise ValueError(f"{field_name} must be an integer")
    else:
        raise ValueError(f"{field_name} must be an integer")

    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")

    return parsed


def parse_model_response(
    response_text: str,
    model_id_mapping: ModelIDMapping,
) -> list[CriterionScoreResult]:
    """validates structure then checks all criterion ids exist and no duplicates"""
    data = json_repair.loads(response_text)
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object with a 'scores' list")

    scores = data.get("scores")
    if not isinstance(scores, list):
        raise ValueError("Model response missing 'scores' list")

    expected_criteria_ids = set(model_id_mapping.criterion_numeric_to_uuid.keys())
    seen_criteria_ids: set[int] = set()
    results: list[CriterionScoreResult] = []

    for idx, score in enumerate(scores, start=1):
        if not isinstance(score, dict):
            raise ValueError(f"Score entry at index {idx} must be an object")

        criteria_id = _parse_numeric_id(score.get("criteria_id"), "criteria_id")
        if criteria_id not in expected_criteria_ids:
            raise ValueError(f"Unknown criteria_id: {criteria_id}")
        if criteria_id in seen_criteria_ids:
            raise ValueError(f"Duplicate criteria_id in model response: {criteria_id}")

        level_id = _parse_numeric_id(score.get("level_id"), "level_id")
        allowed_levels = model_id_mapping.level_numeric_to_uuid_by_criterion.get(
            criteria_id, {}
        )
        if level_id not in allowed_levels:
            raise ValueError(
                f"Unknown level_id {level_id} for criteria_id {criteria_id}"
            )

        feedback_raw = str(score.get("feedback", "")).strip()
        if not feedback_raw:
            raise ValueError(f"Missing feedback for criteria_id {criteria_id}")

        seen_criteria_ids.add(criteria_id)
        criterion_uuid = model_id_mapping.criterion_numeric_to_uuid[criteria_id]
        level_uuid = allowed_levels[level_id]

        results.append(
            CriterionScoreResult(
                criterion_uuid=criterion_uuid,
                level_uuid=level_uuid,
                feedback=feedback_raw,
            )
        )

    missing_criteria = sorted(expected_criteria_ids - seen_criteria_ids)
    if missing_criteria:
        missing_csv = ", ".join(str(criterion_id) for criterion_id in missing_criteria)
        raise ValueError(
            f"Model response missing scores for criteria_id(s): {missing_csv}"
        )

    return results
