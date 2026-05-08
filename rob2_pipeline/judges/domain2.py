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
        if (s21 in ("N", "PN") and s22 in ("N", "PN")) or s23 in ("N", "PN") or s24 in ("N", "PN"):
            return "Low", "Part1 Low condition met"
        if s23 in ("Y", "PY") and s24 in ("Y", "PY") and s25 in ("N", "PN", "NI"):
            return "High", "Part1 High condition met"
        return "Some concerns", "Part1 default to Some concerns"

    def _part2():
        if s26 in ("Y", "PY"):
            return "Low", "2.6=Y/PY (appropriate ITT analysis) -> Part2=Low"
        if s26 in ("N", "PN") and s27 in ("Y", "PY"):
            return "High", "2.6=N/PN and 2.7=Y/PY -> Part2=High"
        if s26 in ("N", "PN") and s27 in ("N", "PN", "NI"):
            return "Some concerns", "2.6=N/PN and 2.7=N/PN/NI -> Part2=Some concerns"
        return "Some concerns", "Part2 default to Some concerns"

    p1_j, p1_r = _part1()
    p2_j, p2_r = _part2()

    if p1_j == "High" or p2_j == "High":
        return "High", f"Part1={p1_j} ({p1_r}); Part2={p2_j} ({p2_r})"
    if p1_j == "Some concerns" or p2_j == "Some concerns":
        return "Some concerns", f"Part1={p1_j} ({p1_r}); Part2={p2_j} ({p2_r})"
    return "Low", f"Part1=Low ({p1_r}); Part2=Low ({p2_r})"
