# RoB2 accuracy + determinism fix fleet - design

Date: 2026-07-02
Branch base: `zaid/k-vote-stabilization`
Status: design (awaiting spec review before implementation planning)

## Problem

The k=5 self-consistency run (`kvote_mt8k`, after the max_tokens truncation fix)
scores voted per-domain agreement D1 100 / D2 80 / D3 90 / D4 100 / D5 80 with 0%
voted instability. Two things remain:

1. **Five accuracy misses** (voted label != reference): GETUG-AFU-15 D2, PEACE-1 D2,
   GETUG-AFU-15 D5, TITAN D5, LATITUDE D3.
2. **Hidden run-to-run fragility** the k=5 vote masks: stray `High` votes surface in
   truly-Low domains (STAMPEDE D4 `LLHHL`, SWOG-1216 D3/D4/D5, ARASENS D3/D5,
   CHAARTED D3) and several cells sit one flipped vote from tipping (ARCHES D2
   `SLHLL`, ENZAMET D2 `LSSLL`). At k<5 some of these flip.

The goal is to raise accuracy across the five domains and reduce run-to-run variance,
touching only LLM-facing surfaces.

## What the audit ruled out

- **Truncation / infrastructure: dead.** Every stray High and every flagged cell shows
  `parse_failed=0`, `at-cap=0`, `empty-output=0` on its domain classifier across all 5
  runs. The max_tokens 2000->8000 fix (ADR-0007) fully closed the truncation->NI-fallback
  ->judge-High channel for the domain judgments. No residual infra cause.
- **k-vote aggregation: correct.** 0% voted instability; every majority is unambiguous.

## Root-cause map (traced from actual per-run signaling-question I/O)

Three distinct mechanisms, plus two defensible reference disagreements. All fixes are
LLM-facing (evidence assembly, methodology cards, classifier prompts). **None touch the
deterministic judge, the skip/NA logic, or the RoB2 Sterne-2019 algorithm.**

### WS1 - D2: retrieval variance on the analysis-population (ITT) evidence

- **Driver:** D2 judgement hinges on SQ 2.6 ("was an appropriate ITT analysis used?").
  For GETUG-AFU-15 (ref Low), the model answered 2.6=`NI` in 3/5 runs (-> Some concerns)
  and 2.6=`Y` in 2/5 (-> Low). Awareness SQs 2.1/2.2=`Y` are stable and correct.
- **Evidence:** the runs that answered 2.6=`Y` had the sentence "Efficacy analyses were
  by intention-to-treat" (run2) / "performed on an intention-to-treat basis" (run5) in
  the D2 analysis-stage evidence packet. The runs that answered `NI` did not surface that
  sentence; they foregrounded "one patient... analysed in the ADT+docetaxel *safety*
  population," which reads as an as-treated signal. Packet lengths differ every run
  (43447 / 47479 / 41784 / 44694), confirming non-deterministic evidence assembly.
- **Diagnosis:** retrieval variance, not reasoning variance or card wording. The D2 card
  prose is already correct (it warns against over-using `NI` and against counting
  protocol-consistent changes). The model reasons correctly *given its evidence*; the
  evidence-mining step inconsistently includes the deciding sentence.
- **Lever:** strengthen the D2 evidence contract / RAG so the analysis-population
  statement (ITT / mITT / per-protocol / as-treated) is *reliably* retrieved into the D2
  analysis-stage packet. Same lever should also surface trial-context deviation details
  that SQ 2.3/2.4 need.
- **Predicted effect:** GETUG-AFU-15 D2 miss flips to Low; D2 run-to-run wobble collapses
  (the NI-vs-Y flip is the wobble). PEACE-1 D2 (ref Some concerns) is a secondary target -
  it needs the deviation evidence for SQ 2.3/2.4 surfaced, but its correct label is partly
  a judgment call, so it may not fully flip.
- **Risk:** a stronger D2 evidence packet could move a currently-correct D2 cell. Validate
  with full k=5 and inspect all 10 D2 cells before/after.
- **Confidence:** high (accuracy + determinism), high leverage. Marquee lever.

### WS2 - D5: methodology gap, plan-vs-reported diff

- **Driver:** for GETUG-AFU-15 D5 (ref Some concerns) the model judged Low across all 5
  runs because "the outcome is registered on ClinicalTrials.gov." It never compared the
  pre-specified plan against what was reported.
