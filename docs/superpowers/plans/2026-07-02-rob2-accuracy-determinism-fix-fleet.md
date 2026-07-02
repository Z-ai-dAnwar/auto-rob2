# RoB2 Accuracy + Determinism Fix Fleet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise RoB2 voted accuracy on the 3 fixable misses (GETUG-AFU-15 D2, PEACE-1 D2, GETUG-AFU-15 D5) and reduce run-to-run variance, touching only LLM-facing surfaces and without overfitting to the 10-trial benchmark.

**Architecture:** Three independent LLM-facing changes, each in its own git worktree, each validated by a single-variable k=5 benchmark run. WS1 is a retrieval-contract change (mechanism), WS2 and WS3 are methodology-card `guidance`-string changes (judgment, tightest review). No change touches the deterministic judge, skip/NA control, or the RoB2 algorithm.

**Tech Stack:** Python 3.13, the auto-rob2 LangGraph pipeline, gpt-oss-120b via OpenRouter, pytest. Benchmark scored by `docs/superpowers/tooling/kvote_score.py`.

Design basis: `docs/superpowers/specs/2026-07-02-rob2-accuracy-determinism-fix-fleet-design.md`.

## Global Constraints

Every task's requirements implicitly include this section.

- **LLM-facing surfaces only.** Permitted: evidence contracts/queries (`nodes/evidence_contracts.py`, `nodes/evidence_packets.py`, `nodes/evidence_source_selection.py`), methodology cards (`methodology/domain*.py`), classifier prompts (`prompts.py`, `methodology/render.py`).
- **DO-NOT-TOUCH (deterministic, published algorithm).** All of `rob2_pipeline/judges/*.py`; all of `rob2_pipeline/nodes/sq_control.py`; `rob2_pipeline/nodes/common.py:set_na`; the D5 selective-reporting guard `rob2_pipeline/nodes/domain5.py:71 apply_domain5_selective_reporting_guard`. A change that requires editing any of these is out of scope - stop and escalate.
- **Anti-overfitting derivability gate (overrides the scoreboard).** Every change must be justifiable from the published RoB2 / Sterne 2019 guidance WITHOUT reference to our 10 trials. Cite the Sterne 2019 basis (page/section) for each guidance change. Reject any change whose only justification is "it makes cell X pass," even if it improves the benchmark. Prefer mechanism fixes (what evidence the model sees) over judgment fixes (wording that nudges a label). A change motivated by 1-2 cells must be neutral-or-positive across all cells it could touch.
- **Live-path caveat (from the code-surface map).** On the live `*_json` classifier path, `card.notes` and `card.algorithm_note` are NOT emitted - only `response_rules[answer].guidance` reaches the model (via `evidence_packets.py:328 build_decision_table()`). Card-guidance changes MUST go in `response_rules[...].guidance`, never in `notes`/`algorithm_note`, or the model never sees them. Every card change carries a guard test proving the new text appears in the emitted decision table.
- **Process:** TDD (write the failing test, watch it fail, minimal change, watch it pass). Worktree per workstream, never the shared checkout. No AI attribution in commits/PRs. Push to the fork (`Z-ai-dAnwar`), never origin (Ali). No PR without Zaid's approval. No em-dashes. `.env` holds live secrets - never print.
- **Validation:** single-variable k=5 per workstream; report the full per-cell vote distribution, not just point accuracy.

---

## Shared context for all workers

- Every target node runs the **packet path**: `nodes/domain_classifier.py:53 run_json_sq_classifier()` -> `:127 build_classifier_prompt()` -> `:117 packets_for_stage()`. Packets are built upstream by `nodes/evidence_packets.py:72 build_evidence_packets()` -> `:229 _build_packet_for_contract()` per `CONTRACTS[sq]` in `nodes/evidence_contracts.py`.
- Source selection/ranking: `nodes/evidence_source_selection.py:30 candidate_sources()` (RAG retrieve by contract `terms`); top-N with reserved slots by `evidence_packets.py:185 _select_with_coverage()`.
- Card guidance -> prompt: `evidence_packets.py:328 build_decision_table()` reads `rule_cards[sq].response_rules[answer].guidance`.

---

## WS1 - D2 SQ 2.6 analysis-population retrieval (PRIORITY, mechanism fix)

