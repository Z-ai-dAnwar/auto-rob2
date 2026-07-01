# ADR-0007: Raise The LLM Output-Token Budget Above The Truncation Ceiling

Date: 2026-07-01

## Status

Proposed

## Context

The k=2 baseline on the paid `openai/gpt-oss-120b` model (banked in
`outputs/benchmark/kvote_fix1` and `kvote_fix2`) showed a large, structural loss
of accuracy and run-to-run consistency in domains D3, D4, and D5. Tracing the
recorded calls (`*_trace.json` `llm_calls`) pinpoints a single cause: the output
budget `max_tokens=2000` truncates the model mid-answer.

`gpt-oss-120b` is a reasoning model, so its `completion_tokens` count (recorded
as `output_tokens`) covers reasoning plus the JSON answer. On the larger-JSON
domains the model spends its whole 2,000-token budget and is cut off before the
JSON closes.

The evidence is a clean partition, not a correlation. Among the JSON-contract
calls (the classifier and evidence-extraction calls that run through the schema
parser, so they carry a `parse_status`):

- Across both passes, **113 of 113** parse-failed contract calls sit at exactly
  2,000 output tokens. **0 of 241** successful (parsed) contract calls reach
  2,000; the largest successful call is 4,506 tokens, median ~1,034.
- Scoped wider, **204 of 579** non-cache calls sit at exactly 2,000: the 113
  contract parse failures plus 91 evidence-family-mining calls that do not run
  through the contract parser (so their `parse_status` is `None`) and are
  therefore not counted as parse failures. A raw scan that ignores
  `parse_status` sees 204-at-2,000 and must split by it to reproduce the
  partition.
- The single most-truncated node is `paper_evidence_extraction` (35 failures).
  This node runs upstream of every domain, so its truncation degrades all
  domains, not only the three where the loss surfaces in the score.
- Domain classifiers fail next most often (`domain4_sq_json`, `domain3_sq_json`,
  `domain5_sq_json`, `domain2_conditional_json`).
- Which calls truncate changes run to run, because reasoning-token count varies
  per run: pass 1 truncated d3=7 / d4=9 / d5=10 classifier calls, pass 2 truncated
  d3=10 / d4=14 / d5=6. This is the mechanism behind the D3/D4/D5 instability.
- Truncation also produces empty output, not just malformed JSON: **58 of the
  204** at-cap calls return zero visible content (the budget is spent entirely on
  reasoning, which reached 15,859 characters, ~4,500 tokens, in one call). 11 of
  those are evidence-family-mining calls, including `_repair` calls that re-hit
  the same 2,000 cap. When both a mining call and its repair truncate, the family
  is recorded as a failed claim (`evidence_store.py:523`), so the mined evidence
  is lost before any domain sees it. This loss does not surface as a
  `parse_status` failure, so it is easy to undercount.

The downstream damage: a parse failure routes through
`call_json_contract_llm` (`rob2_pipeline/llm_contracts.py`) to
`_classifier_fallback` (`rob2_pipeline/nodes/domain_classifier.py:329`), which
sets every signaling question to `"NI"` (no information) with the quote
"No relevant text found". The deterministic judge then routes NI-heavy domains to
"High" (for D3, via `d3:missingness-likely-dependent-on-true-value`). The retry
inside `call_json_contract_llm` cannot help, because a second attempt re-hits the
same 2,000 ceiling. So a purely mechanical output cap is silently converted into
a wrong bias judgment.

The `max_tokens` default lives in one place and applies to every call:
`rob2_pipeline/config.py` (`LLMConfig.max_tokens` and the `ROB2_MAX_TOKENS`
default read by `get_llm_config()`), passed through `build_provider()` into the
provider request body (`rob2_pipeline/providers/openrouter.py:_post_chat_completion`).
The benchmark environment does not set `ROB2_MAX_TOKENS`, so the 2,000 default is
what actually ran. `config.py` is unchanged upstream, so this is collision-free.

## Decision

Raise the default output budget from 2,000 to 8,000 tokens, in the one config
surface that feeds every call:

- `LLMConfig.max_tokens` default: 2000 -> 8000.
- `get_llm_config()` `ROB2_MAX_TOKENS` default: "2000" -> "8000".
- `OpenRouterProvider.__init__` `max_tokens` default: 2000 -> 8000, so a caller
  who constructs the provider directly gets the same safe floor.

8,000 is ~1.8x the largest observed successful output (4,506). The headroom is
deliberate: calls truncated at the old 2,000 cap were cut off, so their true
required length was never observed and may exceed 4,506; and reasoning-token
count varies run to run. The `ROB2_MAX_TOKENS` env knob still overrides the
default, so ops can tune the budget without a code change.

This is an LLM-facing infrastructure change (call configuration). It does not
touch the deterministic judges, the skip/NA logic, or the published RoB 2
(Sterne 2019) algorithm.

