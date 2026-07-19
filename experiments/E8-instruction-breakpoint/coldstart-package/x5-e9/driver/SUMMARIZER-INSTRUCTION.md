# E9 — the summarizer (compaction operator) instruction

DRAFT — to be frozen by content hash at registration, exactly like ARM-B-INSTRUCTION.md
(pin recorded in the E9 registration §5, verified at load time in run_e9.py, mismatch HALTS).

Selected (at registration) as the strongest FAITHFUL-COMPRESSION prompt subject to the frozen
compression band (DESIGN.md §10 fix), after an adversarial candidate review — a lossy strawman
summarizer makes an accumulation result worthless, and a near-lossless one never exercises the
operator. The instruction optimizes retention AT the pinned compression ratio.

The compaction operator replaces the live context with the summary this instruction produces; the
model then continues reasoning from the summary plus the next correction. The summary is the ONLY
memory that survives the cycle — anything it drops is gone.

> You are compacting a working context so reasoning can continue from a shorter version. Produce a
> summary that another reasoner will use as its ONLY record of everything so far — the original
> documents will not be available to it. Your summary MUST be between 30% and 50% of the length of
> the material you are given (this is a hard requirement of the compaction step). Within that budget,
> preserve with the highest priority: (1) every quantitative figure that is still in force, with its
> label; (2) every correction or supersession that has occurred, stated as the current truth (do not
> preserve a figure that has been superseded as if it were live — record the current value, and note
> that it replaced an earlier one); (3) every intermediate conclusion still needed to answer the
> question. Drop restatement, framing, and decorative narration first. Do not introduce any figure or
> conclusion not present in the material. Do not resolve the final question — only compact the record
> needed to resolve it.