- **Evidence (from the paper, via the reference-rationale research pass):** GETUG-AFU-15
  documents a *data-driven* change to the analysis plan - "initially planned with only 36
  months of follow-up," then the sponsor extended follow-up to a July 2011 cutoff, plus
  explicit post-hoc subgroup analyses. That is a selection-of-reported-result concern the
  card does not prompt for.
- **Lever:** revise the D5 card (and its evidence contract) to diff pre-specified plan vs
  reported result - outcome list, OS timepoint, analysis timing, post-hoc additions -
  raising Some concerns when the reported result reflects an *unplanned / data-driven*
  deviation from the plan.
- **Hard boundary:** the change must catch *unplanned* deviations only. TITAN's interim
  analysis and alpha-spending were *pre-specified*; a card that flags any interim as Some
  concerns would wrongly regress TITAN and others. Pre-specified interims stay Low.
- **Predicted effect:** GETUG-AFU-15 D5 flips to Some concerns; TITAN D5 stays Low.
- **Risk:** over-triggering D5 on clean pre-specified trials. Validate + inspect all D5
  cells before/after.
- **Confidence:** medium-high.

### WS3 - D4/objective-outcome: reasoning variance

- **Driver:** STAMPEDE D4 (ref Low) voted `LLHHL`. The two High runs answered SQ 4.2=`Y`
  (and 4.4/4.5=`Y`) - outcome measurement could be influenced by assignment awareness -
  while the Low runs answered 4.2=`N`. Packet lengths are ~identical between a Low run
  (135844) and a High run (135859), so this is not retrieval-driven.
- **Diagnosis:** reasoning variance. Overall survival (death) is an objective outcome that
  cannot be measurement-biased by knowledge of assignment; 4.2=`N` is correct. The model
  occasionally over-reasons it to `Y`.
- **Lever:** reinforce in the D4 card / classifier prompt that for objective mortality
  endpoints, outcome ascertainment is not influenced by assignment awareness (SQ 4.2/4.3
  default toward `N` absent specific evidence of biased ascertainment). Optionally raise
  the evidence bar for the most-cautious answer so a `High` requires explicit strong
  evidence.
- **Hard boundary:** must not systematically bias toward Low - only suppress *unjustified*
  High/Some-concerns votes, or we trade determinism for accuracy.
- **Open item:** SWOG-1216 D3 stray-High could not be traced to a `domain3_sq` node (no
  such call in the trace; ties to a `maxOT=0` anomaly on D3-High rows). The WS3 worker
  must first locate SWOG's D3 judgement path (cached / differently-named node) before
  concluding its mechanism.
- **Confidence:** medium. Lowest priority - these cells already vote correctly at k=5.

### Defensible reference disagreements (out of scope, documented)

- **TITAN D5:** interim OS + alpha-spending were pre-specified (Wang-Tsiatis boundary,
  public protocol + SAP, registered matches reported). Model's Low is legitimate; the
  reference's Some concerns is a conservative call. Chasing it would mean overfitting the
  D5 card to a debatable label and regressing the general case.
- **LATITUDE D3:** model's Low correctly reflects negligible loss-to-follow-up but misses
  that OS was an immature interim readout (406/852 required deaths). Strict RoB2 treats
  planned-interim censoring as normal follow-up, so filing this under D3 is itself an
  arguable adjudicator choice (the reference put LATITUDE's early-stopping under D3 and
  TITAN's identical early-stopping under D5 - evidence these are conservative judgment
  calls). Fixing D3 risks regressing other trials for one debatable cell.

Honest accuracy ceiling: 3 of 5 misses are fixable (GETUG D2, PEACE-1 D2 partially,
GETUG D5); 2 are the pipeline reasonably disagreeing with a borderline gold label.

## Anti-overfitting gate (governing rule, overrides scoreboard)

The 10 benchmark trials are simultaneously the training and test set; there is no
held-out set. "No regression on the 10" is therefore necessary but NOT sufficient - it
cannot detect a change that helps these 10 while degrading an unseen trial. The defense
against overfitting is principled, not empirical:

