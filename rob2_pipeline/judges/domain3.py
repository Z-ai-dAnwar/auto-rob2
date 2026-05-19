def judge_domain3(sq: dict) -> tuple[str, str]:
    """
    3.1=Y/PY -> Low
    3.1=N/PN/NI | 3.2=Y/PY -> Low
    3.1=N/PN/NI | 3.2=N/PN | 3.3=N/PN -> Low
    3.1=N/PN/NI | 3.2=N/PN | 3.3=Y/PY/NI | 3.4=N/PN -> Some concerns
    3.1=N/PN/NI | 3.2=N/PN | 3.3=Y/PY/NI | 3.4=Y/PY/NI -> High
    """
    s31 = sq.get("3.1", {}).get("answer", "NI")
    s32 = sq.get("3.2", {}).get("answer", "NA")
    s33 = sq.get("3.3", {}).get("answer", "NA")
    s34 = sq.get("3.4", {}).get("answer", "NA")

    if s31 in ("Y", "PY"):
        return "Low", "3.1=Y/PY (nearly complete data) -> Low"
    if s32 in ("Y", "PY"):
        return "Low", "3.2=Y/PY (evidence of no bias from missing data) -> Low"
    if s33 in ("N", "PN"):
        return "Low", "3.3=N/PN (missingness cannot depend on true value) -> Low"
    if s33 in ("Y", "PY", "NI") and s34 in ("Y", "PY", "NI"):
        return "High", "3.3=Y/PY/NI and 3.4=Y/PY/NI -> High"
    if s33 in ("Y", "PY", "NI") and s34 in ("N", "PN"):
        return "Some concerns", "3.3=Y/PY/NI and 3.4=N/PN -> Some concerns"
    return (
        "Some concerns",
        f"Unresolved D3 answers: 3.1={s31} 3.2={s32} 3.3={s33} 3.4={s34}",
    )
