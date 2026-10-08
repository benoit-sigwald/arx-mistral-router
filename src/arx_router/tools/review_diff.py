"""Implementation of mistral_review_diff tool."""

from typing import Any, Dict, Optional
from ..mistral_client import MistralRouterClient
from ..model_router import ModelRouter

DIFF_REVIEW_SYSTEM_PROMPT = """You are a senior peer reviewer conducting an advisory code review of a git diff.

Rules:
1. Identify subtle regression risks, breaking changes, race conditions, edge case mishandling, and security flaws.
2. Flag missing test coverage for changed code branches.
3. This is an advisory review: focus on concrete high-signal issues, avoiding bikeshedding or stylistic complaints.
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "potential_regressions": [<potential side-effects, breaking API changes, or regressions>],
  "security_or_reliability_concerns": [<security vulnerabilities, race conditions, unhandled exceptions, leakages>],
  "missing_tests": [<scenarios or branches in the diff lacking automated test coverage>],
  "suggested_fixes": [<actionable fixes or improvements>]
}
"""


async def run_review_diff(
    client: MistralRouterClient,
    router: ModelRouter,
    diff: str,
    requirements: str = "",
    test_results: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform advisory review on git diff."""
    model = router.get_model_for_task("review_diff")

    test_info = f"\nExisting Test Results:\n{test_results}\n" if test_results else ""
    req_info = f"\nRequirements / Intent:\n{requirements}\n" if requirements else ""
    user_content = f"""{req_info}{test_info}\n--- GIT DIFF ---\n{diff}"""

    result = await client.complete(
        model=model,
        system_prompt=DIFF_REVIEW_SYSTEM_PROMPT,
        user_content=user_content,
        response_format_json=True,
        temperature=0.1,
    )
    return result
