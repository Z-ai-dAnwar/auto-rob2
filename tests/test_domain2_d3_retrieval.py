"""SQ 2.6 must surface the analysis-population (ITT/analysed-as-randomized) sentence.

Regression guard for the D2 SQ 2.6 retrieval-targeting gap.

The ITT sentence is already retrieved into the d2 candidate pool, but it can
lose the top-3 packet selection to other Domain 2 chunks that match more of
SQ 2.6's existing vocabulary (intention, itt, modified, per-protocol, as treated,
randomized). With no analysis-population statement in its packet, the classifier
returns "No relevant text found" even for trials that clearly state ITT analysis.

The fix adds coverage_groups=(ANALYSIS_POPULATION_COVERAGE_TERMS,) to the 2.6
EvidenceContract, mirroring the mechanism already used for D5 SQ 5.3. This
reserves one packet slot for a source whose text contains one of the
high-precision analysis-population terms, so higher-ranked generic D2 chunks
cannot crowd it out.

Fixture design rationale
------------------------
SQ 2.6 contract terms: intention, itt, modified, per-protocol, as treated, randomized
ANALYSIS_POPULATION_COVERAGE_TERMS: intention-to-treat, intention to treat, itt,
  analysed as randomi, analyzed as randomi, all randomi, per-protocol, as-treated,
  as treated

ITT_CHUNK matches only 1 contract term ("intention" from "intention-to-treat").
Three noise chunks are crafted to match 3 contract terms each ("intention",
"modified", "randomized") WITHOUT containing any coverage term -- so the noise
chunks outrank ITT_CHUNK by term count but cannot fill the coverage slot. The
coverage slot must therefore be filled by ITT_CHUNK.
"""

from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.evidence_packets import build_evidence_packets


def _state_with_chunks(
    domain: str, chunks: list[dict], outcome: str = "Overall Survival"
) -> dict:
    evidence = empty_paper_evidence("test")
    return {
        "outcome": outcome,
        "evidence": evidence,
        "rag_chunk_metadata": {
            "d1": [],
            "d2": [],
            "d3": [],
            "d4": [],
            "d5": [],
            domain: chunks,
        },
        "retrieval_grades": {},
    }


# The load-bearing ITT sentence that SQ 2.6 must see in its packet.
# Contract term matches: "intention" (1 term -- "randomised" != "randomized").
# Coverage term match: "intention-to-treat" (triggers the reserved slot).
ITT_CHUNK = {
    "text": (
        "All randomised participants were analysed in the group to "
        "which they were assigned (intention-to-treat)."
    ),
    "page_numbers": [7],
    "section": "Statistical Analysis",
    "score": 0.30,
}

# Three distractor chunks that each outrank ITT_CHUNK on contract term count
# (3 matches vs 1) but contain NO coverage terms, so the coverage slot cannot
# be filled by any of them.
#
# Safe contract terms (not coverage terms): "intention" (standalone, not
# "intention-to-treat"/"intention to treat"), "modified", "randomized".
NOISE_A = {
    # Contract matches: "intention", "modified", "randomized" (3 terms)
    # Coverage matches: none ("intention" alone is not a coverage term)
    "text": (
        "The original intention was to report a modified efficacy analysis using "
        "the randomized set with at least one dose of study drug."
    ),
    "page_numbers": [2],
    "section": "Statistical Analysis",
    "score": 0.31,
}
NOISE_B = {
    # Contract matches: "intention", "modified", "randomized" (3 terms)
    # Coverage matches: none
    "text": (
        "It was the investigators' intention to apply a modified covariate "
        "adjustment to the randomized population at interim review."
    ),
    "page_numbers": [3],
    "section": "Statistical Analysis",
    "score": 0.32,
}
NOISE_C = {
    # Contract matches: "intention", "modified", "randomized" (3 terms)
    # Coverage matches: none
    "text": (
        "The intention was to conduct a modified frequentist analysis of the "
        "randomized participants using ANCOVA."
    ),
    "page_numbers": [4],
    "section": "Statistical Analysis",
    "score": 0.33,
}


def test_sq26_packet_keeps_itt_sentence_against_higher_ranked_chunks():
    """Without coverage_groups, NOISE_A/B/C each score 3 matched contract terms
    and crowd ITT_CHUNK (1 term) out of the top-3 packet. With coverage_groups,
    the analysis-population coverage slot reserves a place for the ITT chunk
    because none of the noise chunks contain a coverage term."""
    state = _state_with_chunks("d2", [NOISE_A, NOISE_B, NOISE_C, ITT_CHUNK])
    packet = build_evidence_packets(state)["evidence_packets"]["2.6"]
    selected = " ".join(s.get("text", "") for s in packet["sources"])
    assert "intention-to-treat" in selected.lower() or "analysed in the group" in selected.lower(), (
        "SQ 2.6 must select the intention-to-treat / analysed-as-randomized "
        "sentence into its packet even when higher-ranked generic D2 chunks are "
        "present. Without a reserved coverage slot the ITT sentence is crowded "
        "out and the classifier returns 'No relevant text found'."
    )
