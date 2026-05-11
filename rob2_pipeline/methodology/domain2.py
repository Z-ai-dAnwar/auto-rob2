from rob2_pipeline.methodology.types import Citation, DomainMethodology, ResponseRule, RuleCard

SUPP = "Sterne 2019 supplement"
BMJ = "Sterne 2019 BMJ"

_AWARENESS_21 = RuleCard(
    "2.1",
    "Were participants aware of their assigned intervention during the trial?",
    {
        "Y": ResponseRule("Participants were explicitly aware, blinding was impossible, or assignment-specific effects revealed allocation."),
        "PY": ResponseRule("Design or side effects probably allowed participants to infer assignment."),
        "PN": ResponseRule("Blinding or similarity of interventions makes awareness unlikely, but not fully verified."),
        "N": ResponseRule("Participants were explicitly and successfully blinded."),
        "NI": ResponseRule("Participant awareness cannot be inferred from available information."),
    },
    [Citation(SUPP, "p.6"), Citation(BMJ, "p.4")],
)

_AWARENESS_22 = RuleCard(
    "2.2",
    "Were carers and people delivering interventions aware of participants' assigned intervention?",
    {
        "Y": ResponseRule("Carers/deliverers were explicitly aware, blinding was impossible, allocation was unconcealed to care staff, or effects revealed assignment."),
        "PY": ResponseRule("Design or side effects probably revealed assignment to carers or deliverers."),
        "PN": ResponseRule("Blinding or intervention similarity makes awareness unlikely, but not fully verified."),
        "N": ResponseRule("Carers/deliverers were explicitly and successfully blinded."),
        "NI": ResponseRule("Awareness of carers/deliverers cannot be inferred from available information."),
    },
    [Citation(SUPP, "p.6"), Citation(BMJ, "p.4")],
)

DOMAIN2_ASSIGNMENT_METHODOLOGY = DomainMethodology(
    domain_id="D2_ASSIGNMENT",
    title="Bias due to deviations from intended interventions: effect of assignment",
    principles=["Open-label trials are not automatically high risk; bias depends on trial-context deviations and analysis appropriateness."],
    rule_cards={
        "2.1": _AWARENESS_21,
        "2.2": _AWARENESS_22,
        "2.3": RuleCard(
            "2.3",
            "Were there deviations from intended intervention that arose because of the trial context?",
            {
                "Y": ResponseRule("Evidence shows trial context caused protocol-inconsistent deviations or non-protocol interventions."),
                "PY": ResponseRule("Strong reason suggests recruitment, engagement, unblinding, or trial personnel caused protocol-inconsistent changes."),
                "PN": ResponseRule("Changes appear consistent with what could occur outside the trial context."),
                "N": ResponseRule("Changes were protocol-consistent, normal clinical management, or explicitly unrelated to trial context."),
                "NI": ResponseRule("Deviations are described but their trial-context origin cannot be judged reasonably."),
            },
            [Citation(SUPP, "p.7"), Citation(BMJ, "p.3")],
        ),
        "2.4": RuleCard("2.4", "Were these deviations likely to have affected the outcome?", {"Y": ResponseRule("Deviations clearly affected or plausibly had large effect on the outcome."), "PY": ResponseRule("Substantial deviations probably could affect the outcome."), "PN": ResponseRule("Deviations were unlikely to materially affect the outcome."), "N": ResponseRule("Deviations could not affect the outcome."), "NI": ResponseRule("Outcome impact cannot be determined.")}, [Citation(SUPP, "p.7")], applicability="Only if 2.3 is Y/PY/NI."),
        "2.5": RuleCard("2.5", "Were these deviations balanced between groups?", {"Y": ResponseRule("Deviations were clearly balanced."), "PY": ResponseRule("Available data suggest balance."), "PN": ResponseRule("Available data suggest imbalance but not conclusively."), "N": ResponseRule("Deviations were clearly unbalanced."), "NI": ResponseRule("Distribution between groups is not reported.")}, [Citation(SUPP, "p.7")], applicability="Only if deviations likely affected the outcome."),
        "2.6": RuleCard("2.6", "Was an appropriate analysis used to estimate the effect of assignment?", {"Y": ResponseRule("ITT or appropriate mITT analysis was used."), "PY": ResponseRule("Analysis appears consistent with assignment effect despite limited detail."), "PN": ResponseRule("Analysis probably deviates from assignment principles."), "N": ResponseRule("Naive per-protocol, as-treated, treatment-received, or inappropriate post-randomization exclusions were used."), "NI": ResponseRule("Analysis approach is not reported sufficiently.")}, [Citation(SUPP, "p.8"), Citation(BMJ, "p.3")]),
        "2.7": RuleCard("2.7", "Was there potential for substantial impact from failure to analyse participants as randomized?", {"Y": ResponseRule("Exclusions or wrong-group analyses could substantially affect the result."), "PY": ResponseRule("Moderate exclusions or misclassification probably could matter."), "PN": ResponseRule("Few affected participants or unlikely material impact."), "N": ResponseRule("No meaningful failure or clearly no substantial impact."), "NI": ResponseRule("Insufficient information about exclusions or wrong-group analysis.")}, [Citation(SUPP, "p.8")], applicability="Only if 2.6 is N/PN/NI."),
    },
)

