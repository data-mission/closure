"""Model loading with revision enforcement and chat-template hashing (audit-driven redesign, G).

e3-0004 pins the generation model to a specific repo id AND snapshot revision because the probe reads
a specific tensor of a specific checkpoint — a silent model-revision change would move the input
vector itself, not just bookkeeping. This module makes that pin FAIL-CLOSED: loading resolves the
snapshot the loader actually returned and asserts it equals the requested revision, raising otherwise.
It also records the SHA-256 of a canonical probe rendered through the model's chat template, so a
change to the template (which changes the exact prompt string the hidden state is read from) is
detectable even when the revision string is unchanged.

No model is downloaded here and the tests never touch the network: ``load`` takes an injected
``loader_fn`` so the assertion and hashing logic are unit-tested against stubs. The real confirmatory
session supplies a ``loader_fn`` that wraps ``mlx_lm.load`` (mlx-lm 0.31.3, e3-0004) and returns the
resolved snapshot revision plus a chat-template renderer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

#: The fixed canonical probe rendered through the chat template for hashing. A single-turn user
#: message with frozen content — the template's framing tokens are what we are fingerprinting, not the
#: content, but the content is fixed so the hash is a pure function of the template.
CANONICAL_PROBE_MESSAGES: tuple[Mapping[str, str], ...] = (
    {"role": "user", "content": "What is the semantic volume of the reachable futures?"},
)

#: A loader returns (resolved_revision, render_chat) where render_chat(messages) -> the exact string
#: the model would be fed after chat templating.
LoaderFn = Callable[[str, str], tuple[str, Callable[[Sequence[Mapping[str, str]]], str]]]


def chat_template_sha256(rendered: str) -> str:
    """SHA-256 hex digest of a chat-templated prompt string (UTF-8)."""
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LoadedModel:
    """Provenance of a revision-enforced load."""

    model_id: str
    requested_revision: str
    resolved_revision: str
    chat_template_sha256: str


class RevisionMismatchError(RuntimeError):
    """Raised (fail-closed) when the resolved snapshot revision differs from the pin."""


class ChatTemplateMismatchError(RuntimeError):
    """Raised (fail-closed) when the rendered-probe hash differs from the expected pin."""


def load(
    model_id: str,
    revision: str,
    loader_fn: LoaderFn,
    expected_chat_template_sha256: str | None = None,
) -> LoadedModel:
    """Load ``model_id`` at ``revision`` via ``loader_fn``, enforcing the revision and template pins.

    Args:
        model_id: repo id (e.g. ``mlx-community/Qwen2.5-7B-Instruct-4bit``).
        revision: the pinned snapshot revision that MUST be the one resolved.
        loader_fn: injected loader returning ``(resolved_revision, render_chat)``. In tests this is a
            stub; in the real run it wraps ``mlx_lm.load`` at the pinned revision.
        expected_chat_template_sha256: if given, the rendered canonical probe's hash must equal it,
            else ``ChatTemplateMismatchError`` — catches a template change under an unchanged revision.

    Returns:
        A ``LoadedModel`` recording the (verified-equal) revisions and the chat-template hash.

    Raises:
        RevisionMismatchError: the loader resolved a different snapshot than pinned (fail-closed).
        ChatTemplateMismatchError: the template hash differs from the supplied expectation.
    """
    resolved_revision, render_chat = loader_fn(model_id, revision)
    if resolved_revision != revision:
        raise RevisionMismatchError(
            f"resolved snapshot {resolved_revision!r} != pinned revision {revision!r} for "
            f"{model_id!r} — refusing to read hidden states from an unpinned checkpoint"
        )
    rendered = render_chat(CANONICAL_PROBE_MESSAGES)
    sha = chat_template_sha256(rendered)
    if expected_chat_template_sha256 is not None and sha != expected_chat_template_sha256:
        raise ChatTemplateMismatchError(
            f"canonical-probe chat-template hash {sha} != expected "
            f"{expected_chat_template_sha256} for {model_id!r}@{revision} — the prompt string the "
            "probe reads has changed despite an unchanged revision"
        )
    return LoadedModel(
        model_id=model_id,
        requested_revision=revision,
        resolved_revision=resolved_revision,
        chat_template_sha256=sha,
    )
