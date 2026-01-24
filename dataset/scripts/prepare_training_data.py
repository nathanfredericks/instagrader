import csv
import json
from pathlib import Path

from rubrics import get_rubric_id, get_prompt_id, get_score_mapping, get_rubric

BASE_DIR = Path(__file__).parent.parent
ASAP_PATH = BASE_DIR / "asap-aes" / "training_set_rel3.tsv"
ASAP_PLUS_PLUS_DIR = BASE_DIR / "asap++"
OUTPUT_DIR = BASE_DIR / "training"


def load_asap_essays() -> dict[int, dict]:
    essays = {}

    with open(ASAP_PATH, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            essay_set = int(row["essay_set"])
            if essay_set > 6:
                continue

            essay_id = int(row["essay_id"])
            essays[essay_id] = {
                "essay_id": essay_id,
                "essay_set": essay_set,
                "essay": row["essay"],
            }

    return essays


def load_asap_plus_plus_scores() -> dict[int, dict]:
    scores = {}

    for prompt_num in range(1, 7):
        csv_path = ASAP_PLUS_PLUS_DIR / f"Prompt-{prompt_num}.csv"
        rubric = get_rubric(prompt_num)
        criteria_cols = [c["name"] for c in rubric]

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            id_col = (
                "EssayID"
                if reader.fieldnames and "EssayID" in reader.fieldnames
                else "Essay ID"
            )

            for row in reader:
                essay_id = int(row[id_col])

                essay_scores = []
                for criteria_col in criteria_cols:
                    if criteria_col in row and row[criteria_col]:
                        essay_scores.append(
                            {"name": criteria_col, "score": int(row[criteria_col])}
                        )

                scores[essay_id] = {
                    "essay_id": essay_id,
                    "prompt_num": prompt_num,
                    "scores": essay_scores,
                }

    return scores


def merge_datasets(essays: dict, scores: dict) -> list[dict]:
    merged = []

    for essay_id, essay_data in essays.items():
        if essay_id not in scores:
            continue

        score_data = scores[essay_id]
        essay_set = essay_data["essay_set"]

        mapped_scores = [
            mapping
            for s in score_data["scores"]
            if (mapping := get_score_mapping(essay_set, s["name"], s["score"]))
            is not None
        ]

        merged.append(
            {
                "id": essay_id,
                "prompt_id": get_prompt_id(essay_set),
                "rubric_id": get_rubric_id(essay_set),
                "essay": essay_data["essay"],
                "scores": mapped_scores,
            }
        )

    return merged


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

essays = load_asap_essays()
scores = load_asap_plus_plus_scores()
merged = merge_datasets(essays, scores)

output_path = OUTPUT_DIR / "essays.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2)

sample_path = OUTPUT_DIR / "sample.json"
with open(sample_path, "w", encoding="utf-8") as f:
    json.dump(merged[:3], f, indent=2)
