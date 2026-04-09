import argparse
import json
import sys
from pathlib import Path

import datetime

import boto3
from json_repair import repair_json

from rubrics import get_rubric_by_id

AWS_REGION = "us-east-1"
boto3.setup_default_session(region_name=AWS_REGION)

BASE_DIR = Path(__file__).parent.parent / "training"
INPUT_PATH = BASE_DIR / "essays.json"
BATCH_INPUT_PATH = BASE_DIR / "batch_input.jsonl"
OUTPUT_PATH = BASE_DIR / "essays_with_feedback.json"

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
S3_BUCKET = "instagrader-dataset-generate-feedback"
BEDROCK_ROLE_ARN = "arn:aws:iam::605134461989:role/BedrockBatchInferenceRole"
MAX_TOKENS = 2048


def load_prompt(prompt_id: int) -> dict:
    path = BASE_DIR / "prompts" / f"{prompt_id}.json"
    with open(path) as f:
        return json.load(f)


def build_score_section(scores: list, rubric: list) -> list:
    score_items = []
    for score in scores:
        criteria_id = score["criteria_id"]
        level_id = score["level_id"]
        criterion = next(
            criteria for criteria in rubric if criteria["id"] == criteria_id
        )
        level = next(level for level in criterion["levels"] if level["id"] == level_id)
        score_items.append(
            {
                "id": criteria_id,
                "name": criterion["name"],
                "level": {"id": level_id, "descriptor": level["descriptor"]},
            }
        )
    return score_items


def build_output_schema(scores: list, rubric: list) -> str:
    schema_items = []
    for score in scores:
        criteria_id = score["criteria_id"]
        level_id = score["level_id"]
        criterion = next(
            criteria for criteria in rubric if criteria["id"] == criteria_id
        )
        level = next(level for level in criterion["levels"] if level["id"] == level_id)
        schema_items.append(
            {
                "id": criteria_id,
                "name": criterion["name"],
                "level": {
                    "id": level_id,
                    "descriptor": level["descriptor"],
                    "feedback": "<feedback>",
                },
            }
        )
    return json.dumps({"score": schema_items})


def build_prompt(
    essay: str,
    scores: list,
    rubric: list,
    prompt_text: str,
    source_text: str | None,
) -> str:
    score_section = build_score_section(scores, rubric)
    output_schema = build_output_schema(scores, rubric)

    if source_text:
        source_text_section = f"""Here is the source text that the essay is based on:

<source_text>
{source_text}
</source_text>

"""
        intro = "You are an expert essay grader tasked with providing constructive feedback on a student's essay. You will be given a source text, a writing prompt, the student's essay, scores that have already been assigned according to a rubric, and a JSON schema for your output."
    else:
        source_text_section = ""
        intro = "You are an expert essay grader tasked with providing constructive feedback on a student's essay. You will be given a writing prompt, the student's essay, scores that have already been assigned according to a rubric, and a JSON schema for your output."

    return f"""{intro}

{source_text_section}Here is the writing prompt the student was responding to:

<writing_prompt>
{prompt_text}
</writing_prompt>

Here is the student's essay:

<essay>
{essay}
</essay>

Here are the scores that have already been assigned to this essay:

<score>
{json.dumps(score_section)}
</score>

Your task is to generate constructive feedback that explains why each score was given based on the rubric criteria. For each score in the rubric, you must write between 1 and 3 sentences that include:

1. What the student did well (if applicable based on the score)
2. What could be improved (if applicable based on the score)
3. Specific examples from the essay that justify the score

Follow these writing guidelines strictly:
- Write in a clear, straightforward manner using direct language and simple vocabulary
- Avoid complex jargon, overly technical terms, and unnecessarily complicated sentence structures
- Keep sentences concise and easy to follow, similar to high school senior-level writing
- Use active voice whenever possible
- Get straight to the point without unnecessary elaboration
- Maintain a conversational yet informative tone that is accessible to a general audience
- Do not use an em dash (—) anywhere in your feedback

Your response must be valid JSON that matches this exact schema:

<output_schema>
{output_schema}
</output_schema>

Generate feedback for each scoring criterion in the rubric. Make sure your feedback directly references specific elements from the student's essay to support each score. Your entire response should be only the JSON output with no additional text, commentary, or explanation outside the JSON structure."""


def cmd_prepare(_args):
    with open(INPUT_PATH, "r") as f:
        essays = json.load(f)

    with open(BATCH_INPUT_PATH, "w") as f:
        for essay_data in essays:
            prompt_id = essay_data["prompt_id"]
            rubric_id = essay_data["rubric_id"]
            prompt_data = load_prompt(prompt_id)
            rubric = get_rubric_by_id(rubric_id)

            prompt = build_prompt(
                essay_data["essay"],
                essay_data["scores"],
                rubric,
                prompt_data["prompt"],
                prompt_data.get("source_text"),
            )

            record = {
                "recordId": str(essay_data["id"]),
                "modelInput": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": MAX_TOKENS,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": "{"},
                    ],
                },
            }

            f.write(json.dumps(record) + "\n")


