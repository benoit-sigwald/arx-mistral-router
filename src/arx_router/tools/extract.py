"""Implementation of mistral_extract tool."""

import json
from typing import Any, Dict, Optional
from ..mistral_client import MistralRouterClient
from ..model_router import ModelRouter

EXTRACTION_SYSTEM_PROMPT = """You are a deterministic evidence extraction engine.
Your objective: Extract exact information from the provided source text according to the user's instructions.

Rules:
1. Preserve source fidelity strictly. Do NOT invent, assume, or extrapolate facts.
2. If evidence is missing or ambiguous, explicitly note it as null or "not found in source".
3. Distinguish clearly between factual extraction and inference.
4. Output MUST be valid JSON adhering to the following structure:
{
  "extracted_evidence": <structured object or list with extracted data>,
  "source_references": [<exact quotes or line/section references supporting the extraction>],
  "notes": "<optional notes or caveats>"
}
"""


async def run_extract(
    client: MistralRouterClient,
    router: ModelRouter,
    text: str,
    instructions: str,
    output_schema: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract structured evidence from text using Mistral Small."""
    model = router.get_model_for_task("extraction")

    schema_prompt = ""
    if output_schema:
        schema_prompt = f"\nDesired Schema / Constraints:\n{output_schema}\n"

    user_content = f"""Instructions:\n{instructions}\n{schema_prompt}\n--- SOURCE TEXT ---\n{text}"""

    result = await client.complete(
        model=model,
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_content=user_content,
        response_format_json=True,
        temperature=0.0,
    )
    return result
