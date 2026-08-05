# Full-system audit, 2026-08-05

One ranked list of everything found wrong, produced by six parallel read-only review agents.
**Nothing in here has been fixed.** The audit was explicitly scoped to find and rank, not repair,
so that the fix targets get picked deliberately rather than in the order an agent happened to
trip over them.

- **Audited**: working tree on `zaid/k-vote-stabilization` at `14d29ec`, which is
  `upstream/master` (`82d8b0e`, Ali's last commit 2026-06-12) plus roughly 1,700 lines of our own
  branch work.
- **Cost**: zero. No benchmark was run and no model was called. Every number below is arithmetic
  over files already on disk, or a claim verified by reading code.
- **Attribution** is given per finding, because "ours" and "upstream" get fixed differently.

---

## What I would fix first

Read this section and skip the rest if you only have five minutes.

**The single most important finding is not a bug in the pipeline. It is that the reference set
cannot be matched by a correct implementation.** On 17 of its 28 rows the human reference assigns
"Some concerns" to at least one domain and still records an Overall of "Low". The published RoB 2
algorithm forbids that: Overall Low requires Low in every domain. So the "Overall 47-54%" that
this project has been chasing since May was never a pipeline defect. A faithful implementation
can score at most 40% on OS Overall, and every point above that would have to come from breaking
the algorithm. I verified this myself from the CSVs, independent of the agent that raised it:
6 contradictory rows in OS, 6 in PFS, 5 in AE.

That reframes three months of work. It also means the very first question is not "how do we fix
the pipeline" but **"is the reference set right?"** Either the expert applied a different rule
than the published one, or the Overall column was filled in separately from the domains. Somebody
has to ask the human who produced it. No amount of code work resolves it.

**Second: the pipeline contains a layer that systematically converts uncertainty into "Low".**
There are 23 automatic answer-rewriting rules in `nodes/sq_control.py` and `nodes/domain5.py`.
Sixteen move an answer toward Low or benign, four toward concern, three are neutral, and all four
concern-direction rules are D4-only with companions that cap D4 at Some concerns. On this
reference set, where every trial is overall survival, only one of the rules that can fire points
toward concern. Evaluated against a reference that is 81% "Low", a layer that flips toward Low
raises the agreement number while destroying the ability to detect bias, which is the only thing
the system is actually for.

**Third, and this is the one I would fix first among the code defects because it is one line:**
`rob2_pipeline/nodes/evidence_packets.py:238` sorts candidate evidence by BM25 score ascending.
BM25 is a similarity, so higher is better; ascending order picks the *least* relevant source
first. Among sources tied on matched terms and role rank, which is the common case, the best
passage is pushed toward the 3-slot cut and dropped.

**Fourth: `rob2_pipeline/nodes/sq_control.py` contains literal sentences from the benchmark PDFs,
including an OCR artifact** (`inthe adt with docetaxel population for efficacy`, lines 314 and
321; `plus abiraterone`, `plus prednisone` and a de-spaced variant at lines 87-90). That is
benchmark overfitting compiled into the judging path. It cannot generalize to any trial outside
the ten, and it only ever moves answers toward the benign side.

**One thing that is emphatically NOT broken, and it matters:** the deterministic judges in
`rob2_pipeline/judges/` reproduce the published Sterne 2019 tables exactly, verified row by row,
including the subtle case where 2.4=NI correctly does *not* skip 2.5. The skip/NA branching is
correct too. Every judgment defect found in this audit lives *upstream* of the judges, in the
node layer and the prompts. The standing rule never to touch the judges stays intact and is not
in tension with fixing any of this.

---

## The verified numbers

Computed directly from `data/references/*.csv`. These correct and extend the figures in the
2026-08-04 brief.

### Label distribution and the trivial baseline

| File | n | D1 | D2 | D3 | D4 | D5 | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OS | 10 | 100 | 90 | 70 | 100 | 80 | 100 |
| PFS | 10 | 100 | 90 | 70 | **40** | 80 | 70 |
| AE | **8** | 100 | 87.5 | 62.5 | 50 | 87.5 | 75 |
| Pooled | 28 | 100 | 89.3 | 67.9 | 64.3 | 82.1 | 82.1 |

Each cell is the score for answering "Low" to everything without reading a word. Across all three
files: 113 Low, 27 Some concerns, **zero High**. The brief's OS row is exactly right.

Two corrections to the brief. **AE has 8 trials, not 10** (no CHAARTED, no GETUG); the "140 cells"
figure is still right, by 10+10+8 = 28 rows x 5 domains. And **PFS D4 is the one column in the
whole corpus where always-Low loses** (40%), because its majority class is "Some concerns".

### The three outcome files are mostly the same sample

- D1 is "L" in all 28 rows. Zero variance, so it carries no information at all.
- D2 is "S" for PEACE-1 and only PEACE-1, in all three files. One fact counted three times.
- D3 is "S" for exactly {ARCHES, LATITUDE, STAMPEDE} in all three files. Fully redundant.
- Of the 50 distinct (trial, domain) pairs, **44 carry an identical label in every file they
  appear in**. The only 6 that vary are all D4.

**Effective sample size is 11 distinct trials and 50 distinct cells, of which only 12 are ever
non-Low.** The 140-cell figure is inflated about 2.8x by duplication. One flip moves a domain by
12.5 points at n=8 and 10 points at n=10. No confidence interval is computed anywhere in the repo.

### What the July work actually did

The headline k=5 run (`kvote_mt8k1..5`, 2026-07-01/02, 10 OS trials) re-scored offline at zero
cost. The reproduction matches the recorded numbers exactly, including the `kvote_combined`
regression, so the method is sound.

| Domain | voted agreement | always-Low | delta | recall on "Some concerns" | Cohen's kappa |
| --- | --- | --- | --- | --- | --- |
| D1 | 100 | 100 | **0** | n/a (no S cells) | undefined |
| D2 | 80 | 90 | **-10** | **0% (0/1)** | **-0.11** |
| D3 | 90 | 70 | **+20** | 67% (2/3) | 0.74 |
| D4 | 100 | 100 | **0** | n/a (no S cells) | undefined |
| D5 | 80 | 80 | **0** | **0% (0/2)** | **0.00** |

Pooled over the 50 domain cells: **90.0% against an 88.0% always-Low baseline. A net gain of one
cell out of fifty.** The system answered "Low" in 47 of 50 cells; the reference is Low in 44. Its
entire margin over reading nothing is ARCHES D3 and STAMPEDE D3 — the only non-Low labels it ever
gets right in the whole grid. Overall recall on "Some concerns" is 2/6 = 33%.

D2 kappa is negative, meaning worse than chance. D5 kappa is exactly zero, meaning
indistinguishable from chance. Both report as "80%".

### Run-to-run spread, which the reporting format hides

Individual passes of that same k=5 set: D2 = 80, 80, 60, 80, 80. D4 = 100, 100, 90, 90, 90. The
`kvote_combined` set is worse: D2 = 40, 60, 70, 80, 80, a **40-point spread across five identical
invocations**. Every report prints a single point estimate to one decimal place with no spread and
no n. Most of the improvements recorded across June and July are inside that noise.

---

## Ranked findings

Severity is about consequence, not effort. **Critical** means it produces wrong judgments or makes
results unmeasurable. **High** means silent information loss, unreproducible runs, or a number
that cannot be trusted. **Medium** and **Low** follow.

### Critical

**C1. The reference Overall column contradicts the published algorithm on 17 of 28 rows.**
`data/references/*.csv`. Overall Low requires Low in every domain; 17 rows have a non-Low domain
and an Overall of Low (OS 6, PFS 6, AE 5). A correct implementation cannot exceed 40% on OS
Overall. Independently verified from the CSVs. *Not a code defect — a question for the human who
produced the reference.*

**C2. The reference set cannot distinguish work from no work.** 81% one class, zero High
judgments, effective n of 11 trials. Always-Low ties or beats the best result ever produced on
four of five domains. Every "D1 100" and "D4 100" since May measured a column with zero variance.
*Confirmed and extended from the 8/4 brief.*

**C3. 23 auto-flip rules, 16 of them pointing at Low.** `nodes/sq_control.py`,
`nodes/domain5.py:71-203`. Deterministic string and regex matches over the model's own text
rewrite its answers before the judge sees them, then re-run the judge on the rewritten answers
(`judges` re-invoked at `domain2.py:185-203`, `domain3.py:60-66`, `domain4.py:72-82`,
`domain5.py:435-443`). Full rule-by-rule table in the appendix. *Ali's upstream, `175b514`.*

**C4. "No information" is coerced to the benign answer in seven places upstream of the judges.**
`sq_control.py:598`, `:741`, `:777`, `:292`, `:413`; `domain5.py:83`, `:105`, `:188`. The judges
route NI correctly; the node layer never lets them see it. In RoB 2, NI is deliberately not
equivalent to "probably no" — that distinction is the Some-concerns floor, and this erases it.
This is the mechanism by which the pipeline can score 81% Low against a reference that is 81% Low
without reading evidence. *Ali's upstream.*

**C5. A total classifier failure is laundered into D3 = Low.** `sq_control.py:258-306`. The guard
explicitly whitelists the fallback's own failure strings — `"classifier fallback"` at `:261` and
`"no relevant text found"` at `:263` — then rewrites 3.1 to PY and attaches a **hardcoded quote
the paper may never contain** (`:270-278`). The case with the least information becomes "outcome
data were nearly complete". *Ali's upstream.*

**C6. Literal benchmark-PDF text, including an OCR artifact, is compiled into the flip rules.**
`sq_control.py:87-90` (`"plus abiraterone"`, `"plus prednisone"`, `"not randomly assigned
according to docetaxel prescription"` and its de-spaced variant) and `sq_control.py:314` and
`:321` (`inthe\s+adt\s+with\s+docetaxel\s+population\s+for\s+efficacy` / `...for safety`).
`domain5.py` hardcodes `"psa progression"`, `"skeletal event"`, `"coprimary endpoints"`. Verified
by hand. These are phrases from the ten prostate-cancer trials; they cannot generalize, and they
only ever move answers toward benign. *Ali's upstream.*

**C7. For any vital-status outcome, five NI answers are rewritten into a forced D4 = Low.**
`sq_control.py:718-800` (rules at `:725`, `:741`, `:777`, `:794`). Model answers 4.1-4.5 all NI;
the node layer rewrites four of them; the judge then correctly returns Low. Under the published
algorithm those same five answers give **High**. All ten reference trials are overall survival and
all ten have reference D4 = "L", so this converts total ignorance into agreement. *Ali's upstream.*

**C8. D3's time-to-event guard erases every possible concern for survival outcomes.**
`sq_control.py:376-431`, assignment at `:413`. `_is_time_to_event_outcome` matches a bare
substring against `("survival", "time to", ...)`, true for every reference trial. The guard fires
whenever the rationale mentions death or progression — unavoidable for an overall-survival
rationale — and does not contain censoring vocabulary, rewriting 3.1 to PY, which returns Low
immediately. *Ali's upstream.*

**C9. D5 has five flip rules and all five point at Low.** `domain5.py:71-203`. There is no rule
in the opposite direction. The gate `_has_prespecified_reported_outcome_evidence` requires only
that the outcome name, one of {protocol, primary endpoint, prespecified}, and one of {reported,
hazard ratio} appear anywhere in the concatenated text — satisfied by every registered oncology
RCT, making two of the rules effectively unconditional. *Ali's upstream.*

**C10. D5 polarity is inverted: the RoB 2 trigger phrases for "Y" are coded as evidence against
Y.** `domain5.py:282-331`, specifically `:306`, `:317`, `:318`. SQ 5.2/5.3 ask whether a result
was selected from *multiple eligible* measurements or analyses. `misleading_signals` lists
`"multiple eligible outcomes"`, `"multiple eligible analyses"`, `"multiple analyses were
possible"` — matching any of them downgrades Y/PY to PN. Meanwhile `verification.py:100-105`
flags any 5.2/5.3 Y/PY whose justification lacks the word "multiple". Say it and you get flipped;
omit it and you get flagged. Also `"only a subset"` appears as a downgrade trigger at
`domain5.py:308` and as a downgrade *blocker* at `:399`. *This is the D5 polarity regression.
Ali's upstream.*

**C11. Every contract or parse failure degrades into a plausible answer instead of an error, and
the one field that would reveal it is permanently empty.** `llm_contracts.py:89-95` returns
`fallback_factory(...)` with no exception after retries. `domain_classifier.py:329-359` fills
every SQ in the stage with NI. And `benchmark.py:1536-1540` reads `schema_failures` /
`schema_validation_failures` from the pipeline output, but **neither key exists in
`JSON_OUTPUT_KEYS`** (`pipeline.py:23-83`), so the list is always `[]`, "Schema validation
failures: 0" is hardcoded truth, and the `"parse"` mismatch category can never fire. A run where
every domain fell back to NI has the same diagnostic surface as a clean run. *Ali's upstream.*

**C12. The RCT screener's failure path scores as a real result.** `nodes/ingest.py:56-63` →
`graph.py:104-108` → `pipeline.py:123-135` → `benchmark.py:1613-1632`. The screener's fallback
hard-codes `is_rct: False`; the graph routes to `END`; no domain runs; `run_assessment` returns
normally so `error` is `None` and `skipped` is `False`; the benchmark compares `""` against
`"Low"` and records 0/6 for that trial. This is the full path of the June k=3 Haiku zeroing. The
headline reads "Trials evaluated: 8" with a 0% agreement rate that looks like a model result.
*Ali's upstream.*

**C13. Errored and skipped trials are deleted from the denominator rather than counted.**
`benchmark.py:1613-1614`. A crash shrinks n silently, so consecutive runs report percentages over
different samples. Already happened repeatedly on disk: `newmaster_gptoss_k3_run1..3` evaluated 5
of 8 after ARCHES, ENZAMET and STAMPEDE errored — and ARCHES and STAMPEDE are two of the three
D3="Some concerns" trials, so D3 was scored on a subset containing one S cell instead of three.
`kvote_fix1` (n=10) and `kvote_fix2` (n=9) were compared as before/after. Dropping only
GETUG-AFU-15 from the headline run moves **D2 from 80.0 to 88.9 and D5 from 80.0 to 88.9** with no
judgment changing. A test locks the behavior in at `tests/test_benchmark.py:806-813`. *Ali's
upstream.*

I counted this across every run on disk. **Ten past runs scored fewer trials than they requested,
and none of them says so in its headline:**

| run | requested | evaluated | errored | skipped |
| --- | --- | --- | --- | --- |
| `kvote_fix2` | 10 | 9 | 1 | 0 |
| `newmaster_gptoss_k3_run1` | 8 | 5 | 3 | 0 |
| `newmaster_gptoss_k3_run2` | 8 | 5 | 3 | 0 |
| `newmaster_gptoss_k3_run3` | 8 | 5 | 3 | 0 |
| `newmaster-smoke` | 1 | 0 | 1 | 0 |
| `postmerge_gptoss_k3_run1` | 10 | 8 | 0 | 2 |
| `postmerge_gptoss_k3_run2` | 8 | 6 | 2 | 0 |
| `postmerge_k3_run1` | 10 | 8 | 0 | 2 |
| `postmerge_k3_run2` | 10 | 8 | 0 | 2 |
| `postmerge_k3_run3` | 10 | 8 | 0 | 2 |

**C14. A trial whose name fails to resolve vanishes from the score with only a log warning.**
`benchmark.py:1422-1440`. Both "not in reference" and "PDF not found" set `skipped=True`, which
routes into C13. Already happened: `postmerge_k3_run1..3` requested 10 and reported 8. **The state
on disk right now guarantees a recurrence.** The `GETUG-AFU 15` → `GETUG-AFU-15` rename in the OS
CSV is an *uncommitted working-tree edit*, so a fresh checkout silently drops GETUG from OS. And
PFS cannot be fixed by any spelling: the PFS reference still has the space while the PDF has the
hyphen, so `'GETUG-AFU-15'` resolves the PDF but not the reference, and `'GETUG-AFU 15'` resolves
the reference but not the PDF. GETUG in PFS is the only row in that file with both D4=S and D5=S,
the most informative row there, and it currently cannot be scored. *Ali's upstream; the partial
rename is ours and uncommitted.*

**C15. `judges/overall.py` ships a policy that reproduces the reference Overall column exactly.**
`judges/overall.py:55-58`, `:86-92`. `_benchmark_reference_low` returns Low whenever no domain is
High and at most one is Some concerns. Run over all 28 reference rows it contradicts the reference
**0 times**, where the official Sterne rule contradicts it 17 times. It is named after the
benchmark and its rationale string says "Benchmark-reference policy". It is off by default
(`state_factory.py:95` sets `official_rob2`) and is one state key away from turning the Overall
metric into a tautology that would look like a legitimate accuracy win. *Ali's upstream,
`1c4a9e9`.*

**C16. The prompt-budget guard truncates the tail, which is exactly where the JSON schema lives.**
`llm_contracts.py:26-36`, applied at `:77-79`; prompt assembled at `:186-200`. `_contract_prompt`
appends the schema and the "return exactly one JSON object" instruction *last*, and
`enforce_prompt_budget` cuts with `prompt[:max_chars]`. Over the cap, the first thing destroyed is
the output contract. The retry cannot recover because `_repair_prompt` is *longer* than the
original and gets trimmed harder, so the call lands in the all-NI fallback. ADR-0006 specified
dropping the lowest-ranked evidence and logging each drop; the implementation is a blind character
slice. *Our branch, `e7cb995`.*

**C17. Candidate evidence is sorted by BM25 relevance ascending, so the least relevant source
wins ties.** `nodes/evidence_packets.py:233-240`, offending key at `:238`. `supplement_retrieval.py:84-86`
stores the raw BM25 similarity, where higher is better; the `1e9` default for a missing score
suggests the author read it as a distance. Verified by hand. Reproduced on GETUG-AFU-15's real
text: the passage containing "efficacy analyses were done by intention to treat" is the top BM25
hit at 1.846 and is ranked **last** among term-matching candidates, so the packet is built from
the 1.395, 1.442 and 1.476 passages instead. *Ali's upstream, arrived with PR #168.*

**C18. `retrieval_repair` rebuilds a byte-identical packet, then the SQ is force-answered NI with
no LLM call.** `nodes/retrieval_repair.py:70-89`, rebuild at `:77`. It computes three repair
queries at `:157-184` and never executes them, calling `build_packet_for_contract(state, contract)`
with the same state and contract. The packet keeps `needs_retrieval_repair`, which is a blocking
status, so `domain_helpers.py:139-166` hard-codes that SQ to NI and the classifier is never asked.
`added_source_ids` is therefore always `[]`. *Ali's upstream.*

**C19. A truncated model response is indistinguishable from a complete one.**
`providers/openrouter.py:98-109`, and the same in `anthropic.py` and `openai.py`. `finish_reason`
has **zero occurrences** in the entire package. A response cut off at `max_tokens` is handed
downstream as normal. If the truncated JSON happens to close, it validates and becomes real
answers; if it is reasoning-only, `content or ""` makes it an empty string that fails into the
silent fallback. ADR-0007 measured 58 empty-output calls in one k=2 pass. `LLMResponse`
(`providers/base.py:20-32`) has no field to carry a truncation flag. *Ali's upstream.*

**C20. Nothing computes per-class recall, a chance-corrected statistic, a confidence interval, or
a trivial baseline.** `benchmark.py:1653-1662`, `:1977-1994`, `:891-912`;
`self_consistency.py:100-107`; `docs/superpowers/tooling/kvote_score.py:81-94`. A repo-wide grep
for `kappa|AC1|PABAK|chance|per-class|macro` returns nothing in any scoring context, and
`always low|trivial baseline|majority class` returns nothing in any doc. Every score in the
project is raw agreement. This is why D2 at kappa -0.11 and D5 at kappa 0.00 both read as "80%".
*Ali's upstream design; our k-vote layer reproduced it.*

### High

**H1. Confusion matrices are computed and then never shown to a human.** Computed at
`benchmark.py:1591-1601`, `:1628`, `:1644`, `:1672` and written into `benchmark_results.json`;
zero references inside `write_benchmark_report` (`:1952-2263`) or `_engineering_report`
(`:891-1011`). The one artifact that would have exposed the always-Low collapse is buried in JSON
nobody reads.

**H2. The rate limiter never throttles, because a fresh one is built on every call.**
`config.py:56-84` has no memoization, and both `llm_contracts.py:65` and `nodes/common.py:120`
call `build_provider()` per call, each constructing a `SlidingWindowRateLimiter` with empty deques
(`_rate_limiter.py:31-33`). `ROB2_RPM_LIMIT` and `ROB2_RPD_LIMIT` are dead configuration.
**Fixing this activates H3**, so fix them together.

**H3. The daily limit sleeps up to 24 hours inside a held lock.** `_rate_limiter.py:40-52`. A run
that trips it appears hung, not failed, with only a `logger.warning` — and no `logging.basicConfig`
exists anywhere in the repo. Currently unreachable only because of H2.

**H4. Retry classification does string matching on an error whose HTTP status has been thrown
away.** `providers/openrouter.py:21-57`, `:138-140`. The handler re-raises a plain `RuntimeError`,
so the numeric branch at `:22-32` never executes and `retry_terms` contains no codes except
`"429"`. A 500/502/503 whose body lacks the exact phrase is treated as permanent and raised on the
first attempt; a 429 whose body contains "invalid request" is also treated as permanent. The
escaped error then routes into C13 and shrinks the denominator.

**H5. The cache key is `sha256(node_name + prompt)` and excludes model, provider, temperature and
`max_tokens`.** `cache.py:25-28`. Switching models replays the previous model's answers under the
new model's name, and a cache hit logs `"model": None`. Raising `max_tokens` from 2000 to 8000
does not invalidate anything, so a cached truncated response survives the fix — a textbook "we
fixed it and the benchmark showed no change". Blast radius is currently limited: the cache is
opt-in and off by default, and only `evidence_family_mining` is cacheable (see H7). Also
`read_cache` runs *before* `enforce_prompt_budget`, so entries are keyed on the untrimmed prompt.

**H6. No benchmark output records git commit, model, provider, temperature, `max_tokens`, prompt
budget, or k.** `benchmark.py:848-883`, `:1952-1970`; `pipeline.py:23-83`. A grep for any of those
across the 87 KB of `benchmark.py` returns nothing. The envelope hashes the input PDFs but records
nothing about what produced the results. **No past benchmark number in this repo can be attributed
to a code state.** Per-call model and provider do survive in `{trial}_trace.json`. *The new
`scripts/run_benchmark.ps1` records commit, branch, dirtiness, provider and model in its
done-marker, which partly covers this from the outside.*

**H7. `evidence_family_mining` makes 8-16 LLM calls per trial whose output nothing ever reads.**
`graph.py:113-115`, `evidence_family_mining.py:10-16`, `evidence_store.py:493`, `:510`. It writes
`evidence_store` and `selected_evidence_facts`; the only consumers are the workspace writer that
dumps them to `facts.jsonl`. No prompt builder and no judge references either. The classifier uses
`packet["candidate_facts"]`, produced deterministically by `source_to_fact`. Pure latency and cost
on the critical path.

**H8. The whole primary paper reaches the classifier through one LLM call with an 8,000-token
output cap, and the deterministic parse of the same text is computed and thrown away.**
`ingestion/evidence.py:87-114`; `ingestion/assessment.py:173-179` overwritten at `:212-225`. The
model must reproduce ten sections plus tables in one bounded JSON response, covering reasoning
*and* output. Nothing merges the deterministic sections back in as a union. On the ADR-0008
fixture the summary compressed 57,679 characters to 11,562 and dropped the decisive ITT sentence
entirely.

**H9. ADR-0008 displaces the LLM summary instead of supplementing it, and covers 1 of 21 signaling
questions.** `nodes/evidence_source_selection.py:93-123` on `feature/adr-0008-primary-retrieval`.
The ADR states the summary "is kept as complementary context"; measured on its own fixture the 2.6
packet goes from 6,576 characters (summary only) to **1,065** (pilot), because the rank-encoded
scores beat `section_text` on the third sort key and there are only three slots. The decisive
sentence is recovered and 84% of the packet's other content is evicted. The branch test asserts
only that the ITT sentence is present. Coverage is `PRIMARY_RETRIEVAL_PILOT_SQS = {"2.6"}`; all of
D1, D3, D4, D5 and the rest of D2 still reach the classifier only through the stochastic summary.
*Our branch.*

**H10. ADR-0008's rank-encoding works around C17 rather than fixing it, and is load-bearing.**
`evidence_source_selection.py:113-123`. With the real BM25 score the pilot fails its own acceptance
fixture. It also discards score magnitude, so a near-zero-scoring primary passage still enters as
"rank 0" and can outrank a genuinely strong supplement hit. *Our branch; the underlying bug is
upstream.*

**H11. The classifier's evidence surface is bimodal, and which mode runs is decided by regexes over
stochastically-selected text.** `domain_classifier.py:107-114`; branch at `domain1.py:38-46` and
the same in domains 2-5. If every SQ in a stage is "ready" the domain runs the packet-only
classifier; if any one is not, the whole stage falls back to a completely different and much wider
prompt. Readiness comes from `missing_evidence()`, regex matching over packet text that was itself
selected from the stochastic summary. The *shape* of the prompt therefore flips run to run.

**H12. In the packet path — the default — the model never sees the signaling-question text or the
methodology notes.** `domain_classifier.py:127-182`; `evidence_packets.py:328-379`.
`build_decision_table` copies only `rule_card.response_rules`, dropping `question`, `notes`,
`algorithm_note` and `applicability`. All the carefully written polarity guidance in
`methodology/*.py`, and everything in `prompts.py`, reaches the model only on the fallback path.
Whatever is right or wrong in those cards, **the primary path is not what has been tuned.**

**H13. The D1 methodology card instructs PY on the basis of trial infrastructure, not concealment
evidence.** `methodology/domain1.py:65`. It tells the model to answer PY rather than NI for 1.2
for "large multicenter cooperative-group trials with stratified randomization, balanced groups" —
which describes all ten reference trials, all of which have reference D1 = "L". Cochrane's
criterion for 1.2 is the concealment mechanism. D1 is the one domain with no flip layer, so the
bias sits in the card instead.

**H14. Three prompt-level instructions convert "not reported" into the benign answer.**
`prompts.py:266` (2.3), `prompts.py:628` (5.2/5.3), `methodology/domain5.py:39` (5.1). The last
lowers the 5.1=Y bar to "a registration number combined with a prespecification claim", but 5.1
asks whether the analysis plan was finalized *before unblinded outcome data were available*, which
a registration number does not establish.

**H15. The guards fabricate quotes attributed to the paper, and verification runs too late to
matter.** `sq_control.py:153-156`, `:270-278`, `:579-583`; `quote_verifier` runs after all five
domain judges. A synthesized quote that fails verification lowers a confidence label and leaves
the Low judgment standing, because nothing re-judges.

**H16. `kvote_score.py` defaults to an 8-trial subset that deletes both problem trials, and
compares against a hardcoded stale baseline.** `docs/superpowers/tooling/kvote_score.py:33-42`,
`:45`. `TRIALS_8` omits GETUG-AFU-15 and SWOG-1216 — exactly the two with the naming defect — and
nothing in the output says which set was used. On that default subset the headline run scores
**exactly the always-Low baseline on four of five domains**. `K3_BASELINE` is a frozen literal
from an old run, and it is a mean-per-run number printed as a delta against a voted number, so the
delta column is arithmetic between two different metrics. *Our branch.*

**H17. The two scorers in the repo disagree about what counts and in which direction.**
`benchmark.py:51-59` vs `self_consistency.py:19-33` recognize different label strings, so the same
run file scores differently depending on which tool reads it. And `self_consistency.py:126-137`
counts an unresolvable trial as a *disagreement* while `benchmark.py:1613` *drops* it. The
k-vote design is the correct one; the inconsistency means "80% D2" means two different things.

**H18. Rate-limit and network errors inside evidence mining are swallowed into "failed claims"
and the run still produces judgments.** `evidence_store.py:492-498`, `:516-523`. A bare
`except Exception` makes a connection failure indistinguishable from "no evidence found". ADR-0007
confirms 11 truncated mining calls silently lost facts before any domain saw them.

**H19. ClinicalTrials.gov failures return `None` silently, stripping the evidence D5 depends on.**
`registration_api.py:49-50`, `:91-92`, `:154-155`, `:206-207`, `:254-255`; consumed at
`preliminary.py:198-230`. Five bare handlers return benign defaults; the caller's `if _reg_data:`
guard skips the whole registry block, `ctgov_outcomes` keeps its placeholder, and D5 is still
judged and still scored. A ten-second network hiccup silently removes the pre-registration
evidence from the one domain that reasons about pre-registration.

**H20. Running `pytest` makes live, authenticated, billable API calls.** `tests/test_graph.py`.
The autouse fixture at `:131-146` patches `call_json_contract_llm` in only 4 of the 7 modules that
import it, and the tests patch `nodes.common.build_provider` but not `llm_contracts.build_provider`.
So `nodes/domain_classifier.py:74` falls through to a real POST to
`https://openrouter.ai/api/v1/chat/completions` carrying the `.env` key. **4 of 512 tests currently
fail**, and they fail with HTTP 404 — the default model `openai/gpt-oss-120b:free` appears retired
— which is the only reason this is not costing money today. Fix the model name without fixing the
mocks and `pytest` starts billing.

**H21. Supplement domain-tagging inspects only the first 300 characters of a segment.**
`ingestion/supplement_segments.py:348-354`. A protocol page whose analysis-population statement
sits at character 2,000 under a generic heading gets no D2 tag and is excluded from the D2 index
entirely. A pure recall hole in the deterministic half.

**H22. Every packet source is cut to 700 characters before it reaches the legacy domain prompt.**
`evidence_packets.py:104-141`, cut at `:122`. A source allowed 8,000 characters by
`MAX_SOURCE_CHARS` is rendered into `rag_text` as its first 700. On the fallback path (H11) a
decisive sentence at character 900 is present in the packet, present in the quote-verification
haystack, and absent from the prompt.

**H23. The benchmark launcher was never version controlled.** `.gitignore:56` ignores `outputs/*`,
and all four watchdog scripts lived in `outputs/benchmark/logs/`. The tooling behind every number
this project has produced was unreviewable, undiffable, and would die with the disk — which is why
four near-duplicate copies of it exist. *Fixed tonight as a side effect of the workspace cleanup:
`scripts/run_benchmark.ps1`, commit `14d29ec`.*

### Medium

**M1. Retrieval confidence rises when the packet loses evidence.**
`evidence_packet_grading.py:77-91`. Confidence saturates at 4 matched terms and 2 sources, so three
short term-diverse snippets outscore three long sections containing far more evidence. Measured:
confidence went **0.475 → 0.825** while the packet lost 84% of its characters. Since confidence
below 0.35 triggers `retrieval_repair`, the metric that gates evidence quality moves the wrong way.

**M2. bm25s top-k has no deterministic tie-break.** `supplement_retrieval.py:119-137` into
`bm25s/selection.py`. `np.argpartition` plus a non-stable `argsort` means ties break by numpy's
internal pivot behavior, a function of the whole score array. Measured with bm25s 0.3.9 / numpy
2.4.4: appending *irrelevant* filler documents changes which tied documents survive the cut, not
just their order. Nuance worth keeping straight: this is *reproducible* run-to-run on a fixed
corpus, so it is not a source of today's variance. It is fragility across corpus edits, numpy
upgrades and platforms, and it means "top-5" is not a well-defined set.

**M3. Everything `enforce_prompt_budget` drops is reported only to a logger that is never
configured.** `llm_contracts.py:31-36`; both call sites discard the returned count
(`llm_contracts.py:77`, `nodes/common.py:122`). No `logging.basicConfig` exists in the repo, so it
reaches stderr only through Python's last-resort handler and appears in no artifact. A run that
lost 40,000 characters of evidence is indistinguishable from a clean one. ADR-0006 promised
"logging every drop (no silent truncation)".

**M4. `cap_section` keeps three overlapping keyword windows and hard-cuts mid-sentence.**
`ingestion/evidence.py:177-220`, plus a hard `if len(windows) >= 8: break` at `:270`. A section over
10,000 characters is reduced to at most three overlapping 2,000-character windows covering under
~6k unique characters. The inline truncation marker never says how much was lost.

**M5. `reference_ambiguity` absorbs the reference's own algorithm violations into a mismatch
bucket.** `benchmark.py:1311-1319`. It fires on exactly the 17 self-contradictory rows from C1 — a
category that excuses disagreement with a broken gold standard instead of flagging it. It also
misfires: `postmerge_k3_run1` produced empty judgments for all 8 trials and its report blamed
`reference_ambiguity` for 10 mismatches.

**M6. An empty pipeline output scores as 100% agreement when a reference cell is blank.**
`benchmark.py:48-59`, `:1056-1066`. `_normalize_judgment(None)` and `("")` both return `""`, and
comparison is string equality. Latent today because no CSV cell is blank; live the moment anyone
adds a trial row with an unfilled domain, and that trial then scores 100% for free.

**M7. `_normalize_judgment` passes unrecognized labels through silently.** `benchmark.py:51-59`
maps only `{l, low, s, some concerns, h, high}`. `'Low risk'`, `'low_risk'`, `'some-concerns'` and
`'HIGH RISK'` all pass through unchanged. The direction is safe today (unmapped strings become
mismatches) but it is a silent-failure surface.

**M8. Unstable k-votes are counted as agreement.** `self_consistency.py:148-182`, `:112-145`. When
no label reaches the threshold, the tie breaks toward the most cautious label with
`stable=False` — and `summarize_domain_votes` still counts it toward `agreements`. The headline
rate mixes confident and coin-flip cells. *To be clear, the tie-break direction is correct: it
breaks toward High, away from Low, and the aggregation is deterministic and unbiased.* **But
k-voting cannot surface any of C3-C10, because every flip is a deterministic string match and
therefore fires identically in all k runs.** k measures the model's sampling variance only.

**M9. The markdown report erases the marker that distinguishes a fallback answer from a real one.**
`nodes/reporter.py:47-51`. `_clean_cell` detects the `"Auto-set:"` prefix and replaces the whole
cell with `"No relevant text found"`, so a fallback-derived NI and a genuine one render
identically. `_domain_table` also defaults missing SQs to NI and missing judgments to "Not
assessed", so a domain that never ran renders as a complete-looking table.

**M10. The k-vote scorer reads run directories by name with no check they came from this run or
this commit.** `kvote_score.py:69-79`. No timestamp, commit, or manifest check. A prefix reused
after a partial failure silently mixes judgments from two code states into one vote, and `OK`
means only "the directory exists". *Our branch.*

**M11. Config is frozen at import while a misspelled variable name silently selects the free
model.** `config.py:8`, `:22-31`, `:43-53`. `os.getenv("ROB2_MODEL", "openai/gpt-oss-120b:free")`
means a typo runs the free tier with no warning, and nothing in the output distinguishes which
variant produced a result. `.env` currently has both overrides commented out, with a note that a
previous Anthropic override "was silently hijacking every standard benchmark run". An invalid
provider fails lazily at the first LLM call, after ingestion has already run.

**M12. Contract terms are matched literally with no stemming, and several carry only the American
spelling.** `nodes/evidence_contracts.py:142-155`; bm25s is configured with `stemmer=None`. SQ 2.6
and 2.7 list `"randomized"` but not `"randomised"`, while SQ 3.1 carries both — so the omission
reads as an oversight. GETUG-AFU-15 is a Lancet Oncology trial and uses the British spelling.

**M13. No seed and no provider pinning on the OpenRouter request.** `providers/openrouter.py:111-120`.
The body carries only model, temperature, max_tokens and messages. OpenRouter routes across
multiple hosting providers with different numerics, so two runs can hit different backends.
ADR-0008 attributes remaining variance to "the reasoning model's inherent non-determinism";
provider routing is a separate and partly controllable contributor that has not been ruled out.
*Confidence medium — inferred from OpenRouter's documented routing, not from this repo's traces.*

**M14. A repair-path parse failure returns NI answers on the legacy caller.**
`nodes/common.py:132-167`. Dormant today because `evidence_family_mining` is the only caller and
passes no `parse_fn`; live the moment any node passes a parser. It does two things right that the
contract path does not: marks the response non-cacheable and records `suspected_parse_failures` —
which no metric reads.

**M15. LLM evidence extraction failure degrades to keyword extraction, recorded only as a warning
string.** `ingestion/assessment.py:213-238`, `ingestion/evidence.py:108-113`. `evidence["warnings"]`
is not in `JSON_OUTPUT_KEYS`, so neither degradation appears in any scored artifact.

### Low

**L1. `required_evidence` labels are injected into the BM25 query but can never match text.**
`evidence_source_selection.py:157-162`. Snake_case labels like `"analysis_population"` never appear
in trial prose; they add a dead token to every query and inflate the confidence denominator.

**L2. `_estimate_tokens` is dead.** `evidence_packets.py:53-56`, referenced only by a test. The
packet-level token budget ADR-0006 specified was never wired in, which is why the only defense
against overflow is the blind tail slice in C16.

**L3. `extract_censoring_context` is dead**, and the structural fallback can never recover a table.
`ingestion/evidence.py:307-333`; `ingestion/assessment.py:241-247` hardcodes `self.blocks = []`, so
the table-harvesting loop at `evidence.py:165-173` is a permanent no-op. When LLM extraction fails,
the structural fallback recovers no baseline table and no CONSORT table.

**L4. JSON-contract calls bypass the cache entirely.** `llm_contracts.py:47-183` never touches
`read_cache`/`write_cache`. Every call that matters is uncached; `ROB2_USE_CACHE=1` buys nothing on
the paths that drive the judgment.

**L5. D1's judge has no row for a non-random allocation sequence** and falls through to Some
concerns. `judges/domain1.py:62-67`. The repo's own reference table has the same gap, so this is
*not* a deviation from the cited source — noted only because it is a surprising outcome.

**L6. `.env` is clean.** `.gitignore:166` covers it, it is untracked, and `git log --all -- .env`
is empty, so no key has ever entered history. Recorded as a verification result, not a defect. One
residual risk: `openrouter.py:139` embeds the full HTTP error body into an exception that
`benchmark.py:1505` writes verbatim into `benchmark_results.json`.

---

## What is not broken

Worth stating plainly, because it constrains where fixes should go.

- **The deterministic judges are correct.** D2 Version A parts 1 and 2 and the combination rule,
  D2 Version B, D3, D4 including all four 4.2=NI rows, and D5 all reproduce the published Sterne
  2019 tables exactly. The skip/NA branching is correct, including `sq_control.py:42` where 2.4=NI
  correctly does not skip 2.5. The only overall-judgment deviation is the opt-in policy in C15.
- **The ADR-0008 retrieval is genuinely deterministic.** Repeated calls on the same index, a fresh
  index, and interleaved different queries all returned byte-identical results.
- **k-vote aggregation is unbiased and deterministic.** Domain-judgment level, threshold over the
  intended k so failed runs make consensus harder rather than being dropped, ties broken toward
  High. Its limitation (M8) is what it cannot see, not what it does.
- **The bm25s path has no unseeded randomness**, no `os.walk`/`glob` ordering leak, and no
  set/dict iteration reaching output order.

---

## Coverage and method

Six agents, each given a different lens so their findings would be mostly disjoint rather than
three independent rediscoveries of the loudest bug. Each was instructed to report file:line,
severity, attribution and confidence, to prove claims by reading rather than inferring, and to
mark anything unproven as low confidence.

| Lens | Findings returned |
| --- | --- |
| Evidence path (PDF to classifier) | 20 |
| Scoring and benchmark code | 12 plus verified arithmetic |
| Judging layer and auto-flips | 15 plus the full flip table |
| Plumbing and failure modes | 20 |
| Dead code and needless complexity | see below |
| Reference-set expansion feasibility | see below |

I independently re-verified the most consequential claims rather than taking them on trust:

- **C1**, the 17-of-28 reference contradiction — recomputed from the CSVs (OS 6, PFS 6, AE 5).
- **C6**, the hardcoded benchmark phrases — grepped, exact, and the OCR artifact appears twice
  (`sq_control.py:314` and `:321`), not once.
- **C11**, `schema_failures` — read in 19 places in `benchmark.py`, written in **zero** places
  anywhere in the pipeline. `parser_metrics.schema_validation_failures` is structurally always 0,
  so the "Schema validation failures: 0" line in every engineering report is not a measurement.
- **C13**, the shrinking denominator — counted across every run on disk: 10 runs affected.
- **C17**, the ascending BM25 sort — read both the sort key and the score producer.
- **H7**, the wasted mining calls — `selected_evidence_facts` and `evidence_store` appear only in
  the state declaration, the output-key list, their own producer, and the `facts.jsonl` writer.
- **H20**, live API calls under `pytest` — ran the suite (508 pass, 4 fail) and traced the failure
  to a real outbound POST.

**Known gaps.** Nothing here was confirmed by running the pipeline, because that costs money and
the measurement is broken until C1/C2/C20 are resolved. Claims about how *often* a path fires
(C16, H11, H21) are mechanism-verified but frequency-unverified. There are no PFS or AE runs on
disk at all, so D4 — the only column with real cross-outcome variance and the only one where
always-Low loses — has never been benchmarked.
