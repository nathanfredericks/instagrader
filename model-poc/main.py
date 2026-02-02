import json
import boto3
from pathlib import Path

AWS_REGION = "us-east-1"
MODEL_ID = "openai.gpt-oss-20b-1:0"


def load_json(filepath: Path) -> dict:
    """Load and parse JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_text(filepath: Path) -> str:
    """Load text file"""
    with open(filepath, 'r') as f:
        return f.read()


def build_prompt(prompt_data: dict, rubric_data: dict, essay_text: str) -> str:
    """Build the formatted prompt following the training data format"""

    # Build rubric JSON array (list of criteria with levels)
    rubric_json = json.dumps(rubric_data["criteria"])

    # Get writing prompt text
    writing_prompt = prompt_data["prompt"]

    # Build source text section if present
    source_text_section = ""
    if prompt_data.get("source_text"):
        source_text_section = f"""<source_text>
{prompt_data["source_text"]}
</source_text>

"""

    # Build expected output schema based on rubric
    expected_scores = []
    for criterion in rubric_data["criteria"]:
        expected_scores.append({
            "criteria_id": criterion["id"],
            "level_id": "<level_id>",
            "feedback": "<feedback explaining the score with specific examples from the essay>"
        })

    output_schema = json.dumps({"scores": expected_scores}, indent=2)

    # System instructions
    system_instructions = """<system>
You are an expert essay grader. Score the essay according to the rubric and provide constructive feedback for each criterion.

For each criterion in the rubric, provide:
1. The criteria_id matching the rubric
2. The level_id indicating the score level achieved
3. Feedback explaining why this score was given, citing specific examples from the essay

Your response must be valid JSON matching the expected schema.
</system>

"""

    # Build the complete prompt
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

Provide your grading with specific feedback for each criterion. Your entire response should be only the JSON output with no additional text, commentary, or explanation outside the JSON structure."""

    return prompt


def call_bedrock(prompt_text: str, model_id: str = MODEL_ID, region: str = AWS_REGION) -> str:
    """Call Bedrock API and return response"""

    # Create bedrock-runtime client
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=region
    )

    # Build request body for OpenAI model on Bedrock
    request_body = {
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "max_completion_tokens": 4096,
        "temperature": 0.7
    }

    # Call the API
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )

    # Parse response
    response_body = json.loads(response['body'].read())

    output_text = response_body["choices"][0]["message"]["content"]

    # Remove reasoning tags (GPT-OSS models include <reasoning> tags)
    import re
    output_text = re.sub(r'<reasoning>.*?</reasoning>', '', output_text, flags=re.DOTALL).strip()

    return output_text


def format_response_as_text(response_json: dict, rubric_data: dict) -> str:
    """Format JSON response as readable text"""
    output_lines = []

    # Create a mapping of criteria IDs to criteria details
    criteria_map = {c["id"]: c for c in rubric_data["criteria"]}

    for score in response_json.get("scores", []):
        criteria_id = score["criteria_id"]
        level_id = score["level_id"]
        feedback = score["feedback"]

        # Get criteria details
        criterion = criteria_map.get(criteria_id, {})
        criteria_name = criterion.get("name", f"Criterion {criteria_id}")

        # Get level description
        level_description = "Unknown level"
        for level in criterion.get("levels", []):
            if str(level["id"]) == str(level_id):
                level_description = level["descriptor"]
                break

        # Format output
        output_lines.append(f"{criteria_name}: Level {level_id}")
        output_lines.append(level_description)
        output_lines.append(f"Feedback: {feedback}")
        output_lines.append("")

    return "\n".join(output_lines)


# Get paths relative to script location
script_dir = Path(__file__).parent
rubric_path = script_dir / "rubric.json"
prompt_path = script_dir / "prompt.json"
essay_path = script_dir / "essay.txt"

# Load files (silently)
rubric_data = load_json(rubric_path)
prompt_data = load_json(prompt_path)
essay_text = load_text(essay_path)

# Build prompt
prompt = build_prompt(prompt_data, rubric_data, essay_text)

try:
    response = call_bedrock(prompt, region="us-east-1")

    # Parse and format as readable text
    try:
        response_json = json.loads(response)
        formatted_output = format_response_as_text(response_json, rubric_data)
        print(formatted_output)
    except json.JSONDecodeError as e:
        print(f"Error: Response is not valid JSON: {e}")
        print(response)

except Exception as e:
    print(f"Error calling Bedrock API: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()