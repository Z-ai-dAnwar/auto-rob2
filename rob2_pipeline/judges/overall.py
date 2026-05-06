def judge_overall(domain_judgments: dict) -> tuple[str, str]:
    """
    Low: Low in ALL domains.
    Some concerns: Some concerns in >=1 domain, High in none.
    High: High in >=1 domain, OR >=3 domains with Some concerns.
    """
    values = list(domain_judgments.values())

    if any(v == "High" for v in values):
        high_domains = [k for k, v in domain_judgments.items() if v == "High"]
        return "High", f"High in: {', '.join(high_domains)}"

    if values and all(v == "Low" for v in values):
        return "Low", "Low in all 5 domains"

    some_concerns_domains = [k for k, v in domain_judgments.items() if v == "Some concerns"]
    n_sc = len(some_concerns_domains)

    if n_sc >= 3:
        return "High", (
            f"Some concerns in {n_sc} domains ({', '.join(some_concerns_domains)}). "
            "Per RoB 2 guidance, multiple Some concerns that substantially lower "
            "confidence yields High overall. FLAG FOR HUMAN REVIEW."
        )
    if n_sc == 2:
        return "Some concerns", (
            f"Some concerns in 2 domains: {', '.join(some_concerns_domains)}. "
            "2 domains with Some concerns - consider upgrading to High if concerns "
            "are in complementary domains. FLAG FOR HUMAN REVIEW."
        )

    return "Some concerns", f"Some concerns in {n_sc} domain(s): {', '.join(some_concerns_domains)}"
