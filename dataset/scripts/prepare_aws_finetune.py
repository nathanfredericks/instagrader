import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from rubrics import get_rubric_by_id

BASE_DIR = Path(__file__).parent.parent / "training"
DEFAULT_INPUT_PATH = BASE_DIR / "essays_with_feedback.json"
TRAIN_OUTPUT_PATH = BASE_DIR / "aws_finetune_train.jsonl"
VALIDATION_OUTPUT_PATH = BASE_DIR / "aws_finetune_validation.jsonl"

RANDOM_SEED = 42
TRAIN_RATIO = 0.8

SYSTEM_PROMPT = """You are an expert essay grader. Score the essay according to the rubric and provide constructive feedback for each criterion.

For each criterion in the rubric, provide:
1. The criteria_id matching the rubric
2. The level_id indicating the score level achieved
3. Feedback explaining why this score was given, citing specific examples from the essay

Your response must be valid JSON matching the expected schema."""


def load_prompt(prompt_id: int) -> dict:
    path = BASE_DIR / "prompts" / f"{prompt_id}.json"
    with open(path) as f:
        return json.load(f)


def build_prompt(
    essay: str,
    rubric: list,
    prompt_text: str,
    source_text: str | None,
) -> str:
    rubric_json = json.dumps(rubric)

    parts = [f"<system>\n{SYSTEM_PROMPT}\n</system>"]

    if source_text:
        parts.append(f"<source_text>\n{source_text}\n</source_text>")

    parts.append(f"<writing_prompt>\n{prompt_text}\n</writing_prompt>")
    parts.append(f"<rubric>\n{rubric_json}\n</rubric>")
    parts.append(f"<essay>\n{essay}\n</essay>")

    return "\n\n".join(parts)


def build_completion(scores: list) -> str:
    output = {
        "scores": [
            {
                "criteria_id": s["criteria_id"],
                "level_id": s["level_id"],
                "feedback": s["feedback"],
            }
            for s in scores
        ],
    }
    return json.dumps(output)


def stratified_split(essays: list, train_ratio: float, seed: int) -> tuple[list, list]:
    random.seed(seed)

    by_prompt = defaultdict(list)
    for essay in essays:
        by_prompt[essay["prompt_id"]].append(essay)

    train_set = []
    validation_set = []

    for prompt_id, prompt_essays in by_prompt.items():
        random.shuffle(prompt_essays)
        split_idx = int(len(prompt_essays) * train_ratio)
        train_set.extend(prompt_essays[:split_idx])
        validation_set.extend(prompt_essays[split_idx:])

    random.shuffle(train_set)
    random.shuffle(validation_set)

    return train_set, validation_set


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "input_file",
    nargs="?",
    default=str(DEFAULT_INPUT_PATH),
    help="Path to essays JSON file (default: essays_with_feedback.json)",
)
args = parser.parse_args()

input_path = Path(args.input_file)
if not input_path.exists():
    print(f"Error: Input file not found: {input_path}")
    print("Run batch_generate_feedback.py first to generate essays with feedback.")
    exit(1)

with open(input_path) as f:
    essays = json.load(f)

train_essays, validation_essays = stratified_split(essays, TRAIN_RATIO, RANDOM_SEED)

print(f"Total essays: {len(essays)}")
print(f"Training: {len(train_essays)}")
print(f"Validation: {len(validation_essays)}")

for output_path, essay_set in [
    (TRAIN_OUTPUT_PATH, train_essays),
    (VALIDATION_OUTPUT_PATH, validation_essays),
]:
    with open(output_path, "w") as f:
        for essay_data in essay_set:
            prompt_data = load_prompt(essay_data["prompt_id"])
            rubric = get_rubric_by_id(essay_data["rubric_id"])

            prompt = build_prompt(
                essay_data["essay"],
                rubric,
                prompt_data["prompt"],
                prompt_data.get("source_text"),
            )

            completion = build_completion(essay_data["scores"])

            record = {"prompt": prompt, "completion": " " + completion}
            f.write(json.dumps(record) + "\n")

    print(f"Wrote {output_path}")