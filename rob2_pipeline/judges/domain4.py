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

    if s41 in ("N", "PN", "NI") and s42 in ("N", "PN") and s43 in ("N", "PN"):
        return "Low", "4.1=N/PN/NI, 4.2=N/PN, and 4.3=N/PN -> Low"
    if s41 in ("N", "PN", "NI") and s42 in ("N", "PN") and s43 in ("Y", "PY", "NI") and s44 in ("N", "PN"):
        return "Low", "4.1=N/PN/NI, 4.2=N/PN, 4.3=Y/PY/NI, and 4.4=N/PN -> Low"

    if s41 in ("N", "PN", "NI") and s42 == "NI" and s43 in ("N", "PN"):
        return "Some concerns", "4.2=NI and 4.3=N/PN -> Some concerns"
    if s41 in ("N", "PN", "NI") and s42 == "NI" and s43 in ("Y", "PY", "NI") and s44 in ("N", "PN"):
        return "Some concerns", "4.2=NI, 4.3=Y/PY/NI, and 4.4=N/PN -> Some concerns"
    if s41 in ("N", "PN", "NI") and s42 in ("N", "PN", "NI") and s43 in ("Y", "PY", "NI") and s44 in ("Y", "PY", "NI") and s45 in ("N", "PN"):
        return "Some concerns", "4.4=Y/PY/NI and 4.5=N/PN -> Some concerns"
    if s41 in ("N", "PN", "NI") and s42 in ("N", "PN", "NI") and s43 in ("Y", "PY", "NI") and s44 in ("Y", "PY", "NI") and s45 == "NI":
        return "High", "4.4=Y/PY/NI and 4.5=NI -> High"

    return "Some concerns", f"Unresolved D4 answers: 4.1={s41} 4.2={s42} 4.3={s43} 4.4={s44} 4.5={s45}"
