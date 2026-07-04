# Handoff: Mayo RoB2 evidence-layer foundation (2026-07-03)

## TL;DR

The RoB2 pipeline's inaccuracy AND its run-to-run inconsistency share ONE root cause:
the evidence layer is fully non-deterministic. The primary paper reaches the classifier
only through a stochastic LLM summary that drops a different set of sentences every run,
while the raw `full_text` is never searched. A card/prompt fix fleet (WS1/WS2/WS3) FAILED
validation and was reverted. The foundational fix - deterministic BM25 retrieval over the
raw paper - is PROVEN on a pilot (D2 SQ 2.6): GETUG-AFU-15's decisive "intention-to-treat"
sentence now reaches the packet deterministically, every run. Resume by extending that to
the other domains, pairing it with coverage_groups, then benchmarking LAST.
Philosophy: fix the foundation first; do not chase benchmark deltas while the substrate is
non-deterministic.

## Current state (git)

- **Working branch `zaid/k-vote-stabilization`** (HEAD ~ e71e75e): code is CLEAN (failed
  fleet reverted). Contains ADR-0007 (max_tokens fix, shipped earlier), ADR-0008
  (evidence-layer diagnosis + fix design), the failed-fleet spec + plan under
  `docs/superpowers/`, and this handoff.
- **`feature/adr-0008-primary-retrieval` @ 3715dd5**: the VERIFIED pilot -
  `rob2_pipeline/primary_paper_index.py`, `primary_paper_sources()` in
  `nodes/evidence_source_selection.py` (gated to SQ 2.6), state key `primary_index`, and
  `tests/test_primary_paper_retrieval.py` (5 tests pass on a real-trace fixture). Based on
  `82d8b0e`, so it lacks the ADR doc - rebase/integrate onto the working branch when
  resuming.
- **`validate/fix-fleet`**: the FAILED card/prompt fleet (WS1 D2 coverage_groups, WS2 D5
  guidance, WS3 D4 guidance). Reverted from the working branch. Reference only - DO NOT ship.
- **Uncommitted, leave as-is**: `data/references/overall_survival.csv` (M) and the
  GETUG-AFU-15 / SWOG-1216 PDF+supplement renames (untracked/deletions).

## Upstream alignment (Ali) - checked 2026-07-03

