from rob2_pipeline.methodology.types import Citation, DomainMethodology, ResponseRule, RuleCard

SUPP = "Sterne 2019 supplement"

DOMAIN5_METHODOLOGY = DomainMethodology(
    domain_id="D5",
    title="Bias in selection of the reported result",
    principles=["Assess the specific numerical result for the outcome under review, not selective non-reporting of other outcomes at review level."],
    rule_cards={
        "5.1": RuleCard("5.1", "Were data analysed according to a pre-specified plan finalized before unblinded outcome data were available?", {"Y": ResponseRule("A sufficiently detailed pre-specified plan was finalized before unblinded data and followed."), "PY": ResponseRule("Strong indication of pre-specification exists, with some detail missing or minor justified deviations."), "PN": ResponseRule("A plan is mentioned but not detailed enough, or unexplained deviations raise concern."), "N": ResponseRule("Clear post hoc decisions, endpoint switching, or result-based changes occurred."), "NI": ResponseRule("No adequate information on pre-specified analysis intentions or timing.")}, [Citation(SUPP, "p.26")]),
        "5.2": RuleCard("5.2", "Was the result selected from multiple eligible outcome measurements within the outcome domain?", {"Y": ResponseRule("Multiple eligible measurements existed, only a subset is reported without justification, and result-based selection is clear."), "PY": ResponseRule("Multiple eligible measurements likely existed and reporting appears potentially selective."), "PN": ResponseRule("Most intended measurements are reported or omissions are explained."), "N": ResponseRule("All intended eligible measurements are reported, only one measurement was possible, or inconsistencies are unrelated to results."), "NI": ResponseRule("Analysis intentions are unavailable or insufficient and multiple eligible measurements could have existed.")}, [Citation(SUPP, "p.26-27")]),
        "5.3": RuleCard("5.3", "Was the result selected from multiple eligible analyses of the data?", {"Y": ResponseRule("Multiple eligible analyses existed, only a subset is reported without justification, and result-based selection is clear."), "PY": ResponseRule("Multiple analyses likely existed and reporting appears potentially selective."), "PN": ResponseRule("Intended analyses are mostly reported or omissions are explained."), "N": ResponseRule("All intended analyses are reported, only one analysis was possible, or inconsistencies are unrelated to results."), "NI": ResponseRule("Analysis intentions are unavailable or insufficient and multiple eligible analyses could have existed.")}, [Citation(SUPP, "p.27-28")]),
    },
)
