"""Unit tests for correlation ID helpers."""

from shared.correlation import (
    bind_correlation_id,
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


def test_generate_correlation_id_format() -> None:
    correlation_id = generate_correlation_id()
    assert correlation_id.startswith("corr_")
    assert len(correlation_id) == len("corr_") + 12


def test_bind_correlation_id_uses_provided_value() -> None:
    correlation_id = bind_correlation_id("corr_fixed123456")
    assert correlation_id == "corr_fixed123456"
    assert get_correlation_id() == "corr_fixed123456"


def test_bind_correlation_id_generates_when_missing() -> None:
    reset_correlation_id()
    correlation_id = bind_correlation_id()
    assert correlation_id.startswith("corr_")
    assert get_correlation_id() == correlation_id


def test_set_correlation_id_overrides_context() -> None:
    set_correlation_id("corr_manual000001")
    assert get_correlation_id() == "corr_manual000001"
