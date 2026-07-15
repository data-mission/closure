"""loader.py — revision enforcement and chat-template hashing with stubs (redesign G).

No model is downloaded; an injected stub ``loader_fn`` supplies the resolved revision and a
chat-template renderer, so the fail-closed assertion logic and the template hash are unit-tested in
isolation (e3-0004 pins the model to a specific snapshot revision because the probe reads a specific
tensor of a specific checkpoint).
"""

from __future__ import annotations

import pytest

from e3_validation.loader import (
    CANONICAL_PROBE_MESSAGES,
    ChatTemplateMismatchError,
    RevisionMismatchError,
    chat_template_sha256,
    load,
)

MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
PIN = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"


def _stub(resolved_revision: str, rendered: str):
    def loader_fn(model_id: str, revision: str):
        def render_chat(messages):
            return rendered

        return resolved_revision, render_chat

    return loader_fn


def test_chat_template_sha256_is_deterministic():
    assert chat_template_sha256("hello") == chat_template_sha256("hello")
    assert chat_template_sha256("hello") != chat_template_sha256("world")


def test_load_succeeds_when_revision_matches():
    lm = load(MODEL, PIN, _stub(PIN, "<|im_start|>user\nprobe<|im_end|>"))
    assert lm.model_id == MODEL
    assert lm.requested_revision == PIN and lm.resolved_revision == PIN
    assert lm.chat_template_sha256 == chat_template_sha256("<|im_start|>user\nprobe<|im_end|>")


def test_load_fails_closed_on_revision_mismatch():
    with pytest.raises(RevisionMismatchError):
        load(MODEL, PIN, _stub("deadbeef" * 5, "anything"))


def test_load_enforces_expected_chat_template_hash():
    rendered = "<|im_start|>user\nprobe<|im_end|>"
    good = chat_template_sha256(rendered)
    # matching expectation passes
    load(MODEL, PIN, _stub(PIN, rendered), expected_chat_template_sha256=good)
    # a changed template under an unchanged revision is caught
    with pytest.raises(ChatTemplateMismatchError):
        load(MODEL, PIN, _stub(PIN, rendered + " CHANGED"), expected_chat_template_sha256=good)


def test_canonical_probe_is_a_single_user_turn():
    assert len(CANONICAL_PROBE_MESSAGES) == 1
    assert CANONICAL_PROBE_MESSAGES[0]["role"] == "user"
