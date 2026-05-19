from rob2_pipeline.methodology.types import (
    Citation,
    DomainMethodology,
    ResponseRule,
    RuleCard,
)

SUPP = "Sterne 2019 supplement"

DOMAIN3_METHODOLOGY = DomainMethodology(
    domain_id="D3",
    title="Bias due to missing outcome data",
    principles=[
        "Imputed data count as missing outcome data for Q3.1.",
        "Time-to-event censoring before complete follow-up can represent missing outcome data.",
    ],
    rule_cards={
        "3.1": RuleCard(
            "3.1",
            "Were data available for all, or nearly all, randomized participants?",
            {
                "Y": ResponseRule(
                    "Outcome data were available for all or enough participants that missing outcomes could not materially affect the result."
                ),
                "PY": ResponseRule(
                    "Nearly all participants have data and missingness is unlikely to matter."
                ),
                "PN": ResponseRule(
                    "Noticeable missing outcome data may affect the result."
                ),
                "N": ResponseRule(
                    "A significant proportion of outcome data is missing or imputed."
                ),
                "NI": ResponseRule(
                    "The extent of missing outcome data is not reported."
                ),
            },
            [Citation(SUPP, "p.18")],
            notes=[
                "Nearly all means the number with missing outcome data is sufficiently small that their outcomes could have made no important difference. For continuous outcomes, 95 percent availability is often sufficient. For dichotomous outcomes, compare missing participants with observed events. Imputed data are missing data for this question.",
                "For time-to-event outcomes, participants who are administratively censored at end-of-follow-up are NOT missing. Participants censored early because they withdrew, were lost to follow-up, or switched treatments are potentially missing. If the proportion of non-event censorings appears large relative to observed events, investigate whether censoring is informative before answering Y.",
            ],
        ),
        "3.2": RuleCard(
            "3.2",
            "Is there evidence that the result was not biased by missing outcome data?",
            {
                "Y": ResponseRule(
                    "Appropriate correction methods or sensitivity analyses convincingly show no material bias."
                ),
                "PY": ResponseRule(
                    "Methods or sensitivity analyses suggest minimal impact with residual uncertainty."
                ),
                "PN": ResponseRule(
                    "Methods are inadequate, limited, or poorly described."
                ),
                "N": ResponseRule(
                    "No adequate attempt addresses missing-data bias or sensitivity analyses show possible bias."
                ),
                "NA": ResponseRule("Not applicable if Q3.1 is Y/PY."),
            },
            [Citation(SUPP, "p.18")],
        ),
        "3.3": RuleCard(
            "3.3",
            "Could missingness in the outcome depend on its true value?",
            {
                "Y": ResponseRule(
                    "Loss, withdrawal, or censoring is clearly related to health status or outcome."
                ),
                "PY": ResponseRule(
                    "Reasons are ambiguous or could plausibly relate to true outcome value."
                ),
                "PN": ResponseRule(
                    "Most documented reasons are unlikely to relate to true outcome value."
                ),
                "N": ResponseRule(
                    "All missingness is clearly unrelated to outcome, such as technical failure or administrative interruption."
                ),
                "NI": ResponseRule("Reasons or patterns are not described."),
                "NA": ResponseRule("Not applicable when Q3.2 is Y/PY."),
            },
            [Citation(SUPP, "p.18")],
        ),
        "3.4": RuleCard(
            "3.4",
            "Is it likely that missingness depended on its true value?",
            {
                "Y": ResponseRule(
                    "Evidence such as differential missingness, outcome-related reasons, group-specific reasons, trial circumstances, or outcome-related censoring makes dependence likely."
                ),
                "PY": ResponseRule(
                    "Some evidence suggests likely dependence on true outcome value."
                ),
                "PN": ResponseRule(
                    "Reasons and patterns mostly argue against likely outcome dependence."
                ),
                "N": ResponseRule(
                    "Evidence indicates missingness is independent of true outcome value or explained by measured characteristics."
                ),
                "NI": ResponseRule("Insufficient information to judge likelihood."),
                "NA": ResponseRule("Not applicable when Q3.3 is N/PN."),
            },
            [Citation(SUPP, "p.19")],
            notes=[
                "Reasons include differences between groups in missing-data proportions, reasons suggesting outcome-dependence, reasons differing between groups, trial circumstances making outcome-dependent missingness likely, or time-to-event censoring when participants stop/change assigned intervention for outcome-related reasons.",
                "Per the RoB 2 supplement, five specific reasons support answering Y: (1) differences between groups in proportions of missing outcome data; (2) reported reasons for missingness provide evidence of outcome-dependence; (3) reported reasons differ between groups; (4) trial circumstances make outcome-dependent missingness likely; (5) in time-to-event analyses, participants' follow-up is censored when they stop or change their assigned intervention for reasons related to prognosis, treatment failure, or the outcome process.",
                "For time-to-event outcomes, check whether rates of censoring differ between intervention groups — a meaningful difference in censoring rates supports answering Y or PY.",
            ],
        ),
    },
)
