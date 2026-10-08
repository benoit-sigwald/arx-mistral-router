"""Implementation of mistral_generate_tests tool."""

from typing import Any, Dict, Optional
from ..mistral_client import MistralRouterClient
from ..model_router import ModelRouter

TEST_GEN_SYSTEM_PROMPT = """You are a software test engineer crafting robust, idiomatic automated tests.

Rules:
1. Generate runnable test code for the specified testing framework (e.g., pytest, jest, unittest).
2. Cover happy paths, edge cases (empty inputs, nulls, boundaries, timeouts), and error scenarios.
3. State all mocking assumptions clearly.
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "proposed_tests": "<complete, self-contained test code string>",
  "edge_cases_covered": [<list of specific edge cases and error conditions addressed>],
  "assumptions": [<assumptions regarding fixtures, dependencies, or environment>]
}
"""


async def run_generate_tests(
    client: MistralRouterClient,
    router: ModelRouter,
    code_or_module: str,
    framework: str = "pytest",
    expected_behavior: str = "",
) -> Dict[str, Any]:
    """Generate unit and integration tests for a function or module."""
    model = router.get_model_for_task("generate_tests")

    user_content = f"""Target Framework: {framework}\nExpected Behavior & Requirements:\n{expected_behavior}\n\n--- CODE UNDER TEST ---\n{code_or_module}"""

    result = await client.complete(
        model=model,
        system_prompt=TEST_GEN_SYSTEM_PROMPT,
        user_content=user_content,
        response_format_json=True,
        temperature=0.2,
    )
    return result
