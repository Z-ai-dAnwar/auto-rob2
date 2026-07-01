"""D3 SQ 3.1 must retrieve the missing-outcome-data denominator.

The vital-status / participant-flow denominator (how many of the randomized
participants had known outcome status) lives in the ClinicalTrials.gov
participant-flow, which enters the packet as a document_role="registry" source.
Ranking demotes "registry" for d3 and 3.1 has no coverage group, so the flow
source loses the top-3 contest to generic primary sections and never reaches the
model. This test pins that the denominator source must be selected into the 3.1
packet.
"""

from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_packet_for_contract


def _section(text: str) -> dict:
    return {"text": text, "tables": [], "source": "primary"}


def _d3_state_with_participant_flow() -> dict:
    # Three primary (role_rank 0) fallback sections that match several 3.1 terms
    # and so outrank the registry participant-flow on the current key, plus the
    # CT.gov participant-flow that actually carries the vital-status denominator.
    return {
        "outcome": "overall survival",
        "outcome_type": "vital-status",
        "pdf_path": "trial.pdf",
        "supplement_indexes": {},
        "registration_number": "NCT00104715",
        "ctgov_flow": (
            "Participant flow:\n"
            "  STARTED: Drug A plus usual care 601, Usual care alone 602\n"
            "  COMPLETED: 597, 599\n"
            "  Lost to Follow-up: 4, 3\n"
            "1053 of 1060 randomized participants had known vital status."
        ),
        # Each primary section matches >=2 of the 3.1 terms so it outranks the
        # role-demoted registry source, and none contains the participant-flow /
        # vital-status coverage terms (so only the registry source can satisfy
        # the coverage group once it exists).
        "evidence": {
            "d3_missing_data": _section(
                "Missing outcome data were handled with multiple imputation; the "
                "analysed population followed the randomised assignment."
            ),
            "consort_flow": _section(
                "Figure 1 shows the profile: patients were randomised and "
                "analysed by intention to treat."
            ),
            "results": _section(
                "Outcome data for overall survival were analysed (HR 0.61)."
            ),
        },
    }


def test_3_1_packet_includes_participant_flow_denominator_source():
    state = _d3_state_with_participant_flow()

    packet = build_packet_for_contract(state, CONTRACTS["3.1"])

    roles = [source.get("document_role") for source in packet["sources"]]
    joined = " ".join(source.get("text", "") for source in packet["sources"]).casefold()
    assert "registry" in roles, f"participant-flow source dropped; roles={roles}"
    assert "vital status" in joined, "denominator text did not reach the packet"


def _d3_state_with_competing_flow_mention() -> dict:
    # The LATITUDE / TITAN failure mode: a non-registry source also mentions a
    # coverage term ("lost to follow-up") and, because it matches more of the
    # generic 3.1 terms and is not demoted by the d3 role hierarchy, it outranks
    # the registry participant-flow AND satisfies the coverage group first. The
    # text-only coverage slot therefore goes to the imputation prose, and the
    # authoritative registry flow (the only source with the randomized
    # denominator + vital-status counts) is crowded out of the top-3.
    return {
        "outcome": "overall survival",
        "outcome_type": "vital-status",
        "pdf_path": "trial.pdf",
        "supplement_indexes": {},
        "registration_number": "NCT00104715",
        "ctgov_flow": (
            "Participant flow:\n"
            "  STARTED: Drug A plus usual care 601, Usual care alone 602\n"
            "  COMPLETED: 597, 599\n"
            "  Lost to Follow-up: 4, 3\n"
            "1053 of 1060 randomized participants had known vital status."
        ),
        "evidence": {
            # A primary (role_rank 0) section that also mentions the coverage
            # term "lost to follow-up" and matches several 3.1 terms, so it both
            # outranks and pre-empts the registry flow under the current logic.
            "d3_missing_data": _section(
                "Patients lost to follow-up were rare; missing outcome data were "
                "analysed by intention to treat for the randomised population."
            ),
            "consort_flow": _section(
                "Figure 1 shows the profile: patients were randomised and "
                "analysed by intention to treat."
            ),
            "results": _section(
                "Outcome data for overall survival were analysed (HR 0.61)."
            ),
        },
    }


def test_3_1_registry_flow_wins_slot_over_competing_flow_mention():
    state = _d3_state_with_competing_flow_mention()

    packet = build_packet_for_contract(state, CONTRACTS["3.1"])

    roles = [source.get("document_role") for source in packet["sources"]]
    joined = " ".join(source.get("text", "") for source in packet["sources"]).casefold()
    assert "registry" in roles, (
        f"registry participant-flow crowded out by a competing 'lost to "
        f"follow-up' mention; roles={roles}"
    )
    assert "vital status" in joined, "denominator text did not reach the packet"
