"""Implementation of mistral_usage tool."""

from typing import Any, Dict
from ..usage import UsageTracker


def run_usage_report(tracker: UsageTracker) -> Dict[str, Any]:
    """Retrieve current token consumption, delegation metrics, rate limit stats, and budget health."""
    return tracker.get_summary()
