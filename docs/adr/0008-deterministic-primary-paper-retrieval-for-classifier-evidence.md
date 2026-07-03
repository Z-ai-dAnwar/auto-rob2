# ADR-0008: Deterministic primary-paper retrieval for classifier evidence

Date: 2026-07-03
Status: Proposed (pilot in progress)

## Context

Run-to-run variance and a substantial share of the accuracy misses in the RoB 2
pipeline trace to a single root cause: the evidence layer is fully
non-deterministic. This was established directly from trace data, without any new
benchmark run.

Measured over the 5 passes of the k=5 baseline (`kvote_mt8k`):

- Every upstream evidence LLM node produced a different output on all 5 passes:
  `paper_evidence_extraction`, all eight `evidence_family_mining_*`, and
  `preliminary_info` were "5 distinct / 5 passes" for every trial checked.
- The per-signaling-question classifier packets were fully non-deterministic
  (distinct packet == passes) in essentially every domain: D1 10/10, D2 (both
  stages) 10/10, D4 8/8, D5 9/9, D3 6/7 trials. Packet-length swings reached
  ±34,000 characters between passes of the same trial.

Mechanism. A classifier's evidence packet is assembled by
`candidate_sources()` (`nodes/evidence_source_selection.py`) from three sources:

1. Supplements: retrieved with **BM25** (`supplement_retrieval.py`, `bm25s`) -
   deterministic.
2. ClinicalTrials.gov: registry fields from state - deterministic.
3. The **primary paper**: reached only through `state["evidence"]`, a sectioned
   summary produced by `extract_paper_evidence()` (`ingestion/evidence.py:87`),
   which is an **LLM call** (`paper_evidence_extraction`). A deterministic
   structural parser exists but runs only as a fallback when the LLM fails.

So the most important document - the trial paper - is the only one of the three
sources that is laundered through a stochastic LLM summary rather than searched
deterministically. The raw paper text is present in `state["full_text"]` but is
never searched; the existing BM25 machinery is pointed only at supplements.

Consequence. The decisive evidence for a signaling question is present in some
passes and absent in others. Example (GETUG-AFU-15, D2 SQ 2.6, "was an
appropriate ITT analysis used?"): the sentence "efficacy analyses were by
intention-to-treat" appeared in 2 of 5 baseline passes and 0 of 5 passes in a
later run. When it is absent, the model answers `NI`, the deterministic judge
routes the domain to Some concerns, and the assessment is wrong; when it is
present only sometimes, the domain judgment wobbles run to run. Temperature is
already 0 (`config.py:14`), so this is the reasoning model's inherent
non-determinism and cannot be removed by sampling settings.

Prior attempt (reverted). A change that added `coverage_groups` to reserve a
packet slot for the analysis-population sentence failed in production: it fixed
RANKING (guarantee a slot if the sentence is a candidate) while the real gap is
RECALL (the sentence never becomes a candidate, because the stochastic summary
dropped it). A synthetic unit test passed because it injected the sentence as a
candidate; production retrieval does not reliably produce it.

## Decision

Add a deterministic retrieval path over the primary paper's raw `full_text`,
reusing the existing `bm25s` index machinery, and have `candidate_sources()`
retrieve decisive per-signaling-question evidence directly from it. This reduces
the classifier's dependence on the stochastic LLM summary for the load-bearing
evidence.

This does not reverse ADR-0004 (LLM-led semantic evidence interpretation): the
LLM still interprets the evidence and answers the signaling questions. We change
only how candidate evidence is *retrieved* into the packet - from a stochastic
summary to a deterministic keyword search - so that the LLM's interpretation
operates on a complete and stable input. It also respects ADR-0001 (domain
evidence context limited to prompt assembly): the change lives entirely in
evidence assembly.

## Alternatives considered

1. Determinize the extraction LLM (temperature/seed). Rejected: temperature is
   already 0; gpt-oss-120b is non-deterministic at temp 0 and provider routing
   varies.
2. Cache the LLM extraction. Gives reproducibility (same paper -> same answer on
   re-run) but freezes whichever incomplete extraction was produced; does not fix
   single-run recall. Orthogonal production-reproducibility question; defer to Ali.
3. Make the extraction/mining prompts more exhaustive. Helps at the margin but
   stays stochastic and is not verifiable without runs.
4. (Chosen) Deterministic BM25 over primary `full_text`. Deterministic, complete
   (finds the sentence if it exists in the paper), reuses existing infrastructure,
   and is verifiable from traces with zero benchmark spend.

## Consequences

- Positive: removes the retrieval-driven variance for the primary paper;
  guarantees recall of decisive evidence; makes "is the evidence present?" a
  deterministic yes/no, decoupling evidence-completeness work from noisy LLM
  scoring so progress can be verified without the benchmark.
- Risk: BM25 chunks are noisier than clean LLM summaries. The primary-paper
  retrieval must integrate with the existing ranking/selection so the packet is
  not flooded, and the LLM summary is kept as complementary context rather than
  removed, to avoid regressions. Validate that decisive-evidence recall improves
  without displacing other needed evidence.
- Out of scope / untouched: the deterministic judges, the skip/NA control, and
  the RoB 2 (Sterne 2019) algorithm.

## Implementation (pilot first)

1. Build a primary-paper `bm25s` index over `state["full_text"]`, reusing the
   `SupplementIndex` machinery (`supplement_retrieval.py`).
2. Add a `primary_paper_sources()` producer to `candidate_sources()`, retrieving
   by the per-contract query, tagged with a distinct `source_kind`.
3. Pilot scope: D2 SQ 2.6 (analysis-population) only.
4. Deterministic acceptance test: on GETUG-AFU-15's real parsed `full_text`, the
   2.6 retrieval returns the "intention-to-treat" analysis sentence (RED before
   this change, GREEN after). Because `full_text` is deterministic and BM25 is
   deterministic, "present once" implies "present every run".
5. If the pilot deterministically surfaces the decisive evidence, extend the
   primary-paper retrieval to the decisive evidence types of the other domains.

## Verification

- Deterministic, no benchmark: on real trial `full_text`, assert the decisive
  sentence is retrieved for the target SQ and reaches the packet.
- Only after evidence recall is confirmed deterministically do we spend on a
  paired, powered benchmark to measure the downstream accuracy and determinism
  gain - not before.
