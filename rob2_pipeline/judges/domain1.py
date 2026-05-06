def judge_domain1(sq: dict) -> tuple[str, str]:
    """
    Decision table (from rob2-algorithm.md):
    1.1        | 1.2       | 1.3       | Judgment
    Y/PY/NI    | Y/PY      | NI/N/PN   | Low
    Y/PY       | Y/PY      | Y/PY      | Some concerns
    N/PN/NI    | Y/PY      | Y/PY      | Some concerns
    Any        | NI        | N/PN/NI   | Some concerns
    Any        | NI        | Y/PY      | High
    Any        | N/PN      | Any       | High
    """
    s11 = sq.get("1.1", {}).get("answer", "NI")
    s12 = sq.get("1.2", {}).get("answer", "NI")
    s13 = sq.get("1.3", {}).get("answer", "NI")

    if s12 in ("N", "PN"):
        return "High", "Row: Any / N-PN / Any -> High (allocation not concealed)"
    if s12 == "NI" and s13 in ("Y", "PY"):
        return "High", "Row: Any / NI / Y-PY -> High (no concealment info + baseline imbalance)"
    if s12 == "NI" and s13 in ("N", "PN", "NI"):
        return "Some concerns", "Row: Any / NI / N-PN-NI -> Some concerns (concealment unclear)"
    if s11 in ("Y", "PY", "NI") and s12 in ("Y", "PY") and s13 in ("NI", "N", "PN"):
        return "Low", "Row: Y-PY-NI / Y-PY / NI-N-PN -> Low"
    if s12 in ("Y", "PY") and s13 in ("Y", "PY"):
        return "Some concerns", "Row: Any / Y-PY / Y-PY -> Some concerns (baseline imbalance)"
    return "Some concerns", f"No exact row match for 1.1={s11}, 1.2={s12}, 1.3={s13}; defaulting to Some concerns"
