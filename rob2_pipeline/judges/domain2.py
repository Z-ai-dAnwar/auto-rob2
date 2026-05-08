def judge_domain2(sq: dict) -> tuple[str, str]:
    """
    Implements the two-part algorithm for Domain 2 (ITT / assignment effect).
    """
    s21 = sq.get("2.1", {}).get("answer", "NI")
    s22 = sq.get("2.2", {}).get("answer", "NI")
    s23 = sq.get("2.3", {}).get("answer", "NA")
    s24 = sq.get("2.4", {}).get("answer", "NA")
    s25 = sq.get("2.5", {}).get("answer", "NA")
    s26 = sq.get("2.6", {}).get("answer", "NI")
    s27 = sq.get("2.7", {}).get("answer", "NA")

    def _part1():
        if s21 in ("N", "PN") and s22 in ("N", "PN"):
            return "Low", "Both 2.1 & 2.2 N/PN -> Part1=Low"
        either_aware = s21 in ("Y", "PY", "NI") or s22 in ("Y", "PY", "NI")
        if either_aware and s22 in ("N", "PN"):
            return "Low", "Either aware but 2.2=N/PN -> Part1=Low"
        if either_aware and s22 == "NI":
            return "Some concerns", "2.2=NI -> Part1=Some concerns"
        if either_aware and s22 in ("Y", "PY") and s23 in ("N", "PN"):
            return "Low", "2.3=N/PN (no trial-context deviations) -> Part1=Low"
        if either_aware and s22 in ("Y", "PY") and s23 in ("Y", "PY", "NI"):
            if s24 in ("Y", "PY") and s25 in ("Y", "PY"):
                return "Some concerns", "Deviations balanced -> Part1=Some concerns"
            if s24 in ("N", "PN", "NI") or s25 in ("N", "PN", "NI"):
                return "High", "Deviations unbalanced or uncertain -> Part1=High"
        return "Some concerns", f"Unresolved D2 part 1 answers: 2.1={s21} 2.2={s22} 2.3={s23} 2.4={s24} 2.5={s25}"

    def _part2():
        if s26 in ("Y", "PY"):
            return "Low", "2.6=Y/PY (appropriate ITT analysis) -> Part2=Low"
        if s26 in ("N", "PN", "NI") and s27 in ("N", "PN"):
            return "Some concerns", "2.6 inappropriate but 2.7=N/PN -> Part2=Some concerns"
        if s26 in ("N", "PN", "NI") and s27 in ("Y", "PY", "NI"):
            return "High", "2.6 inappropriate and 2.7=Y/PY/NI -> Part2=High"
        return "Some concerns", f"Unresolved D2 part 2 answers: 2.6={s26} 2.7={s27}"

    p1_j, p1_r = _part1()
    p2_j, p2_r = _part2()

    if p1_j == "High" or p2_j == "High":
        return "High", f"Part1={p1_j} ({p1_r}); Part2={p2_j} ({p2_r})"
    if p1_j == "Some concerns" or p2_j == "Some concerns":
        return "Some concerns", f"Part1={p1_j} ({p1_r}); Part2={p2_j} ({p2_r})"
    return "Low", f"Part1=Low ({p1_r}); Part2=Low ({p2_r})"
