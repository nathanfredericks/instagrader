"""Global test safeguards.

Any real Bedrock/AI client call in tests should fail fast unless the test
explicitly patches the Bedrock client.
"""

from unittest.mock import patch


def _raise_on_unmocked_ai_call(*_args, **_kwargs):
    raise AssertionError(
        "Unmocked AI call detected. Patch grading.bedrock.boto3.client "
        "(or a higher-level AI helper) in this test."
    )


_bedrock_client_guard = patch(
    "grading.bedrock.boto3.client",
    side_effect=_raise_on_unmocked_ai_call,
)
_bedrock_client_guard.start()
