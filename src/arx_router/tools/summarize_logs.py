"""Implementation of mistral_summarize_logs tool."""

from typing import Any, Dict
from ..mistral_client import MistralRouterClient
from ..model_router import ModelRouter

LOG_SUMMARY_SYSTEM_PROMPT = """You are a site reliability engineer and diagnostics expert.
Analyze the provided execution logs according to the diagnostic objective.

Rules:
1. Identify root causes, panics, fatal exceptions, or cascading failures.
2. Avoid returning repetitive raw logs; extract only the most critical lines.
3. Suggest actionable next diagnostic checks.
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "root_cause_candidates": [<hypotheses or confirmed root causes of the issue>],
  "relevant_errors": [<key error messages, HTTP status codes, or exception names>],
  "supporting_log_excerpts": [<brief, exact log lines showing the trigger>],
  "recommended_checks": [<specific commands, files, or configs to inspect next>]
}
"""


async def run_summarize_logs(
    client: MistralRouterClient,
    router: ModelRouter,
    logs: str,
    objective: str = "Identify errors, root causes, and failures",
) -> Dict[str, Any]:
    """Diagnose and summarize system, application, or deployment logs."""
    model = router.get_model_for_task("summarize_logs")

    user_content = f"""Diagnostic Objective: {objective}\n\n--- LOGS ---\n{logs}"""

    result = await client.complete(
        model=model,
        system_prompt=LOG_SUMMARY_SYSTEM_PROMPT,
        user_content=user_content,
        response_format_json=True,
        temperature=0.1,
        context_type="logs",
    )
    return result
