"""Frozen configuration for the E5 G-slice harness.

Every result-sensitive choice in decisions 0001/0002/0006/0007 is recorded here as a
frozen field. The config serializes to sorted-key JSON and hashes to a SHA-256; the hash
is what a reader checks against the pre-registration to confirm the analysis plan predates
the data (0006 freeze boundary). scripts/check_config_freeze.py fails on drift.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class NLIConfig:
    # Primary checkpoint (0002). Revision hash resolved 2026-07-14; version-record-only
    # per 0006 (does not change the frozen result, but pinned for bit-level rerun).
    checkpoint: str = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
    revision: str = "b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7"
    # CPU-lighter fallback (0002), pre-registered and selectable.
    fallback_checkpoint: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    fallback_revision: str = "6f5cf0a2b59cabb106aca4c287eed12e357e90eb"
    use_fallback: bool = False
    max_length: int = 512
    batch_size: int = 16
    # Frozen inference device. Registered runs pin "cpu": MPS/CUDA float paths are not
    # bit-identical to CPU, and an unrecorded device would let two machines disagree at the
    # 0.7/0.10 thresholds while reporting the same config hash (0007 bit-for-bit clause).
    device: str = "cpu"


@dataclass(frozen=True)
class DetectorConfig:
    # 0007 contamination rule. Registered sweep is over these two axes (0002/0007
    # anti-fishing requirement); the frozen point is the centre of each sweep.
    grounding_floor: float = 0.7
    drop_ceiling: float = 0.10
    grounding_floor_sweep: tuple[float, ...] = (0.65, 0.70, 0.75)
    drop_ceiling_sweep: tuple[float, ...] = (0.05, 0.10, 0.15)
    # Threshold comparisons quantize to this many decimals before comparing: float64
    # subtraction can land a mathematically-exact-0.10 drop at 0.0999...8, flipping the
    # boundary case the strict `<` is registered to exclude.
    quantize_decimals: int = 9


@dataclass(frozen=True)
class OutcomeConfig:
    # An arm "still asserts" an annotated conclusion iff bidirectional NLI >= this
    # threshold (0007 outcome scoring). Shared by contamination and completeness.
    assert_threshold: float = 0.7


@dataclass(frozen=True)
class SamplerConfig:
    # 0001 sampler, shared across arms. Non-zero temperature is mandatory (0001).
    temperature: float = 0.7
    top_p: float = 0.95


@dataclass(frozen=True)
class StatsConfig:
    alpha: float = 0.05
    bonferroni_comparisons: int = 3
    # 0007 completeness non-inferiority margin (absolute).
    non_inferiority_delta: float = 0.10
    n_tasks: int = 60


@dataclass(frozen=True)
class GenerationConfig:
    # 0001 registered primary model pin. generate.py halts on a provider-returned
    # mismatch against this identifier.
    model_pin: str = "claude-sonnet-5"


@dataclass(frozen=True)
class Config:
    nli: NLIConfig = field(default_factory=NLIConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    outcome: OutcomeConfig = field(default_factory=OutcomeConfig)
    sampler: SamplerConfig = field(default_factory=SamplerConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)


CONFIG = Config()


def _jsonable(obj: object) -> object:
    # dataclasses -> dict; tuples -> lists so JSON round-trips are stable.
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def config_json(config: Config = CONFIG) -> str:
    """Deterministic sorted-key JSON serialization of the frozen config."""
    return json.dumps(_jsonable(asdict(config)), sort_keys=True, separators=(",", ":"))


def config_hash(config: Config = CONFIG) -> str:
    """SHA-256 of the sorted-key JSON. This is the pre-registration freeze token."""
    return hashlib.sha256(config_json(config).encode("utf-8")).hexdigest()
