# D2 accuracy: 2.6 retrieval re-aim + 2.4 amendment guidance (Focused)

**Date:** 2026-06-10
**Branch:** `zaid/d2d3-inference-retrieval` (off master `0e69799`)
**Author:** Zaid Anwar (Mayo RoB 2)

## Problem

Domain 2 verdicts oscillate run-to-run on the same trial. Diagnosed on PEACE-1
across two runs (`d2d3-fix-peace-titan` vs `d2d3-fix-23verify`): the AI returned
**Low** in one run and **High** in the other, never the reference verdict
**Some concerns**.

Root cause is **retrieval nondeterminism**, not model sampling noise on a fixed
prompt. The two runs fed the AI *different evidence packets*:

- **SQ 2.6 ("appropriate ITT analysis?")** flips Y -> NI depending on whether the
  analysis-population sentence reaches the packet. The phrase is provably in
  PEACE-1's sources ("intention-to-treat" x4, "all randomised" x4), and 2.6
  already has both coverage terms (`ANALYSIS_POPULATION_COVERAGE_TERMS`) and
  strong inference guidance. The failure is upstream: **2.6's RAG queries are
  aimed at the statistical-analysis-plan / pre-specification topic** ("statistical
  analysis plan adherence", "analysis method as pre-specified"), which is D5
  selective-analysis territory, NOT "all randomized patients were analysed in
  their assigned group." So the ITT-population chunk only enters the candidate set
  by luck. `_select_with_coverage` reserves a slot only among *already-retrieved*
  candidates; it cannot rescue a chunk retrieval never surfaced.

- **SQ 2.4 ("deviations likely to affect outcome?")** was answered PY off a
  *reasoning misread*: the AI treated the protocol amendment (sample-size increase,
  docetaxel allowed in standard-of-care) as a deviation from intended intervention.
  A design-level protocol amendment is not a per-participant departure from the
  assigned intervention in the 2.3/2.4 sense.

## Scope decision: Focused (not Broad, not Minimal)

PEACE-1 reaching a *stable* "Some concerns" requires three signaling questions to
align in one run (2.3 stably catching the deviation, 2.4/2.5 resolving Part1 to
Some, 2.6 stably finding ITT). We deliberately do NOT chase all three. Forcing the
2.5 "balance" axis toward Y would bias D2 toward Low and break any future trial
with a genuinely unbalanced deviation - overfitting to one paper.

We make only the two changes that are **correct on their own merits and general to
every RCT**, then measure. If PEACE-1 still wobbles, we accept it as a borderline
reference case.

## The two changes

### Change 1 - re-aim SQ 2.6 retrieval (primary, root cause)
File: `rob2_pipeline/rag_queries.py`, `SQ_QUERIES["2.6"]`.
Add natural-language queries that target the analysis-population statement so the
ITT chunk reliably enters the candidate set, e.g.:
- "all randomized participants were included in the analysis"
- "patients analysed in the group to which they were assigned"
- "intention-to-treat population"

The existing `ANALYSIS_POPULATION_COVERAGE_TERMS` then reserves the slot and the
existing Y/PY inference guidance reads it. Keep (do not remove) the existing SAP
queries; this is additive. No coverage-term or guidance change needed for 2.6.

### Change 2 - SQ 2.4 amendment guidance (general reasoning correction)
File: `rob2_pipeline/methodology/domain2.py`, the 2.4 `RuleCard`.
Add a clarifying note/rule: a protocol amendment to trial *design* (sample size,
eligibility, concomitant therapy permitted across all arms) is not itself a
deviation from intended intervention; assess 2.4 on actual per-participant
departures (non-receipt, switching, contamination). Pure RoB 2 methodology, no
trial named.

## Out of scope (explicit)
- No change to 2.5 / the deviation-balance axis (overfitting trap).
- No change to 2.3 retrieval (just landed in `958ea55`; its stability is a separate
  measurement question).
- No change to judges / `sq_control.py` (deterministic Sterne 2019 - never touched).

## Guard (must hold)
- **ENZAMET** is `2.3=N -> 2.4/2.5=NA -> Part1 Low`, `2.6=Y`. Confirmed empirically
  in `d2d3-fix-23verify`. Neither change can move it: 2.4 is NA (never evaluated),
  2.6 is already Y. This is the look-alike trial the fix must not break.
- **TITAN** win was 2.6 inferring PY; re-aimed 2.6 retrieval should reinforce, not
  disturb, a correct Y/PY.
- coverage/anchor matching is casefold SUBSTRING - any new term must be a
  high-precision phrase (no bare "itt").

## Acceptance test (decided before coding)
1. Unit tests (TDD): a retrieval test proving the analysis-population chunk is
   selected into 2.6's packet given candidate sources that contain it; a
   methodology/guidance test for the 2.4 amendment rule. Full suite stays green
   (currently 491 passed).
2. k>=3 benchmark on the 8 scoreable trials (gpt-oss-120b, free tier + watchdog),
   compared against the baseline (`postmerge_gptoss_k3_run1`: D1 100 / D2 75 /
   D3 75 / D4 100 / D5 87.5).
3. Success = (a) ENZAMET stays Low across all runs, (b) TITAN D2 stays Low/win,
   (c) 2.6 stops flipping Y<->NI where the ITT statement exists, (d) no other trial
   regresses. PEACE-1 landing on Some is a *bonus*, not the pass condition.

## Order of operations
TDD changes 1 + 2 -> full unit suite green -> STOP for diff review -> only then
k>=3 benchmark (spend gate, Zaid's call).
