"""Task-to-model router and complexity evaluation."""

from typing import Dict, Optional, Tuple
from .config import RouterConfig


class ModelRouter:
    """Routes delegated tasks to optimal Mistral models or suggests Gemini Pro escalation."""

    def __init__(self, config: RouterConfig):
        self.config = config

    def get_model_for_task(self, task_type: str) -> str:
        """Resolve model name based on task type and configuration."""
        task_type = task_type.lower()
        if task_type in ("extraction", "extract"):
            return self.config.model_extraction
        elif task_type in ("summarize_logs", "logs", "summarization"):
            return self.config.model_summarization
        elif task_type in ("analyze_code", "code"):
            return self.config.model_code
        elif task_type in ("generate_tests", "tests"):
            return self.config.model_tests
        elif task_type in ("review_diff", "diff"):
            return self.config.model_diff
        return self.config.fallback_model

    def evaluate_delegation_fit(self, task_type: str, input_text: str, context_details: Optional[Dict] = None) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if a task is suitable for Mistral free-tier delegation
        or if it should be escalated to Gemini Pro.
        Returns: (can_delegate: bool, reason_if_cannot: Optional[str])
        """
        char_count = len(input_text or "")
        
        # Check excessive size requiring large context window
        if char_count > self.config.max_input_chars:
            return (
                False,
                f"Input length ({char_count} chars) exceeds the free-tier router limit ({self.config.max_input_chars} chars). "
                "Recommendation: Handle directly in Gemini Pro to avoid context loss."
            )

        # Check task complexity heuristics
        if task_type == "analyze_code":
            if context_details and context_details.get("is_system_wide_refactor", False):
                return (
                    False,
                    "System-wide architectural refactoring requires multi-file cross-repository reasoning. "
                    "Recommendation: Execute in Antigravity's primary Gemini Pro model."
                )

        return True, None
