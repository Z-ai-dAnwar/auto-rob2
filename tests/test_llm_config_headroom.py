"""Guard against regressing the LLM output-token budget below what real calls need.

Background: with max_tokens=2000, every parse-failed JSON-contract call in the
k=2 baseline (kvote_fix1/kvote_fix2) pinned at exactly 2000 output tokens (113/113),
while no successful contract call ever reached 2000 (max successful = 4506). (Scoped
wider, 204 of 579 non-cache calls hit 2000, the extra 91 being evidence-mining calls
that bypass the contract parser.) The 2000 ceiling truncated the reasoning model
mid-output, the JSON failed to parse, the pipeline fell back to all-"NI", and the
deterministic judge routed those NI-heavy domains to High.

These tests lock in the property that the default budget clears the largest observed
real output with headroom, so a future edit cannot silently reintroduce the truncation.
"""

from rob2_pipeline.config import LLMConfig, get_llm_config

# Largest output_tokens seen on a SUCCESSFUL (parsed) call across the k=2 baseline scan.
OBSERVED_MAX_SUCCESSFUL_OUTPUT_TOKENS = 4506

# The default must clear the observed max with margin. The model is a reasoning model,
# so output_tokens includes reasoning tokens, which vary run to run; and calls truncated
# at the old 2000 cap were cut off, so their true length was never observed and may exceed
# 4506. Require ~33% headroom over the observed max as a safety floor.
MIN_SAFE_MAX_TOKENS = int(OBSERVED_MAX_SUCCESSFUL_OUTPUT_TOKENS * 4 / 3)  # 6008


def test_dataclass_default_max_tokens_has_headroom_over_observed_max():
    assert LLMConfig().max_tokens >= MIN_SAFE_MAX_TOKENS


def test_env_default_max_tokens_has_headroom_over_observed_max(monkeypatch):
    # The benchmark environment does not set ROB2_MAX_TOKENS, so the get_llm_config()
    # default is what actually runs. Verify that path clears the floor too.
    monkeypatch.delenv("ROB2_MAX_TOKENS", raising=False)
    assert get_llm_config().max_tokens >= MIN_SAFE_MAX_TOKENS


def test_explicit_env_override_still_wins(monkeypatch):
    # Behavior preservation: the env knob must still override the default, so ops can
    # tune the budget without a code change.
    monkeypatch.setenv("ROB2_MAX_TOKENS", "12345")
    assert get_llm_config().max_tokens == 12345
