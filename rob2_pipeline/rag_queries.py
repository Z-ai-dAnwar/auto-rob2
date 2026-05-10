DOMAIN_QUERIES: dict[str, list[str]] = {
    "d1": [
        "allocation sequence randomization random number concealed envelope",
        "allocation concealment sealed envelope central randomization independent",
        "baseline characteristics demographics imbalance groups comparable",
    ],
    "d2_blinding": [
        "participant blinded masked open-label double-blind aware treatment assignment",
        "carer clinician deliverer aware blinded unblinded intervention",
    ],
    "d2_deviations": [
        "protocol deviation adherence crossover non-adherence dropout discontinuation trial context",
        "concomitant medication rescue therapy additional treatment co-intervention",
    ],
    "d2_analysis": [
        "intention to treat per-protocol modified ITT analysis population",
        "excluded participants post-randomization missing data imputation sensitivity analysis",
    ],
    "d3": [
        "lost to follow-up missing data withdrawal dropout CONSORT flow diagram",
        "sensitivity analysis multiple imputation missing outcome completeness",
        "censoring data maturity minimum follow-up event count",
    ],
    "d4_measurement": [
        "outcome measurement instrument assessment tool questionnaire scale definition",
        "primary outcome endpoint measurement method frequency timing schedule",
        "differential measurement different between groups visit diagnostic opportunity",
    ],
    "d4_assessor": [
        "outcome assessor blinded masked open-label aware treatment assignment",
        "independent adjudication central review blinded committee endpoint review",
        "patient reported outcome PRO self-report questionnaire participant",
    ],
    "d5": [
        "trial registration protocol pre-specified primary outcome analysis plan",
        "ClinicalTrials.gov ISRCTN registered protocol amendment statistical analysis plan",
        "reported outcomes selective reporting pre-planned endpoints",
    ],
}
