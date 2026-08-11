# Review Log

Per PROJECT.md Section 9: after each phase a reviewer pass checks the diff for
correctness vs the spec, statistical validity, and rubric coverage. Any spec
concern is flagged here, never silently "fixed" — the model is professor-approved.

---

## Phase 1 review — engine, policies, validation suite (2026-08-10)

**Process.** Adversarial multi-agent review: four independent lenses
(spec conformance vs Sections 3–4, lookahead/state leakage, statistical
validity, numerical edge cases), each raw finding then attacked by two
independent verifier agents that tried to refute it with actual code runs.
Only findings surviving both verifiers were accepted.

**Raw findings: 3 · Confirmed: 1 · Refuted: 2.**

### Confirmed and fixed

1. **[major] Future-perturbation lookahead check was vacuous**
   (`src/validation.py`, `no_lookahead_check` leg (a)).
   The helper evaluated decisions only for `t < t_perturb` on slices
   `p[:t+1]`, while the "future" shock was applied at `t >= t_perturb` — so
   the shocked prices were never shown to the policy and the check could not
   fail *for any policy*, including a deliberately lookahead-seeking one
   (verified by both refuters with mutation tests: injecting a real
   full-array leak into the harness left the named test green). The property
   was in practice protected only by the structural tests (decide() signature,
   the Recorder copy/slice test, vectorised-vs-stepwise equality).
   **Fix applied:** leg (a) now runs through the *real* harness
   (`run_policy_path`) on full price series and compares all trades before
   `t_perturb` between the base and future-shocked runs — for the EMA policy
   *and* for a future-hungry probe policy that trades on `max(history)` and
   flips immediately if even one future price leaks. The check also asserts
   the probe actually trades on the shocked series (the canary is live).
   Docstring corrected.

2. *(adopted although formally refuted — see below)* The zero-noise
   grid-vs-buy-and-hold assertion combined two marginal SEs via
   `hypot(se, bh_se)` as if independent, but the P&L vectors share common
   random numbers (measured correlation with BH up to +0.89), making the
   acceptance band ~2.9× wider than the correct paired-difference band and
   the test blind to entry-price biases up to ≈ 0.035. One verifier confirmed
   every number, the other judged it "working as intended"; the confirmation
   rule (2/2) formally killed it, but the paired-difference version is
   strictly more powerful and matches the Lecture-7 CRN methodology used
   everywhere else in the project.
   **Fix applied:** `zero_noise_check` now also reports paired-difference
   means/SEs vs buy-and-hold and the test asserts on those.

### Refuted (no change)

- **"ema_profits diverges from run_policy_path for negative unit with
  allow_exit"** — refuted: `unit` is validated/used only as a positive
  position size; no caller can produce the alleged state, and the
  vectorised-vs-stepwise equality test covers the supported parameter space.

**Spec deviations found: none.** The Layer-1/2/3 math, clip bounds, EMA
recursion, grid, and benchmarks match PROJECT.md Sections 3–4 exactly
(kappa=1 reproduces variant A path-for-path; verified in tests).

**Post-fix status:** 31/31 tests green.

---

## Phase 2 review notes — experiments (2026-08-10)

Self-review (full adversarial pass deferred to the final audit): CI math uses
`ddof=1` and `z = Phi^{-1}(0.975)`; every policy at a sweep point is evaluated
on common paths (CRN); comparisons vs buy-and-hold are paired differences;
sweep points use offset seeds so batches are independent across points; the
headline table records CI-significance (`any_ema_beats_bh`) rather than a bare
mean comparison. Headline result documented in the Phase-2 commit message,
reproducible with seed 20260812.

## Extension: Poisson news jumps (2026-08-11) — SPEC FLAG per Section 9

Section 3 marks the model as LOCKED. At the team owner's request we added an
**optional, default-OFF** extension rather than changing the approved model:
with per-period probability `jump_rate` (Bernoulli arrivals = discrete-time
Poisson process, geometric interarrivals), Layer 1 takes an extra zero-mean
N(0, jump_scale²) shock, damped by the same sqrt(q(1-q)) factor.

Safeguards:
- `jump_rate = 0` (the default everywhere) consumes **no** extra random
  numbers, so the approved model's seeded output is bit-for-bit unchanged —
  pinned by a golden-value test captured from the pre-extension engine.
- Zero-mean jumps preserve the martingale property, so the Section-7
  martingale and settlement-calibration checks hold with jumps on (tested).
- All committed results (results/, report/figures/, summary.md) use the
  approved model only. The dashboard exposes the extension behind a clearly
  labelled toggle marked "beyond the professor-approved model".
- **Professor sign-off pending** — until given, the extension stays a
  demo/limitations talking point, not a reported result.

## Final audit (2026-08-10)

A three-auditor adversarial workflow (spec/rubric coverage, numeric-claim
verification, runnability) was launched but its agents were cut off by an
account usage limit, so the audit was completed inline instead:

- **Pushed state:** working tree clean; local `main` == `origin/main` on
  GitHub after every phase commit.
- **Runnability:** `pytest` 31/31 green; all `src` modules import;
  `dashboard/app.py` compiles; dashboard verified interactively in the
  browser (all five tabs, live Polymarket fetch, prefill, offline fallback).
- **Numeric claims:** every figure in `results/summary.md` was extracted
  programmatically from the CSVs it cites at writing time (not typed from
  memory); the executed `notebooks/analysis.ipynb` recomputes the same
  tables from the same CSVs.
- **Fix applied:** Python 3.14 SyntaxWarning for `\$` escapes in the About
  tab markdown (now a raw string).

Re-running the multi-agent audit once limits reset is recommended but not
blocking; the per-phase reviews above already covered the engine (the
highest-risk 30% of the rubric) adversarially.

## Phase 3 review notes — calibration (2026-08-10)

Scope guard honoured: calibration only sets inputs (q0, sigma_q, sigma_p), no
fitting or backtesting. The moment estimator is validated on simulated data
with known parameters (recovers both sigmas within 25% on a T=20k series) and
the offline path is tested with a simulated network outage. Five real markets
bundled (fetched 2026-08-10) so the demo never depends on the API.
