import re

from rob2_pipeline.models import format_evidence
from rob2_pipeline.state import RoB2State


_FACT_PATTERNS = {
    "randomization": re.compile(
        r"\b(randomi[sz]\w*|minimi[sz]\w*|allocation sequence|assigned)\b", re.I
    ),
    "allocation_concealment": re.compile(
        r"\b(conceal|central|sealed|envelope|telephone|web|interactive|accessed only|not disclosed)\b",
        re.I,
    ),
    "masking": re.compile(r"\b(mask|blind|open[- ]label|aware|unaware)\b", re.I),
    "protocol_deviations": re.compile(
        r"\b(deviation|non[- ]adherence|cross[- ]over|contamination|withdraw|discontinu)\b",
        re.I,
    ),
    "protocol_amendments": re.compile(
        r"\b(protocol amendment|amended|modification|standard of care|standard-of-care|regulatory approval)\b",
        re.I,
    ),
    "analysis_populations": re.compile(
        r"\b(intention[- ]to[- ]treat|ITT|modified intention|per[- ]protocol|as treated|safety population|analysis population)\b",
        re.I,
    ),
}


def _sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    return [
        part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()
    ]


def _matching_snippets(text: str, pattern: re.Pattern, limit: int = 3) -> str:
    snippets = []
    for sentence in _sentences(text):
        if pattern.search(sentence):
            snippets.append(sentence)
        if len(snippets) >= limit:
            break
    return " ".join(snippets)


def extract_trial_facts(state: RoB2State) -> dict[str, str]:
    evidence = state.get("evidence", {})
    text = "\n\n".join(
        part
        for part in [
            format_evidence(evidence.get("d1_randomization", {})),
            format_evidence(evidence.get("d2_blinding", {})),
            format_evidence(evidence.get("d5_registration", {})),
            format_evidence(evidence.get("methods", {})),
            format_evidence(evidence.get("results", {})),
        ]
        if part
    )
    facts = {
        name: _matching_snippets(text, pattern)
        for name, pattern in _FACT_PATTERNS.items()
    }
    facts["source"] = "paper_evidence"
    return facts


def trial_facts_node(state: RoB2State) -> RoB2State:
    return {"trial_facts": extract_trial_facts(state)}
