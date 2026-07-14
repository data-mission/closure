# How the execution plan was derived

A companion to [reduction-history.md](reduction-history.md). That file records how the program's *concept* was
cut down; this one records how its *execution plan* — the decision records and E0's plan — was arrived at, so a
reader can see the reasoning behind the frozen choices rather than take them on assertion.

## The gap that was filled
The program had three of the four layers a research program needs: standards (CONTRIBUTING, METHODOLOGY, the
results contract), protocols (the eight experiment READMEs), and ledgers (the hypothesis registry, the citation
ledger). It lacked the middle layer — the engineering plan for building and running the measurement instrument —
even though CONTRIBUTING names that instrument "the highest-leverage engineering contribution available." The
decision records and `experiments/E0-closure-existence/PLAN.md` are that layer.

## How the choices were fixed
Each experiment protocol names *what* to measure but leaves open *how* — the estimator, not just the estimand. A
measurement's meaning is set by its estimator, so those open choices are not implementation detail; a different
clustering algorithm or aggregator changes the numbers the verdict is computed from. The decision records fix each
open choice to a justified default and mark it frozen-before-data, because a choice made after seeing the data is
a researcher degree of freedom the pre-registration exists to remove.

Two disciplines shaped the result:
- **Freeze before build.** The verdict rule is validated on synthetic score matrices *before* the harness is
  built, so its correctness is checked while the data is still throwaway. Building the scorer first would mean
  tuning its parameters against real output and watching the instrument behave — after which an honest
  pre-registration is no longer possible.
- **Attack before trust.** The plan was reviewed adversarially from several independent angles — reproducibility,
  statistical validity, coverage, and the ways a green result could be produced without the discipline actually
  holding. That review changed the plan. Two changes were load-bearing: the generation API exposes no seed, so
  exact reproducibility of model output is not available and E5's contraction had to be made algorithmic rather
  than a fresh model generation; and a factor-analyzability gate (KMO / Bartlett) was added, because factor
  analysis returns a structure even on data that was never suitable for it, which would otherwise yield a
  confident but meaningless verdict.

## Standing scope
Every decision record is `proposed`, not binding, until frozen in the E0 pre-registration on OSF. The plan is a
plan; no experiment has run. Its worth is that a total-refutation outcome still produces a decided question — the
same standard the rest of the program holds itself to.