**Root cause:** D2 judgement hinges on SQ 2.6 ("was an appropriate ITT analysis used?"). For GETUG-AFU-15 (ref Low) the model answered 2.6=NI in 3/5 runs (-> Some concerns) and Y in 2/5 (-> Low). The runs that answered Y had the sentence "efficacy analyses were by intention-to-treat" in the packet; the NI runs did not. `CONTRACTS["2.6"]` (`evidence_contracts.py:142`) has ITT `terms` but no `coverage_groups`, so the analysis-population sentence is crowded out of the top-N by ranking. Contracts 3.1 (`:171`) and 5.3 (`:290`) already reserve a slot with `coverage_groups`.

**Files:**
- Modify: `rob2_pipeline/nodes/evidence_contracts.py:142` (`CONTRACTS["2.6"]` - add `coverage_groups`).
- Test: the evidence-packet test module (worker locates the existing packet/coverage test pattern, e.g. tests covering `_select_with_coverage` or `build_evidence_packets`).

**Interfaces:**
- Consumes: `_select_with_coverage()` (`evidence_packets.py:185`) already honors `coverage_groups`; no change needed there if only adding a group.
- Produces: a D2 analysis packet that reliably contains an analysis-population source when the paper states one.

- [ ] **Step 1: Write the failing test.** Using the existing packet-builder test fixtures, construct (or reuse) a trial whose sources include an analysis-population sentence ("efficacy analyses were by intention-to-treat") that ranks below the top-N on the current `terms`-only 2.6 contract. Assert the built 2.6 packet's selected sources include that analysis-population sentence. It should FAIL today (sentence crowded out).
- [ ] **Step 2: Run it, watch it fail** for the right reason (sentence absent from selected sources), not a fixture error.
- [ ] **Step 3: Minimal change.** Add a high-precision `coverage_groups` to `CONTRACTS["2.6"]` reserving one slot for analysis-population/analysis-set terms (intention-to-treat, ITT, mITT, per-protocol, as-treated, full analysis set, analysis population), modeled exactly on the 3.1/5.3 pattern. Do not alter ranking logic or other contracts.
- [ ] **Step 4: Run it, watch it pass;** run the full evidence-packet test module and confirm no other packet regresses.
- [ ] **Step 5: Commit** (`git add` the contract + test; imperative-subject message, no attribution).

**Boundary / anti-overfit:** the coverage group is a general analysis-population reservation - it must help any trial that reports its analysis population, not encode GETUG's wording. Sterne 2019 D2 SQ 2.6 basis: appropriateness of the analysis (ITT/mITT) is the SQ 2.6 subject.

**Validation (after review):** k=5, prefix e.g. `kvote_ws1`. Predicted: GETUG-AFU-15 D2 -> Low; D2 wobble on ARCHES/ENZAMET/GETUG collapses; PEACE-1 D2 may partially move. Gate: no regression on any currently-correct cell; report full distribution.

---

## WS2 - D5 plan-vs-reported guidance (judgment fix, TIGHTEST review)

**Root cause:** For GETUG-AFU-15 D5 (ref Some concerns) the model judged Low across 5 runs because a registration exists; it never compared the pre-specified plan to what was reported. GETUG documents a data-driven plan change (follow-up extended from a planned 36 months to a July 2011 cutoff) plus post-hoc subgroup analyses - a selection-of-reported-result concern.

**Files:**
- Modify: `rob2_pipeline/methodology/domain5.py` (`response_rules[...].guidance` for the relevant SQ among 5.1/`:17`, 5.2/`:43`, 5.3/`:70`). Guidance strings only - never `notes`.
- Test: assert via `build_decision_table()` that the new guidance text appears in the emitted D5 decision table (live-path proof).

**Interfaces:**
- Consumes: `evidence_packets.py:328 build_decision_table()` renders `response_rules[answer].guidance`.
- Produces: D5 guidance that distinguishes pre-specified analyses/interims (not a concern) from unplanned/data-driven deviations (Some concerns).

- [ ] **Step 1: Write the failing test.** Assert the emitted D5 decision table (from `build_decision_table` for the target SQ) contains the plan-vs-reported principle wording. FAILS today.
- [ ] **Step 2: Run it, watch it fail.**
- [ ] **Step 3: Minimal change.** In the target SQ's `response_rules` guidance, encode the GENERAL principle: when the reported result reflects an unplanned or data-driven departure from the pre-specified analysis plan (changed outcome/timepoint, extended follow-up decided after seeing data, added post-hoc analyses selected for reporting), that supports a Some-concerns direction; a result produced by a PRE-SPECIFIED plan or pre-specified interim analysis (with alpha-spending) does NOT. Worker authors exact wording; cite Sterne 2019 D5 (selection of the reported result, SQ 5.1-5.3).
- [ ] **Step 4: Run it, watch it pass;** run the full methodology/packet test modules.
- [ ] **Step 5: Commit.**

