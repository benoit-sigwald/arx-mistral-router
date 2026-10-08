"""Tests for ModelRouter and delegation fitness."""

from arx_router.model_router import ModelRouter
from arx_router.config import RouterConfig


def test_model_resolution():
    cfg = RouterConfig(
        model_extraction="mistral-small-custom",
        model_code="codestral-custom",
        model_summarization="mistral-small-custom",
    )
    router = ModelRouter(cfg)
    assert router.get_model_for_task("extraction") == "mistral-small-custom"
    assert router.get_model_for_task("analyze_code") == "codestral-custom"
    assert router.get_model_for_task("summarize_logs") == "mistral-small-custom"


def test_evaluate_delegation_fit():
    cfg = RouterConfig(max_input_chars=500)
    router = ModelRouter(cfg)

    # Fits within limit
    fits, reason = router.evaluate_delegation_fit("extract", "Short text")
    assert fits is True
    assert reason is None

    # Oversized payload
    fits_over, reason_over = router.evaluate_delegation_fit("extract", "A" * 600)
    assert fits_over is False
    assert "exceeds the free-tier router limit" in reason_over
    assert "Gemini Pro" in reason_over
