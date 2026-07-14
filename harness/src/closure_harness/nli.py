"""NLI grounding scalar (decision 0002).

Per-pair scalar: (P(entail) - P(contradict) + 1) / 2, in [0,1].
Bidirectional: average the two premise/hypothesis orderings.
Multi-source: max over individual source premises.

The scalar is exposed as a plain callable (a Protocol) so downstream modules — grounding,
detector, outcomes — take it as an injected dependency and can be unit-tested with a stub
that never loads the model.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .config import CONFIG, NLIConfig


@runtime_checkable
class Scalar(Protocol):
    """A grounding scalar: (sources, claim) -> [0,1] agreement.

    sources is a list of independent premise strings; the score is the max over them,
    each direction averaged.
    """

    def __call__(self, sources: Sequence[str], claim: str) -> float: ...


def _softmax_row(logits: "list[float]") -> "list[float]":
    import math

    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


class NLIScorer:
    """Loads the pinned DeBERTa-MNLI checkpoint and produces the 0002 grounding scalar.

    Implements the Scalar protocol via __call__. Inference is batched; runs on MPS when
    available, else CPU (no GPU is required for E5).
    """

    def __init__(self, config: NLIConfig = CONFIG.nli):
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        self.config = config
        checkpoint = config.fallback_checkpoint if config.use_fallback else config.checkpoint
        revision = config.fallback_revision if config.use_fallback else config.revision

        self._torch = torch
        # Device comes from the frozen config, never from runtime availability: MPS/CUDA
        # float paths are not bit-identical to CPU, so an availability-based pick would make
        # scores machine-dependent under an identical config hash. Registered runs pin "cpu".
        self.device = torch.device(config.device)
        torch.use_deterministic_algorithms(True)

        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, revision=revision)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            checkpoint, revision=revision
        )
        self.model.to(self.device)
        self.model.eval()

        # Resolve entailment/contradiction indices from the model's own label map rather
        # than assuming an ordering — the MNLI family is not consistent across checkpoints.
        label2id = {k.lower(): v for k, v in self.model.config.label2id.items()}
        self._entail_idx = label2id["entailment"]
        self._contradict_idx = label2id["contradiction"]

    def _pair_scores(self, pairs: Sequence[tuple[str, str]]) -> "list[float]":
        """Directional (P(entail) - P(contradict) + 1)/2 for each (premise, hypothesis)."""
        if not pairs:
            return []
        torch = self._torch
        out: list[float] = []
        bs = self.config.batch_size
        for start in range(0, len(pairs), bs):
            chunk = pairs[start : start + bs]
            premises = [p for p, _ in chunk]
            hypotheses = [h for _, h in chunk]
            enc = self.tokenizer(
                premises,
                hypotheses,
                truncation=True,
                max_length=self.config.max_length,
                padding=True,
                return_tensors="pt",
            )
            # Fail closed on truncation: a silently-truncated premise changes what
            # "grounded" means for that pair with no visibility. The corpus spec caps
            # source length; anything longer must be excluded upstream, not clipped here.
            if enc["input_ids"].shape[1] >= self.config.max_length:
                lengths = [len(self.tokenizer(p, h)["input_ids"]) for p, h in chunk]
                over = [i for i, n in enumerate(lengths) if n > self.config.max_length]
                if over:
                    raise ValueError(
                        f"NLI input exceeds max_length={self.config.max_length} for pair "
                        f"indices {over} in this batch; exclude or shorten the source text"
                    )
            enc = enc.to(self.device)
            with torch.no_grad():
                logits = self.model(**enc).logits
            probs = torch.softmax(logits, dim=-1)
            entail = probs[:, self._entail_idx]
            contradict = probs[:, self._contradict_idx]
            scalars = (entail - contradict + 1.0) / 2.0
            out.extend(float(x) for x in scalars.detach().cpu().tolist())
        return out

    def __call__(self, sources: Sequence[str], claim: str) -> float:
        """0002 scalar: max over sources of the bidirectional average, in [0,1]."""
        if not sources:
            return 0.0
        pairs: list[tuple[str, str]] = []
        for src in sources:
            pairs.append((src, claim))  # premise = source, hypothesis = claim
            pairs.append((claim, src))  # swapped direction
        scored = self._pair_scores(pairs)
        bidir = [(scored[i] + scored[i + 1]) / 2.0 for i in range(0, len(scored), 2)]
        return max(bidir)
