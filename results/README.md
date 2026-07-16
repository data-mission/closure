# Results

One folder per experiment run: `results/<experiment-id>/<run-id>/`, where `run-id` is `YYYY-MM-DD-<short-slug>`.

Each run folder contains:

- `PROTOCOL.md` — the exact protocol version used (link to the experiment README at the commit hash), plus any deviations, stated explicitly. Includes the run-discipline fields ([experiments/README.md](../experiments/README.md)): exact model checkpoint/version, full generation parameters and seeds, verbatim prompts, and the pilot-testing disclosure (how many design iterations preceded the registered run, and whether preliminary results shaped hypotheses or thresholds).
- `artifacts/` — raw outputs: scores, trajectories, transcripts, model/config identifiers, seeds where applicable. Exclusions applied are counted and listed with reasons, per the experiment's pre-registered exclusion criteria.
- `analysis/` — the code that produced the verdict from the artifacts. Re-runnable.
- `VERDICT.md` — the outcome, written strictly against the experiment's pre-registered confirm/refute conditions. If neither condition is met, say so; partial results are reported as partial. **Confirmatory findings** (specified in the protocol before the run) and **exploratory findings** (everything else) are labeled as such, in separate subsections — an exploratory result is never promoted by phrasing.

Negative results use the identical structure and receive the same review. A confirmed verdict (either direction) triggers a status update in [HYPOTHESES.md](../HYPOTHESES.md) in the same PR.

Runs recorded here:

- [E5 registered run, 2026-07-15](E5-reclosure/2026-07-15-registered-run/) — H-RELEASE refuted (mechanical contraction lost to instructed disregard, 10.3% vs 0.9% contamination). E3's earlier record lives in [experiments/E3-future-volume/run/](../experiments/E3-future-volume/run/), predating this folder's first entry.