- Our branch is **0 behind / 11 ahead** of `origin/master` (Ali's mainline). No stale-copy
  risk.
- The LLM summary is ALL Ali's: `extract_paper_evidence` (`ingestion/evidence.py`) and
  ADR-0004 ("use LLMs for semantic evidence interpretation") are his, on his mainline. Do
  NOT unilaterally remove it.
- Key: on 2026-06-12 Ali introduced BM25S supplement retrieval, `SupplementIndex` in
  evidence packets, and removed the legacy RAG path. He is ALREADY migrating to
  deterministic BM25 - but only for supplements, not the primary paper. ADR-0008 completes
  that migration for the primary paper using his own machinery. This is a natural,
  well-aligned contribution to bring Ali (with determinism numbers + before/after), not a
  departure from his architecture.
- Governance: the additive deterministic retrieval is ours to build (evidence-assembly
  surface). Any decision to REDUCE/REMOVE the LLM summary is Ali's call - build the additive
  fix, measure whether the summary still adds value, and if the data shows it hurts, take
  the finding to Ali; do not rip it out unilaterally.

## What we established (deterministically, from trace data - no benchmark)

- Across the 5 k=5 baseline passes, every upstream evidence LLM node
  (`paper_evidence_extraction`, all 8 `evidence_family_mining_*`, `preliminary_info`)
  produced different output on all 5 passes. The per-SQ classifier packets were fully
  non-deterministic in ~every domain (distinct packet == passes), packet-length swings up
  to +/-34k chars.
- Mechanism: `candidate_sources()` (`nodes/evidence_source_selection.py`) builds a packet
  from supplements (bm25s, deterministic), ClinicalTrials.gov (deterministic), and the
  PRIMARY paper - which comes only from `state["evidence"]`, a stochastic LLM summary
  (`extract_paper_evidence`, `ingestion/evidence.py:87`). The raw `state["full_text"]` is
  never searched.
- Temperature is already 0 (`config.py:14`); gpt-oss-120b is non-deterministic at temp 0.
  A response cache exists (`cache.py`) but the benchmark runs `--no-cache`. Caching gives
  reproducibility, not single-run recall.

## What failed, and the lesson

- The card/prompt fleet: WS1 added `coverage_groups` to reserve a packet SLOT for the ITT
  sentence, but the real gap is RECALL (the sentence was never a candidate). WS2/WS3 were
  card-wording changes. A combined k=5 REGRESSED (D2 80->60, D3 90->70, D5 80->70) and the
  targets did not flip.
- The comparison was CONFOUNDED: an untargeted domain (D3) moved 20 points with zero code
  change, calibrating run-to-run noise at ~20pt/domain at k=5. Signal (2-3 target cells)
  was smaller than noise (~5 cells flip between identical runs).
- Synthetic guard tests passed but did not reflect production (they injected the evidence
  production fails to retrieve). Lesson: verify on REAL data; measure variance not point
  accuracy; never overfit to the 10-trial set.

## What works (the pilot)

- Deterministic BM25 over the raw `full_text`. De-risked: BM25 over GETUG-AFU-15's real
  parsed paper ranks the ITT sentence #1-2 for the 2.6 query. Pilot wired it in and the
  sentence reaches the 2.6 packet at slot 0, deterministically (present-once == present-
  every-run, since full_text and bm25s are both deterministic). Verified independently:
  diff isolated, no DO-NOT-TOUCH file touched, `fallback_sources` (LLM summary) preserved.
- NOT yet benchmarked - downstream accuracy/determinism impact is unmeasured by design.

## The philosophy (Zaid - keep this front of mind)

Fix the foundation before infinitely bug-fixing a system whose foundation is broken.
Prompt-tweak + re-benchmark loops are motion, not progress, while the evidence substrate is
non-deterministic. Retrieval completeness is deterministically checkable - verify there,
for free, before spending on the noisy benchmark.

## Plan (numbered - resume here)

1. Integrate `feature/adr-0008-primary-retrieval` onto `zaid/k-vote-stabilization` (rebase
   or cherry-pick 3715dd5) so ADR + pilot code are on one branch.
2. Extend deterministic primary-paper retrieval to the other domains' decisive evidence
   (D5 prespecification, D3 missing-outcome-data, etc.), gated per-SQ. Verify each
   deterministically from traces ("does the decisive sentence reach the packet every run?").
3. Pair primary retrieval (recall) with `coverage_groups` (guaranteed packet slot) - WS1's
   mechanism at the correct layer - so the decisive sentence is seated even when longer,
   term-heavy passages compete.
4. Evaluate reducing or removing the LLM summary (`fallback_sources`) once deterministic
   retrieval carries the load - decide WITH data whether it still adds value.
5. ONLY THEN: one paired, powered benchmark (baseline + treatment back-to-back) to measure
   the downstream accuracy + determinism gain. This is the sole real spend; it comes last.

## Open decisions

- Rollout scope: all 5 domains at once, or prove D5 first to confirm the pattern
  generalizes beyond D2? (Lean: D5 first.)
- Keep vs drop the LLM summary after deterministic retrieval proves out (decide with data).

## Budget / ops

- OpenRouter ~$12.46 available (verified via API). A k=5 over 10 trials is ~$1.4-1.8. The
  benchmark is the ONLY real spend and comes last.
- Claude weekly usage at ~90% on 2026-07-03; resets Sunday. Resume building after the reset.
- Benchmark launch: `outputs/benchmark/logs/run_kvote_watchdog.ps1 -Prefix <P> -K 5 -Trials
  ARASENS:OS,ARCHES:OS,CHAARTED:OS,ENZAMET:OS,LATITUDE:OS,PEACE-1:OS,STAMPEDE:OS,TITAN:OS,
  GETUG-AFU-15:OS,SWOG-1216:OS` (COMMA-separated, NO spaces - space-separated breaks arg
  binding). Score: `.venv/Scripts/python.exe docs/superpowers/tooling/kvote_score.py
  --prefix <P> --k 5 --trials <all 10 names>`. Run from main checkout (untracked PDFs +
  .env + .venv live there).

## Resume command

Fresh session on auto-rob2: read this handoff, then `CONTEXT.md`, `docs/adr/0008-*.md`, and
the auto-memory (evidence-layer-nondeterminism-root-cause, never-overfit-to-benchmark-set).
Then start at Plan step 1. Diagnostic scripts from this session are in the session
scratchpad (retrieval_determinism.py, where_nondeterminism.py, derisk_bm25_primary.py).
