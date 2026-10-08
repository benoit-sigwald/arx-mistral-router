"""Tests for UsageTracker and token metrics."""

from arx_router.usage import UsageTracker


def test_usage_tracker_aggregation():
    tracker = UsageTracker(monthly_budget=1000)
    tracker.record_request("mistral-small-latest", input_tokens=100, output_tokens=50, success=True)
    tracker.record_request("codestral-latest", input_tokens=200, output_tokens=100, success=True)
    tracker.record_request("codestral-latest", success=False, is_429=True)

    summary = tracker.get_summary()
    assert summary["totals"]["input_tokens"] == 300
    assert summary["totals"]["output_tokens"] == 150
    assert summary["totals"]["total_tokens"] == 450
    assert summary["totals"]["successful_requests"] == 2
    assert summary["totals"]["failed_requests"] == 1
    assert summary["totals"]["rate_limit_429_events"] == 1
    assert summary["budget"]["budget_used_percent"] == 45.0
    assert summary["budget"]["budget_exhausted"] is False


def test_budget_exhaustion():
    tracker = UsageTracker(monthly_budget=500)
    tracker.record_request("mistral-small-latest", input_tokens=400, output_tokens=150, success=True)
    assert tracker.is_budget_exhausted() is True

    summary = tracker.get_summary()
    assert summary["budget"]["budget_exhausted"] is True
    assert summary["budget"]["tokens_remaining"] == 0
