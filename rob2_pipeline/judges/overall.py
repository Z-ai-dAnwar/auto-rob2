def judge_overall(domain_judgments: dict) -> tuple[str, str]:
    """
    Low: Low in ALL domains.
    Some concerns: Some concerns in >=1 domain, High in none.
    High: High in >=1 domain. Multiple Some concerns should be escalated only
    when they substantially lower confidence in the result; this implementation
    flags that case for review rather than applying a blind count threshold.
    """
    values = list(domain_judgments.values())

    if any(v == "High" for v in values):
        high_domains = [k for k, v in domain_judgments.items() if v == "High"]
        return "High", f"High in: {', '.join(high_domains)}"

    if values and all(v == "Low" for v in values):
        return "Low", "Low in all 5 domains"

    some_concerns_domains = [k for k, v in domain_judgments.items() if v == "Some concerns"]
    n_sc = len(some_concerns_domains)

    if n_sc == 2:
        return "Some concerns", (
            f"Some concerns in 2 domains: {', '.join(some_concerns_domains)}. "
            "2 domains with Some concerns. "
            "Skill guidance: present both Some concerns and High as plausible if the "
            "concerns are complementary and together substantially lower confidence. "
            "FLAG FOR HUMAN REVIEW."
        )
    if n_sc >= 3:
        return "Some concerns", (
            f"Some concerns in {n_sc} domains ({', '.join(some_concerns_domains)}). "
            "Skill guidance: 3 or more domains with Some concerns is very likely an "
            "overall High judgment if the concerns substantially lower confidence. "
            "Probable High; FLAG FOR HUMAN REVIEW/CONFIRMATION."
        )

    return "Some concerns", f"Some concerns in {n_sc} domain(s): {', '.join(some_concerns_domains)}"
