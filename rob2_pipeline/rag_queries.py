"""Per-signalling-question query sets for RAG retrieval."""

SQ_QUERIES: dict[str, list[str]] = {
    "1.1": [
        "sequence generation method",
        "randomization method computer generated block stratified minimization",
        "random number table minimization",
        "allocation sequence generation",
        "how were participants randomized",
    ],
    "1.2": [
        "allocation concealment method",
        "sealed opaque envelopes central randomization",
        "pharmacy controlled allocation",
        "allocation sequence concealed from enrolling clinician",
        "concealment of randomization",
    ],
    "1.3": [
        "baseline imbalance between groups",
        "prognostic factor differences at baseline",
        "table 1 baseline characteristics",
        "chance imbalance randomization groups",
        "baseline covariate balance",
    ],
    "2.1": [
        "participants blinded to treatment",
        "patient masking allocation",
        "double blind participants open label",
        "unblinded participants aware of assignment",
        "patient knowledge of treatment allocation",
    ],
    "2.2": [
        "carers or personnel blinded",
        "healthcare provider masking",
        "clinical staff unblinded to treatment",
        "investigators aware of treatment assignment",
        "personnel blinding",
    ],
    "2.3": [
        "unintended deviations from protocol",
        "protocol violations cross-over",
        "contamination between arms",
        "co-interventions applied differentially",
        "adherence to assigned intervention",
    ],
    "2.4": [
        "deviations initiated for beneficial reason",
        "allowed rescue medication deviations",
        "permitted deviations protocol",
        "discontinuation due to lack of effect",
    ],
    "2.5": [
        "intention to treat analysis ITT",
        "modified ITT per-protocol population",
        "as-randomized analysis",
        "all randomized participants included analysis",
        "analysis population definition",
    ],
    "2.6": [
        "statistical analysis plan adherence",
        "analysis method as pre-specified",
        "deviation from planned statistical method",
        "primary analysis method",
    ],
    "2.7": [
        "effect of assignment to intervention",
        "effect of adherence to intervention",
        "complier average causal effect CACE",
        "instrumental variable analysis",
    ],
    "3.1": [
        "missing outcome data proportion",
        "loss to follow-up rate",
        "withdrawal dropout attrition rate",
        "number of participants with missing data",
        "proportion missing by arm",
    ],
    "3.2": [
        "reasons for missing outcome data",
        "missing at random assumption",
        "differential missing between groups",
        "reasons for withdrawal by arm",
        "informative censoring",
    ],
    "3.3": [
        "missing data handling method",
        "multiple imputation last observation carried forward",
        "complete case analysis missing data",
        "sensitivity analysis for missing data",
        "statistical method for dropouts",
    ],
    "3.4": [
        "sensitivity analysis missing data tipping point",
        "pattern mixture model",
        "best case worst case scenario analysis",
        "robustness of results to missing data assumptions",
    ],
    "4.1": [
        "outcome assessors blinded",
        "blinded outcome measurement masked assessors",
        "unblinded outcome assessors aware of allocation",
        "knowledge of treatment assignment outcome measurement",
        "assessor blinding",
    ],
    "4.2": [
        "outcome measurement method validated instrument",
        "objective measurement self-reported outcome",
        "patient reported outcome PRO",
        "imaging central review",
        "outcome definition assessment method",
    ],
    "4.3": [
        "differential outcome misclassification between groups",
        "measurement error outcome",
        "systematic bias in outcome measurement",
        "outcome assessment reliability",
    ],
    "4.4": [
        "independent outcome adjudication committee",
        "blinded adjudication committee events",
        "central review adjudication",
        "endpoint committee",
    ],
    "4.5": [
        "composite endpoint definition components",
        "primary endpoint specification",
        "outcome definition protocol",
        "endpoint adjudication criteria",
    ],
    "5.1": [
        "trial registration number NCT ISRCTN EudraCT",
        "prospective registration ClinicalTrials.gov",
        "registered before enrollment",
        "trial registry entry",
        "registration date versus start date",
    ],
    "5.2": [
        "registered primary outcome matches reported",
        "primary endpoint consistent with registration",
        "outcome switching from registered protocol",
        "discrepancy between registered and reported outcomes",
        "protocol deviation outcome definition",
    ],
    "5.3": [
        "selective outcome reporting multiple analyses",
        "subgroup analysis pre-specified",
        "data dredging fishing multiple comparisons",
        "unreported outcomes suppressed results",
        "statistical analysis plan SAP finalized pre-specified analysis",
        "all pre-specified outcomes reported",
    ],
}


def domain_queries(domain: str) -> list[str]:
    """Return all signalling-question queries for a domain like ``d1``."""
    prefix = domain.removeprefix("d")
    return [
        query
        for sq_id, queries in SQ_QUERIES.items()
        if sq_id.startswith(f"{prefix}.")
        for query in queries
    ]
