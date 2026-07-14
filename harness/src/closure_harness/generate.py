"""Provider-agnostic generation (decision 0001).

The model is a parameter: generate_row() takes a `generate` callable (prompt -> provider
response) and never imports any provider SDK. It validates the 0001 structured-output schema,
records the provider-returned model identifier per row, and raises on mismatch with the
configured pin (the model-identity guard from E0 PLAN.md, adopted for E5).

No concrete provider client lives here — a caller supplies one at run time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .config import CONFIG, GenerationConfig
from .schema import Output, parse_output


class GenerateResponse(Protocol):
    """What a provider callable must return: the structured output plus the model id the
    provider reports having served (not the requested id)."""

    output: dict
    model: str


@dataclass(frozen=True)
class GeneratedRow:
    output: Output
    reported_model: str


class ModelIdentityError(RuntimeError):
    """Raised when the provider-returned model id does not match the configured pin."""


def generate_row(
    generate: Callable[[str], GenerateResponse],
    prompt: str,
    config: GenerationConfig = CONFIG.generation,
) -> GeneratedRow:
    """Generate one row, validate schema, and halt on a model-identity mismatch.

    `generate` is the injected provider callable; the harness stays SDK-free. The pin check
    fires before schema use is trusted so a spoofed/misrouted model cannot enter the dataset.
    """
    response = generate(prompt)
    reported = getattr(response, "model", None)
    if reported != config.model_pin:
        raise ModelIdentityError(
            f"model identity mismatch: provider reported {reported!r}, pin is {config.model_pin!r}"
        )
    output = parse_output(response.output)
    return GeneratedRow(output=output, reported_model=reported)
