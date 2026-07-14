"""Concrete generation provider — the ONLY module that imports the vendor SDK.

The harness is deliberately provider-agnostic (generate.py takes an injected callable and
imports no SDK). This module is the one place that binds to a real client. Keeping it isolated
means the scoring path (nli, grounding, detector, contraction, outcomes, stats, generate,
schema) never transitively pulls in a network client, and the pilot's model-identity guard has
a single, auditable point of contact with the outside world. tests/test_import_hygiene.py
enforces that isolation.

The factory returns a plain `(prompt) -> ProviderResponse` callable that generate.generate_row()
can consume: it exposes `.model` (the provider-reported identifier, checked against the pin) and
`.output` (the raw structured dict handed to schema.parse_output). The API key is read from the
environment at call time and never stored on the client object or logged.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from .config import CONFIG, Config


class ProviderError(RuntimeError):
    """A generation failed for a reason the pilot should log and skip (not halt).

    Covers a declined request (safety refusal), a truncated response (max_tokens before the
    JSON closed), a missing/empty text block, and any SDK/transport error surfaced during the
    call. The pilot records these in an exclusion bucket; they never crash the run. The one
    failure that DOES halt everything is the model-identity mismatch, which generate_row raises
    as ModelIdentityError before this module's output is trusted.
    """


class MissingAPIKeyError(RuntimeError):
    """ANTHROPIC_API_KEY is not set at call time."""


@dataclass(frozen=True)
class ProviderResponse:
    """What the provider callable returns — the GenerateResponse protocol generate.py expects.

    `output` is the raw structured dict (0001 shape) passed verbatim to schema.parse_output.
    `model` is the identifier the provider reports having served, checked against the pin by the
    model-identity guard.
    """

    output: dict
    model: str


# The 0001 structured-output schema, expressed as a JSON Schema for the provider's
# constrained-decoding format. This mirrors schema.parse_output's contract exactly:
# {claims: [{id:int, text:str, source_ids:[int]}], conclusion:str}. Structured outputs
# require additionalProperties:false and an explicit required list on every object.
_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["id", "text", "source_ids"],
                "additionalProperties": False,
            },
        },
        "conclusion": {"type": "string"},
    },
    "required": ["claims", "conclusion"],
    "additionalProperties": False,
}

# Output ceiling for one generation. The 0001 output is a short claim list plus one
# conclusion sentence; a few thousand tokens is ample and bounds the cost of a runaway
# generation. Not a frozen-config field — a plumbing constant local to this provider.
_MAX_TOKENS = 4096


def make_provider(config: Config = CONFIG) -> Callable[[str], ProviderResponse]:
    """Build a generate-callable bound to the pinned model and frozen sampler.

    The returned callable reads ANTHROPIC_API_KEY from the environment on EACH invocation and
    constructs a client scoped to that call, so the key is never held on a long-lived object or
    captured in a closure that could be logged. Model id comes from config.generation.model_pin;
    the structured-output format is the frozen 0001 schema.

    Sampler note: the pinned tier exposes no sampling parameters — explicit temperature/top_p are
    rejected by the API — so none are sent, and the registered sampler is the provider default
    (stochastic), recorded in the frozen config as sampling="provider-default". Thinking is
    explicitly disabled (thinking={"type": "disabled"}), also a frozen choice, so an unfrozen
    adaptive-reasoning mode cannot ride along outside the freeze hash. Both are hashed via
    config.sampler; this module reads neither directly because the API surface fixes them here.
    """
    model_pin = config.generation.model_pin

    def generate(prompt: str) -> ProviderResponse:
        # Read the key at call time; never stored on the client beyond this call's scope,
        # never logged, never returned.
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set; the pilot runner makes no API calls without it"
            )

        # Import inside the function so merely importing this module does not require the SDK
        # be installed (keeps import-hygiene checks and non-API test paths light).
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        try:
            message = client.messages.create(
                model=model_pin,
                max_tokens=_MAX_TOKENS,
                # No temperature/top_p: the pinned tier rejects explicit sampling parameters;
                # the registered sampler is the provider default (config: "provider-default").
                # Thinking is explicitly disabled — a frozen choice that keeps generation
                # single-pass across arms and prevents an unfrozen reasoning mode from riding
                # along outside the freeze hash.
                thinking={"type": "disabled"},
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": _OUTPUT_JSON_SCHEMA,
                    }
                },
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AnthropicError as exc:
            # Any SDK/transport/HTTP error becomes a loggable, skippable failure — the pilot
            # excludes this draw rather than crashing the whole run.
            raise ProviderError(f"generation call failed: {type(exc).__name__}: {exc}") from exc

        reported_model = getattr(message, "model", None)
        if not isinstance(reported_model, str):
            # Let the identity guard downstream decide; hand it whatever was reported (or "").
            reported_model = reported_model or ""

        if message.stop_reason == "refusal":
            raise ProviderError(
                f"model declined the request (stop_reason=refusal, "
                f"category={getattr(message.stop_details, 'category', None)})"
            )
        if message.stop_reason == "max_tokens":
            raise ProviderError(
                "generation truncated at max_tokens before the structured output closed"
            )

        text = _first_text(message)
        if text is None:
            raise ProviderError("no text block in the provider response")
        try:
            output = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"structured output was not valid JSON: {exc}") from exc
        if not isinstance(output, dict):
            raise ProviderError("structured output was not a JSON object")

        return ProviderResponse(output=output, model=reported_model)

    return generate


def _first_text(message: Any) -> str | None:
    """Return the text of the first text content block, or None if there is none.

    A structured-output response carries the JSON in a single text block; this pulls it out
    without assuming block ordering beyond 'first text block wins'.
    """
    content = getattr(message, "content", None) or []
    for block in content:
        if getattr(block, "type", None) == "text":
            return getattr(block, "text", None)
    return None
