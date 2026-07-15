"""Frozen configuration schema and hash (audit-driven redesign, H).

e3-0004 fixes E3's reproducibility posture as *seeded-and-reported with a committed config hash*: the
full configuration is serialized to sorted-key JSON and hashed with SHA-256, so any post-registration
change to a result-moving input is detectable by a reader who recomputes the hash. This module is that
schema — a single dataclass enumerating EVERY input that can move a reported number or the verdict, a
canonical sorted-key JSON serialization, and its SHA-256.

The audit-driven redesign added result-moving inputs (the new threshold params, the correctness CV
folds, the length gate, the orientation table, the model/embedder revisions and chat-template hash).
They are ALL included here — the freeze schema is the single place that must stay in lockstep with the
verdict contract, so the whole ``VerdictThresholds`` dataclass is embedded rather than re-listed.

The hash is a pure function of the field VALUES, independent of key insertion order (sorted keys), and
changes if any field changes — both properties are asserted in ``tests/test_freeze.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .correctness import ORIENTATION
from .verdict import VerdictThresholds


@dataclass(frozen=True)
class SamplerConfig:
    """Continuation sampler (e3-0002)."""

    temperature: float
    top_p: float
    max_tokens: int
    eos_id: int


@dataclass(frozen=True)
class SeedConfig:
    """Base seed and the derivation FORMULAS (strings) for every derived seed (e3-0004).

    The formulas are recorded as text, not just the resolved integers, so a reader can re-derive every
    seed from ``base_seed``. Offsets follow the rehearsal manifest (REHEARSAL.md): split = base+1,
    paired bootstrap = base+2, single-arm CI = base+3, synthetic mixtures = base+4; the correctness
    out-of-fold CV seed is base+5 (added by the redesign's correctness protocol).
    """

    base_seed: int
    continuation_draw: str = "base_seed + prompt_index * N + draw_index"
    split: str = "base_seed + 1"
    paired_bootstrap: str = "base_seed + 2"
    single_arm_ci: str = "base_seed + 3"
    synthetic_mixture: str = "base_seed + 4"
    correctness_cv: str = "base_seed + 5"


@dataclass(frozen=True)
class ModelConfig:
    """Generation model, embedder, tokenizer revisions and the chat-template hash (e3-0004, loader.py)."""

    model_id: str
    model_revision: str
    tokenizer_revision: str
    chat_template_sha256: str
    hidden_dim: int
    embedder_id: str
    embedder_revision: str
    embedder_prefix: str
    embedder_dim: int


@dataclass(frozen=True)
class LibraryVersions:
    """Pinned analysis-environment library versions (VALIDATION.md) plus the inference stack."""

    python: str
    numpy: str
    scikit_learn: str
    scipy: str
    mlx_lm: str


@dataclass(frozen=True)
class FrozenConfig:
    """Every result-moving input for one E3 confirmatory run, hashable to a single SHA-256.

    Grouped for readability but flat for hashing: corpus/label provenance, refusal and normalizer
    specs, the volume constants, the sampler, all seeds, the probe/CV/bootstrap params, ALL verdict
    thresholds (embedded ``VerdictThresholds``, new params included), the eval split fraction, the
    model/embedder pins, library versions, and the frozen correctness-orientation table.
    """

    corpus_sha256: str
    golds_sha256: str
    refusal_regexes: tuple[str, ...]
    normalizer_spec_version: str

    epsilon: float
    n_continuations: int

    sampler: SamplerConfig
    seeds: SeedConfig

    alpha_grid: tuple[float, ...]
    inner_cv_folds: int
    correctness_cv_folds: int
    bootstrap_n: int
    bootstrap_ci_level: float
    test_fraction: float

    thresholds: VerdictThresholds

    model: ModelConfig
    libraries: LibraryVersions

    orientation: Mapping[str, str] = field(default_factory=lambda: dict(ORIENTATION))

    def to_dict(self) -> dict[str, Any]:
        """Recursively convert to a plain JSON-friendly dict (dataclasses -> dicts, tuples -> lists)."""
        return _jsonable(asdict(self))

    def to_json(self) -> str:
        """Canonical sorted-key JSON serialization (the exact bytes that get hashed)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        """SHA-256 hex digest of the canonical sorted-key JSON — the committed config hash (e3-0004)."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _jsonable(obj: Any) -> Any:
    """Normalize tuples/sets to lists so JSON is canonical; dicts/scalars pass through."""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj
