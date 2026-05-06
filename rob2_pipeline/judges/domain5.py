def judge_domain5(sq: dict) -> tuple[str, str]:
    """Implements the RoB 2 Domain 5 decision table."""
    s51 = sq.get("5.1", {}).get("answer", "NI")
    s52 = sq.get("5.2", {}).get("answer", "NI")
    s53 = sq.get("5.3", {}).get("answer", "NI")

    if s52 in ("Y", "PY") or s53 in ("Y", "PY"):
        return "High", "5.2 or 5.3 = Y/PY (selective result reporting) -> High"
    if s51 in ("Y", "PY") and s52 in ("N", "PN") and s53 in ("N", "PN"):
        return "Low", "5.1=Y/PY and 5.2=5.3=N/PN -> Low"
    return "Some concerns", f"5.1={s51} 5.2={s52} 5.3={s53} -> Some concerns"
