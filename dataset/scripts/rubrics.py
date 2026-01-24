import json
from pathlib import Path

TRAINING_DIR = Path(__file__).parent.parent / "training"


def _load_prompt(essay_set: int) -> dict:
    path = TRAINING_DIR / "prompts" / f"{essay_set}.json"
    with open(path) as f:
        return json.load(f)


def _load_rubric(rubric_id: int) -> dict:
    path = TRAINING_DIR / "rubrics" / f"{rubric_id}.json"
    with open(path) as f:
        return json.load(f)


def get_rubric(essay_set: int) -> list:
    if essay_set in (1, 2):
        return _load_rubric(1)["criteria"]
    if essay_set in (3, 4, 5, 6):
        return _load_rubric(2)["criteria"]
    raise ValueError(f"Invalid essay set: {essay_set}")


def get_rubric_by_id(rubric_id: int) -> list:
    return _load_rubric(rubric_id)["criteria"]


def get_rubric_id(essay_set: int) -> int:
    if essay_set in (1, 2):
        return 1
    if essay_set in (3, 4, 5, 6):
        return 2
    raise ValueError(f"Invalid essay set: {essay_set}")


def get_prompt(essay_set: int) -> str:
    return _load_prompt(essay_set)["prompt"]


def get_source_text(essay_set: int) -> str | None:
    return _load_prompt(essay_set)["source_text"]


def get_prompt_id(essay_set: int) -> int:
    return essay_set


def get_criteria_names(essay_set: int) -> list[str]:
    rubric = get_rubric(essay_set)
    return [criterion["name"] for criterion in rubric]


def get_score_mapping(essay_set: int, name: str, score: int) -> dict | None:
    rubric = get_rubric(essay_set)
    for criterion in rubric:
        if criterion["name"] == name:
            criteria_id = criterion["id"]
            for level in criterion["levels"]:
                if level["score"] == score:
                    return {"criteria_id": criteria_id, "level_id": level["id"]}
    return None