**Boundary / anti-overfit (critical):** the wording must express the general pre-specified-vs-unplanned distinction, NEVER "detect follow-up extended from 36 months" (GETUG overfit) and NEVER "any interim analysis is a concern" (would regress TITAN, whose interim was pre-specified). TITAN D5 must stay Low; verify in validation.

**Validation:** k=5, prefix `kvote_ws2`. Predicted: GETUG-AFU-15 D5 -> Some concerns, TITAN D5 stays Low. Gate: no regression on any currently-correct D5 cell; report full distribution.

---

## WS3 - D4 objective-outcome guidance (reasoning variance; VALIDATE LAST)

**Root cause:** STAMPEDE D4 (ref Low) voted LLHHL; the High runs answered SQ 4.2=Y (outcome measurement influenced by assignment awareness) on ~identical packets - reasoning variance, not retrieval. For objective mortality endpoints (death/OS), ascertainment is not influenced by awareness, so 4.2/4.3 should default toward N. The existing objective-outcome nuance lives in `notes`/`algorithm_note`, which the live path DROPS, so the model never sees it.

**Files:**
- Modify: `rob2_pipeline/methodology/domain4.py` (`response_rules[...].guidance` for 4.2/`:35` and 4.3/`:61`). Guidance strings only.
- Test: assert the objective-outcome guidance appears in the emitted D4 decision table via `build_decision_table()` (proves it reaches the live path, unlike the current notes).

**Interfaces:**
- Consumes: `build_decision_table()` renders `response_rules[answer].guidance`.
- Produces: D4 4.2/4.3 guidance that steers objective mortality endpoints toward N absent specific evidence of biased ascertainment.

- [ ] **Step 0: Investigate the SWOG-1216 D3 anomaly.** The audit found SWOG-1216 D3 stray-High but no `domain3_sq` node in its trace (a cached / differently-named path, tied to a `maxOT=0` observation). Determine SWOG's D3 judgement path before assuming WS3's mechanism covers it; if it's a separate path, report and keep D3 out of this workstream's change.
- [ ] **Step 1: Write the failing test.** Assert the emitted D4 4.2 decision table contains the objective-outcome guidance. FAILS today (guidance only in dropped notes).
- [ ] **Step 2: Run it, watch it fail.**
- [ ] **Step 3: Minimal change.** Add to 4.2/4.3 `response_rules` guidance the GENERAL principle: for objective outcomes such as all-cause mortality / overall survival, outcome ascertainment cannot be influenced by knowledge of assignment, so absent specific evidence of biased ascertainment the answer trends N. Cite Sterne 2019 D4 (objective outcomes / measurement of the outcome). Worker authors wording.
- [ ] **Step 4: Run it, watch it pass;** run full methodology/packet test modules.
- [ ] **Step 5: Commit.**

**Boundary / anti-overfit:** must not bias D4 toward Low generally - the steer applies only to genuinely objective outcomes (mortality/OS), which is the benchmark's outcome. Do not suppress legitimate High for subjective outcomes.

**Validation (LAST, after WS1/WS2 banked):** k=5, prefix `kvote_ws3`. Predicted: stray D4/D5 High votes drop; voted labels unchanged where already correct. Gate: no regression on any currently-correct cell; report full distribution.

---

## Integration validation

After each workstream passes its own review + k=5 gate, a final combined k=5 (prefix `kvote_combined`) over all merged changes, scored across all 10 trials. Gate: all previously-correct cells stay correct; the 3 targeted misses moved as predicted; TITAN D5 + LATITUDE D3 unchanged (documented defensible). Each validated change gets an ADR-style write-up (problem / root cause / change / before-after numbers) in Ali's style. Orchestrator assembles; Zaid gates any push/PR.

## Per-workstream review gate (independent Opus reviewer)

1. Apply the anti-overfitting derivability test; reject trial-specific tuning.
2. Confirm the change reaches the live classifier path (guard test present and passing).
3. Confirm NO file in the DO-NOT-TOUCH list was modified; no AI attribution added.
4. Re-derive the change against Sterne 2019; confirm the cited basis is real.
Fix rounds go to the WARM original implementer by name.

## Self-review (this plan vs the spec)

- Spec coverage: WS1/WS2/WS3 + defensible residuals (frozen) + anti-overfit gate + single-variable validation - all present.
- Placeholder scan: card-guidance wording is intentionally worker-authored under a precise principle + boundary + Sterne citation + guard test (not a TODO); WS1's mechanism change is concrete.
- Type/name consistency: node/function/line references taken verbatim from the code-surface map.
