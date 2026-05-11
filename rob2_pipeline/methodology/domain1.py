from rob2_pipeline.methodology.types import Citation, DomainMethodology, ResponseRule, RuleCard

SUPP = "Sterne 2019 supplement"
BMJ = "Sterne 2019 BMJ"


DOMAIN1_METHODOLOGY = DomainMethodology(
    domain_id="D1",
    title="Bias arising from the randomization process",
    principles=[
        "Judge random sequence generation, allocation concealment, and baseline imbalances separately.",
        "Use NI only when information is insufficient and PY/PN would be unreasonable.",
    ],
    rule_cards={
        "1.1": RuleCard(
            "1.1",
            "Was the allocation sequence random?",
            {
                "Y": ResponseRule("A random component is explicitly described, including computer generation, random tables, chance devices, or minimization with a random element."),
                "PY": ResponseRule("A large or well-run trial lacks details but context supports random generation and no predictable method is suggested."),
                "PN": ResponseRule("Context suggests possible non-random methods and the current report does not clarify."),
                "N": ResponseRule("The sequence is predictable or non-random, such as alternation, dates, record numbers, clinician decisions, or availability."),
                "NI": ResponseRule("The report only states that the study was randomized and provides no useful contextual basis for PY/PN."),
            },
            [Citation(SUPP, "p.1"), Citation(BMJ, "p.3")],
        ),
        "1.2": RuleCard(
            "1.2",
            "Was the allocation sequence concealed until participants were enrolled and assigned to interventions?",
            {
                "Y": ResponseRule("Remote, central, pharmacy-controlled, telephone/internet allocation, or adequately protected envelopes/containers prevented foreknowledge."),
                "PY": ResponseRule("Concealment is strongly implied by restricted access, central control, or trial infrastructure even if operational detail is incomplete."),
                "PN": ResponseRule("The method is incomplete and suggests possible inadequacy, such as envelopes without enough safeguards."),
                "N": ResponseRule("Enrolling investigators or participants could know or predict the forthcoming allocation."),
                "NI": ResponseRule("No useful allocation concealment information is available."),
            },
            [Citation(SUPP, "p.1"), Citation(SUPP, "p.4")],
            notes=[
                'Also score Y or PY when the report describes restricted access to the allocation list using patterns such as "accessible only to [role]", "only [role] had access to the allocation sequence", "[role] alone maintained the randomisation list", or "allocation was not disclosed until after enrolment". These describe concealment through information restriction even if no sealed envelope or telephone system is mentioned. Do not confuse "accessible only to the data manager (and later to investigators after enrolment)" with lack of concealment: disclosure to investigators after enrolment is expected post-randomisation unblinding and does not imply the allocation was known before enrolment.',
                "For large multicenter cooperative-group trials with stratified randomization, balanced groups, and no suggestion that recruiters could foresee assignments, answer PY rather than NI for Q1.2 even if the exact operational concealment mechanism is not named. Reserve NI for reports that only say randomized and provide no trial-infrastructure, stratification, or baseline-balance context.",
            ],
        ),
        "1.3": RuleCard(
            "1.3",
            "Did baseline differences between intervention groups suggest a problem with the randomization process?",
            {
                "Y": ResponseRule("Substantial group-size discrepancies, excess significant imbalances, important prognostic imbalance, or excessive similarity suggest a randomization problem."),
                "PY": ResponseRule("Baseline patterns suggest a possible randomization problem but are not conclusive."),
                "PN": ResponseRule("Minor imbalances are unlikely to indicate material bias."),
                "N": ResponseRule("No important imbalances are apparent or observed imbalances are compatible with chance."),
                "NI": ResponseRule("No useful baseline information is available."),
            },
            [Citation(SUPP, "p.2")],
        ),
    },
)