def cmd_submit(_args):
    s3_client = boto3.client("s3")
    bedrock_client = boto3.client("bedrock")

    s3_input_key = "input/batch_input.jsonl"
    s3_input_uri = f"s3://{S3_BUCKET}/input/"
    s3_output_uri = f"s3://{S3_BUCKET}/output/"

    s3_client.upload_file(str(BATCH_INPUT_PATH), S3_BUCKET, s3_input_key)

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    job_name = f"instagrader-dataset-generate-feedback-{timestamp}"

    bedrock_client.create_model_invocation_job(
        jobName=job_name,
        modelId=MODEL_ID,
        roleArn=BEDROCK_ROLE_ARN,
        inputDataConfig={"s3InputDataConfig": {"s3Uri": s3_input_uri}},
        outputDataConfig={"s3OutputDataConfig": {"s3Uri": s3_output_uri}},
    )


def cmd_download(_args):
    bedrock_client = boto3.client("bedrock")
    s3_client = boto3.client("s3")

    jobs = bedrock_client.list_model_invocation_jobs(
        maxResults=1, sortBy="CreationTime", sortOrder="Descending"
    )

    if not jobs.get("invocationJobSummaries"):
        print("No batch jobs found.")
        sys.exit(1)

    job = jobs["invocationJobSummaries"][0]
    job_arn = job["jobArn"]

    response = bedrock_client.get_model_invocation_job(jobIdentifier=job_arn)

    if response["status"] != "Completed":
        print(f"Error: Job status is '{response['status']}', not 'Completed'")
        sys.exit(1)

    output_uri = response["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]

    bucket = output_uri.split("/")[2]
    prefix = "/".join(output_uri.split("/")[3:])

    paginator = s3_client.get_paginator("list_objects_v2")
    output_files = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".jsonl.out"):
                output_files.append(obj["Key"])

    if not output_files:
        print("Error: No output files found")
        sys.exit(1)

    results_by_id = {}
    errors = []

    for output_key in output_files:
        response = s3_client.get_object(Bucket=bucket, Key=output_key)
        content = response["Body"].read().decode("utf-8")

        for line in content.strip().split("\n"):
            if not line:
                continue

            record = json.loads(line)
            record_id = record["recordId"]

            if "error" in record:
                errors.append({"id": record_id, "error": record["error"]})
                continue

            model_output = record.get("modelOutput", {})
            content_blocks = model_output.get("content", [])

            if not content_blocks:
                errors.append({"id": record_id, "error": "No content in response"})
                continue

            text = content_blocks[0].get("text", "")
            json_text = "{" + text

            try:
                repaired_json = repair_json(json_text)
                feedback_data = json.loads(repaired_json)
                results_by_id[record_id] = feedback_data.get("score", [])
            except (json.JSONDecodeError, Exception) as e:
                errors.append({"id": record_id, "error": f"JSON parse error: {e}"})

    with open(INPUT_PATH, "r") as f:
        essays = json.load(f)

    final_results = []

    for essay_data in essays:
        essay_id = str(essay_data["id"])
        feedback_list = results_by_id.get(essay_id, [])

        feedback_by_id = {}
        for f in feedback_list:
            try:
                feedback_by_id[f["id"]] = f["level"]["feedback"]
            except (KeyError, TypeError):
                continue

        merged_scores = []
        for eval_item in essay_data["scores"]:
            merged_scores.append(
                {
                    "criteria_id": eval_item["criteria_id"],
                    "level_id": eval_item["level_id"],
                    "feedback": feedback_by_id.get(eval_item["criteria_id"], ""),
                }
            )

        final_results.append(
            {
                "id": essay_data["id"],
                "prompt_id": essay_data["prompt_id"],
                "rubric_id": essay_data["rubric_id"],
                "essay": essay_data["essay"],
                "scores": merged_scores,
            }
        )

    with open(OUTPUT_PATH, "w") as f:
        json.dump(final_results, f, indent=2)

    if errors:
        error_path = BASE_DIR / "batch_errors.json"
        with open(error_path, "w") as f:
            json.dump(errors, f, indent=2)
        print(f"Errors saved to: {error_path}")


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=__doc__,
)
subparsers = parser.add_subparsers(dest="command", required=True)

subparsers.add_parser("prepare", help="Create JSONL input file")

submit_parser = subparsers.add_parser(
    "submit", help="Upload to S3 and submit batch job"
)

download_parser = subparsers.add_parser("download", help="Download and process results")

args = parser.parse_args()

if args.command == "prepare":
    cmd_prepare(args)
elif args.command == "submit":
    cmd_submit(args)
elif args.command == "download":
    cmd_download(args)
