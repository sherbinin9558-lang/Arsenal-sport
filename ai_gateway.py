"""Single metering gateway for AI-style operations.

All future provider-backed generation should enter through this module. The
current product is intentionally deterministic/free-first, so local operations
record request units and estimated cost without requiring a paid API key.
Provider adapters may supply actual token counts when available.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional

from ai_usage import estimate_cost_rub, record_ai_usage


@dataclass(frozen=True)
class AIUsage:
    operation: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    request_count: int = 1

    @property
    def estimated_cost_rub(self) -> float:
        return estimate_cost_rub(self.input_tokens, self.output_tokens)


def estimate_text_tokens(text: Any) -> int:
    value = str(text or "")
    if not value:
        return 0
    # Conservative provider-independent approximation used only when the
    # provider does not return authoritative token counts.
    return max(1, (len(value) + 3) // 4)


def meter(usage: AIUsage, metadata: Optional[dict] = None) -> dict:
    return record_ai_usage(
        usage.operation,
        provider=usage.provider,
        model=usage.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        request_count=usage.request_count,
        metadata=metadata or {},
    )


@contextmanager
def tracked_operation(
    operation: str,
    *,
    provider: str = "local",
    model: str = "deterministic",
    input_text: Any = "",
    metadata: Optional[dict] = None,
) -> Iterator[Callable[[Any], None]]:
    """Track one operation and optionally attach the produced output size.

    The yielded callback accepts the final output text. Metering failures are
    deliberately non-fatal so business actions never fail because telemetry is
    unavailable.
    """
    input_tokens = estimate_text_tokens(input_text)
    output_tokens = 0

    def set_output(output: Any) -> None:
        nonlocal output_tokens
        output_tokens = estimate_text_tokens(output)

    try:
        yield set_output
    finally:
        try:
            meter(
                AIUsage(
                    operation=operation,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
                metadata=metadata,
            )
        except Exception:
            pass