DOMAIN2_ADHERING_METHODOLOGY = DomainMethodology(
    domain_id="D2_ADHERING",
    title="Bias due to deviations from intended interventions: effect of adhering",
    principles=["Use only when the assessment targets the effect of adhering to intervention."],
    rule_cards={
        "2.1": _AWARENESS_21,
        "2.2": _AWARENESS_22,
        "2.3a": RuleCard("2.3a", "Were important non-protocol interventions balanced?", {"Y": ResponseRule("Important non-protocol interventions were clearly balanced."), "PY": ResponseRule("Available data suggest balance."), "PN": ResponseRule("Available data suggest imbalance."), "N": ResponseRule("Important non-protocol interventions were clearly not balanced."), "NI": ResponseRule("Insufficient information."), "NA": ResponseRule("This deviation type is not part of the selected adhering-effect assessment.")}, [Citation(SUPP, "p.12")]),
        "2.4a": RuleCard("2.4a", "Were there failures in implementing the intervention that could have affected the outcome?", {"Y": ResponseRule("Implementation failures clearly could affect the outcome."), "PY": ResponseRule("Implementation failures probably could affect the outcome."), "PN": ResponseRule("Implementation was mostly successful or failures unlikely to affect outcome."), "N": ResponseRule("No relevant implementation failures or no outcome impact."), "NI": ResponseRule("Insufficient information."), "NA": ResponseRule("This deviation type is not part of the selected assessment.")}, [Citation(SUPP, "p.12")]),
        "2.5a": RuleCard("2.5a", "Was non-adherence to assigned intervention likely to affect outcomes?", {"Y": ResponseRule("Non-adherence clearly could affect outcomes."), "PY": ResponseRule("Non-adherence probably could affect outcomes."), "PN": ResponseRule("Non-adherence limited or unlikely to affect outcomes."), "N": ResponseRule("Participants adhered or imperfect adherence cannot affect outcome."), "NI": ResponseRule("Insufficient information."), "NA": ResponseRule("This deviation type is not part of the selected assessment.")}, [Citation(SUPP, "p.13")]),
        "2.6a": RuleCard("2.6a", "Was an appropriate analysis used to estimate the effect of adhering?", {"Y": ResponseRule("Appropriate causal method was used and justified."), "PY": ResponseRule("Appropriate method appears used but assumptions/details are incomplete."), "PN": ResponseRule("Analysis is probably inappropriate or insufficiently justified."), "N": ResponseRule("Naive ITT, per-protocol, as-treated, or treatment-received analysis was used."), "NI": ResponseRule("Insufficient information to judge appropriateness.")}, [Citation(SUPP, "p.14"), Citation(BMJ, "p.3")]),
    },
)