### Alternatives considered

- **Cap reasoning tokens** via OpenRouter's `reasoning` parameter, to stop the
  reasoning model from spending the whole budget before it emits JSON. This is
  the right follow-up if empty-output cases persist after the bump (a call that
  spends all 8,000 tokens on reasoning and emits nothing). Deferred: do the
  simple, low-risk bump first and measure, rather than over-building before the
  data says it is needed.
- **Per-node output budgets** (small budget for short domains, large for D4/D5).
  More surface area and more ways to misconfigure, for no measured benefit over a
  single safe ceiling. Rejected as premature.
- **Raise to a smaller value (e.g. 5,000).** Clears the observed 4,506 max but
  leaves little slack for the unobserved length of the truncated calls and for
  reasoning-token variance. 8,000 buys that slack while staying within the
  context window (see Consequences).

## Consequences

- The truncation-to-NI-to-High path stops firing for any call whose real output
  is under 8,000 tokens, which is every successful call observed. Expect the
  D3/D4/D5 fallback rate to drop sharply and the run-to-run variance to shrink,
  since the variance was driven by which calls happened to cross 2,000.
- The benefit reaches beyond D3/D4/D5, because the worst-hit node
  (`paper_evidence_extraction`) is shared upstream input to all domains, and 11
  truncated evidence-family-mining calls were silently losing mined facts before
  any domain saw them. Watch D1/D2 and the held-out trials for no-regression
  rather than assuming they are untouched; the gain may be broader than the
  classifier fallback rate alone shows.
- Interplay with ADR-0006: that ADR set `ROB2_PROMPT_TOKEN_BUDGET` (default
  115,000) as the input cap under the model's 131,072-token context window,
  sized assuming a "~2,000-token output". Raising output to 8,000 keeps the
  worst-case total within the window (115,000 + 8,000 = 123,000 < 131,072), with
  ~8,000 tokens of slack for the system prompt and schema overhead. The margin is
  smaller than before but still positive; if the output budget is ever raised
  further, `ROB2_PROMPT_TOKEN_BUDGET` must be lowered to match.
- Cost per call rises only when a call actually needs the extra tokens (billing
  is per token emitted, and `max_tokens` is a ceiling, not a target), so short
  D1/D2 calls are largely unaffected.
- The real per-call cost is latency, not dollars. The affected D3/D4/D5 and
  evidence calls already run 100-207 seconds today at ~59 tokens/second, so a
  call that now generates closer to 8,000 tokens can take ~135 seconds. This is
  not a new hard failure mode: `request_timeout` is 60 seconds but is applied
  per socket read, not as a total deadline, and 4,506-token calls already
  complete today past 200 seconds. Still, the k=5 gate should watch total wall
  clock and confirm no new timeout failures appear.
- Residual risk, now observed rather than hypothetical: a call can spend the
  whole budget on reasoning and emit nothing (58 such empty-output calls at the
  old 2,000 cap; reasoning alone reached ~4,500 tokens). 8,000 clears every
  output length observed on a successful call, but because truncated calls were
  cut off we cannot rule out that the very hardest calls still exhaust 8,000. If
  empty-output-at-8,000 appears in the post-fix trace, apply the reasoning-cap
  follow-up above.

## Implementation notes

- Change confined to `rob2_pipeline/config.py` (two defaults) and the three
  provider constructors (`openrouter.py`, `openai.py`, `anthropic.py`, one
  default each, kept in step so a directly-constructed provider gets the same
  safe floor). The benchmark path never relies on the constructor defaults;
  `build_provider()` always passes the config value explicitly. No judge, no
  skip/NA, no algorithm code touched.
- TDD guard: `tests/test_llm_config_headroom.py` asserts both the dataclass
  default and the `get_llm_config()` env-default path clear a floor derived from
  the observed 4,506-token max (with margin), and that the `ROB2_MAX_TOKENS`
  override still wins. The guard fails at the old 2,000 default, so it locks in
  the property that a future edit cannot silently reintroduce the truncation.
- Verification gate: run a clean k=5 benchmark on the fixed code under a new
  prefix (baseline `kvote_fix1/2` preserved). The gate must compare the raw trace
  counts before vs after, not just the score: (a) at-cap calls (output_tokens
  equal to the budget) should fall from 204 toward zero; (b) empty-output calls
  should fall from 58 toward zero; (c) evidence-family-mining failed claims from
  truncation should drop. Acceptance: the D3/D4/D5 fallback rate drops materially,
  D1/D2/D4 and the held-out GETUG-AFU-15 / SWOG-1216 do not regress, and any
  remaining empty-output-at-8,000 calls are counted (a nonzero count means the
  fix is partial, not complete, and triggers the reasoning-cap follow-up rather
  than being read as success).
