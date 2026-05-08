def judge_domain4(sq: dict) -> tuple[str, str]:
    """Implements the RoB 2 Domain 4 decision table."""
    s41 = sq.get("4.1", {}).get("answer", "NI")
    s42 = sq.get("4.2", {}).get("answer", "NI")
    s43 = sq.get("4.3", {}).get("answer", "NA")
    s44 = sq.get("4.4", {}).get("answer", "NA")
    s45 = sq.get("4.5", {}).get("answer", "NA")

    if s41 in ("Y", "PY"):
        return "High", "4.1=Y/PY (inappropriate measurement method) -> High"
    if s42 in ("Y", "PY"):
        return "High", "4.2=Y/PY (differential measurement between groups) -> High"
    if s45 in ("Y", "PY"):
        return "High", "4.5=Y/PY (assessment likely influenced by intervention knowledge) -> High"

    if s41 in ("N", "PN") and s42 in ("N", "PN") and (s43 in ("N", "PN") or s44 in ("N", "PN")):
        return "Low", "4.1 and 4.2 are N/PN and 4.3 or 4.4 is N/PN -> Low"

    return "Some concerns", f"Unresolved D4 answers: 4.1={s41} 4.2={s42} 4.3={s43} 4.4={s44} 4.5={s45}"
