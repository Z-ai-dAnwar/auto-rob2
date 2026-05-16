from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.trial_facts import extract_trial_facts


def test_extract_trial_facts_collects_trial_level_evidence():
    evidence = empty_paper_evidence()
    evidence["d1_randomization"]["text"] = (
        "Participants were randomized centrally. Allocation was concealed by a web system."
    )
    evidence["d2_blinding"]["text"] = "The trial was open-label and participants were aware of treatment."
    evidence["methods"]["text"] = "The primary analysis used the intention-to-treat population."
    evidence["d5_registration"]["text"] = "The protocol was amended before unblinded analyses."

    facts = extract_trial_facts({"evidence": evidence})

    assert "randomized" in facts["randomization"]
    assert "concealed" in facts["allocation_concealment"]
    assert "open-label" in facts["masking"]
    assert "amended" in facts["protocol_amendments"]
    assert "intention-to-treat" in facts["analysis_populations"]
