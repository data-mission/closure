# Closure is not Design by Contract

A positioning argument. It exists because the strongest early objection to this program was "this is Design by Contract applied to AI — a 40-year-old idea," and that objection rests on a type error worth making explicit.

## The two concepts

**Design by Contract** is a *specification-and-checking* concept. Preconditions, postconditions and invariants are asserted; an external checker verifies them; the contract never produces the state it checks. Its form is `assert(P(x))`. DbC-style layers for LLM agents exist (e.g., arXiv:2508.03665 — a neurosymbolic contract layer) and are useful — as checking.

**Closure**, as defined in this program, is a *generative/equilibrium* concept. The state of interest is the fixed point of the computation's own reorganization: `x* = F(x*)`, where F is "reorganize until the persistent structures are mutually consistent with the constraints." The computation *finds* the state; nothing external asserts it. Its formal lineage is deep equilibrium models, Hopfield energy descent, energy-based models, and predictive coding — the equilibrium tradition, not the assertion tradition.

## Why the distinction matters operationally

- If closure is real (E0), then the G/R/P measurements are not contracts being checked — they are *instruments reading one physical property* of how the computation settled. That changes what improving them means: better instruments, not more assertions.
- The two traditions make different predictions about intervention. A checking layer can only accept/reject/retry. An equilibrium account predicts that *changing the boundary and re-closing* (E5's mechanical arm) outperforms *appending an assertion* (E5's instructed arm) — because the state, not the text, is the object. E5 is, among other things, an empirical test that separates the two framings.
- Lowering invariance (E6) is only a meaningful question in the equilibrium framing: an assertion means whatever its checker computes, but a property of the settled state should be checkable equivalently before, during, or after settling. If E6 confirms, the property belongs to the state; if it refutes, the checking framing was the right one all along.

## The type error, named

The original objection compared closure to DbC because DbC was the nearest neighbor in *product space* — both can be packaged as "a library that checks AI outputs." The nearest neighbor in *concept space* is the equilibrium tradition. Projecting a concept onto product-space neighbors is a recurring failure mode when evaluating new ideas against existing knowledge; this program's own history contains a full worked example ([reduction-history.md](reduction-history.md)).

No claim of settled truth is made here — this is a positioning argument, and the experiments (E0, E5, E6) are what settle it.
