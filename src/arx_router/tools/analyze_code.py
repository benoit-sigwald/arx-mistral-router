"""Implementation of mistral_analyze_code tool."""

from typing import Any, Dict, Optional
from ..mistral_client import MistralRouterClient
from ..model_router import ModelRouter

CODE_ANALYSIS_SYSTEM_PROMPT = """You are an expert code analyst specializing in localized code inspection, bug diagnosis, and refactoring recommendations.

Rules:
1. Provide localized, precise technical analysis for the given code excerpt and question.
2. If the context is incomplete (missing imports, missing definitions), state your assumptions explicitly.
3. Do NOT invent functions, APIs, or architectural dependencies that are not in the context.
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "findings": [<concise analytical points, potential bugs, logic flaws, or performance issues>],
  "relevant_file_locations": [<line numbers, function names, or file references>],
  "recommended_changes": [<specific, actionable code modifications or refactoring suggestions>],
  "confidence": "high" | "medium" | "low",
  "uncertainty_notes": "<limitations due to partial context or external dependencies>"
}
"""


async def run_analyze_code(
    client: MistralRouterClient,
    router: ModelRouter,
    code: str,
    question: str,
    constraints: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform localized code analysis and bug diagnosis."""
    model = router.get_model_for_task("analyze_code")

    constraints_text = f"\nConstraints:\n{constraints}\n" if constraints else ""
    user_content = f"""Technical Question / Goal:\n{question}\n{constraints_text}\n--- CODE EXCERPT ---\n{code}"""

    result = await client.complete(
        model=model,
        system_prompt=CODE_ANALYSIS_SYSTEM_PROMPT,
        user_content=user_content,
        response_format_json=True,
        temperature=0.1,
    )
    return result
