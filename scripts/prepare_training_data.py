import csv
import json
from pathlib import Path

from rubrics import get_rubric, get_prompt

BASE_DIR = Path(__file__).parent.parent / "dataset"
ASAP_PATH = BASE_DIR / "asap-aes" / "training_set_rel3.tsv"
ASAP_PLUS_DIR = BASE_DIR / "asap++"
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
                "domain1_score": int(row["domain1_score"])
                if row["domain1_score"]
                else None,
            }

    return essays


def load_asap_plus_scores() -> dict[int, dict]:
    scores = {}

    trait_cols_1_2 = [
        "Content",
        "Organization",
        "Word Choice",
        "Sentence Fluency",
        "Conventions",
    ]
    trait_cols_3_6 = ["Content", "Prompt Adherence", "Language", "Narrativity"]

    for prompt_num in range(1, 7):
        csv_path = ASAP_PLUS_DIR / f"Prompt-{prompt_num}.csv"

        trait_cols = trait_cols_1_2 if prompt_num <= 2 else trait_cols_3_6

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            id_col = "EssayID" if "EssayID" in reader.fieldnames else "Essay ID"

            for row in reader:
                essay_id = int(row[id_col])

                essay_scores = []
                for trait in trait_cols:
                    if trait in row and row[trait]:
                        essay_scores.append({"name": trait, "score": int(row[trait])})

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

        merged.append(
            {
                "essay_id": essay_id,
                "essay_set": essay_set,
                "prompt": get_prompt(essay_set),
                "rubric": get_rubric(essay_set),
                "essay": essay_data["essay"],
                "scores": score_data["scores"],
            }
        )

    return merged


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

essays = load_asap_essays()
scores = load_asap_plus_scores()
merged = merge_datasets(essays, scores)

output_path = OUTPUT_DIR / "merged.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2)

sample_path = OUTPUT_DIR / "sample.json"
with open(sample_path, "w", encoding="utf-8") as f:
    json.dump(merged[:3], f, indent=2)