- **Derivability test.** Every change must be justifiable from the published RoB2 /
  Sterne 2019 guidance *without reference to our trials*. A reviewer must be able to
  answer "yes" to: "would this change be correct for a trial we have never seen?" If a
  change's only justification is that it makes a specific cell pass, it is overfitting and
  is rejected - even if it improves the scoreboard. Each change cites its Sterne 2019
  basis (page/section).
- **Prefer mechanism over judgment.** A change that alters *what evidence the model sees*
  (retrieval reliability, evidence contract) is inherently general and cannot encode a
  trial-specific answer. A change that alters *what verdict the model reaches* (card
  wording that nudges a borderline label) is the overfit vector - it shifts the decision
  boundary for unmeasured cases. Mechanism fixes are preferred; judgment-wording fixes get
  the strictest review and must express a general principle, never a trial-specific pattern.
- **Generalization signal via leave-motivation-out.** A change is motivated by 1-2 cells
  but is validated across ALL cells it could touch. It must be neutral-or-positive on the
  other trials, not just non-regressive on its target. A change that helps only its
  motivating trial and wobbles others is overfit and rejected.
- **Per-workstream overfit risk:** WS1 (retrieval) lowest - a mechanism fix with no
  trial-specific content. WS3 (objective-outcome) low - a direct Sterne principle. WS2
  (D5 wording) highest - must express the general "pre-specified plan vs reported result"
  principle, never GETUG's specific follow-up-extension pattern, and never a blanket
  "interim = concern" that regresses pre-specified-interim trials like TITAN.

The review gate for every workstream explicitly applies the derivability test and rejects
trial-specific tuning.

## Orchestration structure

Per the orchestrator fleet pattern. The orchestrator does not implement.

- **Isolation:** one git worktree per workstream off `zaid/k-vote-stabilization`. No
  worker touches the shared checkout. WS1 and WS2 edit different surfaces (evidence
  store/RAG vs D5 card) and can design in parallel; WS3 edits the D4 card/prompt.
- **Workers:** Opus for all three (each needs RoB2 judgment). WS1 = evidence-store / RAG
  query focus; WS2 = methodology-card + evidence; WS3 = card/prompt, most delicate.
- **Review gates:** an independent Opus reviewer per workstream (1) applies the
  anti-overfitting derivability test - would this change be correct for an unseen trial,
  justified from Sterne 2019 without reference to our 10 trials? - and rejects
  trial-specific tuning; (2) re-derives the change against RoB2 guidance; (3) confirms *no*
  judge / skip-NA / algorithm code was touched and no AI attribution was added. Fix rounds
  go back to the warm original worker by name.
- **Assembly:** the orchestrator merges approved changes, runs validation, writes the
  before/after ADR, and brings numbers to Zaid. Zaid gates any push/PR.

## Validation plan

Budget now allows multiple k=5 runs (funding being added). Validate **one variable per
k=5 run** for clean attribution:

1. WS1 (D2 evidence) alone -> k=5 -> score with `kvote_score.py` over all 10 trials.
2. WS2 (D5) alone -> k=5 -> score.
3. WS3 (D4/variance) alone -> k=5 -> score. Validated **last** so a bad variance change
   cannot contaminate the WS1/WS2 wins.
4. Combined confirmation k=5 over all merged changes.

**Gate for every run:** (1) no regression on any currently-correct cell (all 45 correct
cells of the 50 must stay correct); (2) the targeted cell(s) must move as predicted; (3)
generalization - the change must be neutral-or-positive across all cells it could touch,
not just helpful on its motivating trial (leave-motivation-out); (4) report the full
per-cell vote distribution, not just point accuracy (measure variance). A change that
passes (1) and (2) but fails (3), or that cannot pass the derivability test, is rejected as
overfitting regardless of the scoreboard. Each validated
change gets an ADR-style write-up (problem / root cause / change / before-after numbers)
in Ali's documentation style.

## Hard constraints (all workstreams)

- LLM-facing surfaces only: evidence assembly / RAG queries, methodology cards, classifier
  prompts, evidence contracts. NEVER the deterministic judges, skip/NA logic, or the RoB2
  Sterne-2019 algorithm.
- No AI attribution in any commit or PR. Push to the fork (`Z-ai-dAnwar`), never origin
  (Ali). No PR without Zaid's approval.
- No em-dashes. `.env` holds live secrets - never print.
- k>=5 for any scored validation; report the distribution.
