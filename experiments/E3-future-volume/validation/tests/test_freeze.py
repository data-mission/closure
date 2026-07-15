"""freeze.py — the frozen-config schema, sorted-key JSON, and SHA-256 (redesign H; e3-0004).

The hash must be a pure function of the field VALUES: stable across key insertion order, and changed
by ANY field change (including the new redesign params buried inside the embedded VerdictThresholds).
These tests build a representative config and assert both properties across a spread of fields.
"""

from __future__ import annotations

import json
from dataclasses import replace

from e3_validation.freeze import (
    FrozenConfig,
    LibraryVersions,
    ModelConfig,
    SamplerConfig,
    SeedConfig,
)

from ._fixtures import PASSING_THRESHOLDS


def _config() -> FrozenConfig:
    return FrozenConfig(
        corpus_sha256="a" * 64,
        golds_sha256="b" * 64,
        refusal_regexes=("^I can't", "^I cannot", "^I'm unable", "^I won't"),
        normalizer_spec_version="v1",
        epsilon=1e-6,
        n_continuations=10,
        sampler=SamplerConfig(temperature=0.7, top_p=0.95, max_tokens=256, eos_id=151645),
        seeds=SeedConfig(base_seed=20260714),
        alpha_grid=(1e-2, 1e0, 1e2, 1e4, 1e6),
        inner_cv_folds=5,
        correctness_cv_folds=5,
        bootstrap_n=10000,
        bootstrap_ci_level=0.95,
        test_fraction=0.30,
        thresholds=PASSING_THRESHOLDS,
        model=ModelConfig(
            model_id="mlx-community/Qwen2.5-7B-Instruct-4bit",
            model_revision="c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed",
            tokenizer_revision="c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed",
            chat_template_sha256="c" * 64,
            hidden_dim=3584,
            embedder_id="nomic-ai/nomic-embed-text-v1.5",
            embedder_revision="e9b6763023c676ca8431644204f50c2b100d9aab",
            embedder_prefix="clustering: ",
            embedder_dim=768,
        ),
        libraries=LibraryVersions(
            python="3.12.13",
            numpy="2.5.1",
            scikit_learn="1.9.0",
            scipy="1.18.0",
            mlx_lm="0.31.3",
        ),
    )


def test_json_is_sorted_key_and_parses():
    cfg = _config()
    js = cfg.to_json()
    parsed = json.loads(js)
    assert list(parsed.keys()) == sorted(parsed.keys())  # top-level keys sorted
    # the new redesign params are present via the embedded thresholds.
    assert parsed["thresholds"]["min_negatives"] == PASSING_THRESHOLDS.min_negatives
    assert parsed["thresholds"]["within_family_spearman_min"] is not None
    assert parsed["orientation"]["probe"] == "-predicted_volume"


def test_hash_is_stable_across_key_order():
    cfg = _config()
    # a differently-ordered orientation dict must not change the hash (sorted-key JSON).
    reordered = replace(
        cfg,
        orientation={
            "verbalized": "stated_value",
            "b4": "P(correct)",
            "b3": "-entropy",
            "probe": "-predicted_volume",
        },
    )
    assert cfg.sha256() == reordered.sha256()


def test_hash_changes_when_any_field_changes():
    base = _config().sha256()
    assert replace(_config(), epsilon=1e-5).sha256() != base
    assert replace(_config(), n_continuations=11).sha256() != base
    assert replace(_config(), test_fraction=0.25).sha256() != base
    assert replace(_config(), bootstrap_n=2000).sha256() != base
    assert replace(_config(), corpus_sha256="z" * 64).sha256() != base
    assert replace(_config(), refusal_regexes=("^No",)).sha256() != base


def test_hash_changes_on_nested_field_changes():
    base = _config().sha256()
    # a new redesign threshold buried in the embedded dataclass.
    assert replace(_config(), thresholds=replace(PASSING_THRESHOLDS, min_negatives=25)).sha256() != base
    assert replace(_config(), thresholds=replace(PASSING_THRESHOLDS, within_family_spearman_min=0.6)).sha256() != base
    # sampler, seeds, model, libraries.
    assert replace(_config(), sampler=replace(_config().sampler, temperature=0.8)).sha256() != base
    assert replace(_config(), seeds=replace(_config().seeds, base_seed=1)).sha256() != base
    assert replace(_config(), model=replace(_config().model, model_revision="x" * 40)).sha256() != base
    assert replace(_config(), libraries=replace(_config().libraries, numpy="2.5.2")).sha256() != base


def test_hash_is_sha256_hex():
    h = _config().sha256()
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
