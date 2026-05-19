import os
import re


SECTION_PATTERNS = {
    "abstract": ["abstract"],
    "methods": [
        "methods",
        "materials and methods",
        "patients and methods",
        "study design",
        "methodology",
    ],
    "randomization": [
        "randomis",
        "randomiz",
        "random allocation",
        "allocation sequence",
        "sequence generation",
    ],
    "blinding": ["blind", "mask", "open-label", "open label", "double-blind"],
    "outcomes": [
        "outcome",
        "endpoint",
        "primary outcome",
        "secondary outcome",
        "efficacy measure",
    ],
    "analysis": [
        "statistical analysis",
        "statistical methods",
        "data analysis",
        "intention-to-treat",
        "per-protocol",
        "analysis population",
    ],
    "results": ["results", "findings"],
    "missing_data": [
        "missing data",
        "lost to follow",
        "dropout",
        "withdrawal",
        "discontinu",
    ],
    "registration": [
        "clinicaltrials",
        "isrctn",
        "trial registration",
        "registered",
        "protocol number",
    ],
    "baseline": ["baseline", "demographic", "characteristics"],
    "consort": [
        "consort",
        "flow diagram",
        "figure 1",
        "participant flow",
        "screened",
        "enrolled",
        "randomized",
        "allocated",
    ],
    "supplementary": ["supplement", "appendix", "online material"],
}

SECTION_ORDER = list(SECTION_PATTERNS)
MAX_SECTION_CHARS = 10000
MIN_EXTRACTED_CHARS = 20
EMBED_MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBED_MAX_TOKENS = 256
TOKENIZER_COUNTING_MAX_LENGTH = 10**9
CENSORING_PATTERNS = [
    re.compile(r"(?i)\bcensor\w*\b.*\d|\d.*\bcensor\w*\b"),
    re.compile(r"(?i)\bdata[ -]?maturity\b.*\d|\d\s*%\s*data\s*maturity"),
    re.compile(r"(?i)\bdata[ -]?cut(?:off)?\b.*\d|\d.*\bdata[ -]?cut(?:off)?\b"),
    re.compile(
        r"(?i)\bfollow[ -]?up\b.*\bcomplete\b.*\d|\d.*\bfollow[ -]?up\b.*\bcomplete\b"
    ),
    re.compile(r"(?i)\badministratively\s+censored\b"),
    re.compile(r"(?i)\bmedian\s+follow[ -]?up\b.*\d"),
    re.compile(r"(?i)\b\d[\d,]*\s*/\s*\d[\d,]*\s+participants?\b.*\bevents?\b"),
    re.compile(r"(?i)\b\d[\d,]*\s+events?\b.*\d|\d.*\b\d[\d,]*\s+events?\b"),
]


def allow_remote_evidence_extraction() -> bool:
    return os.getenv("ROB2_REMOTE_EVIDENCE_EXTRACTION", "1").strip() not in {
        "0",
        "false",
        "False",
    }


def appears_rct_candidate(text: str) -> bool:
    lowered = text.lower()
    trial_signals = [
        "random",
        "randomized",
        "randomised",
        "assigned",
        "allocation",
        "placebo",
        "double-blind",
    ]
    context_signals = ["trial", "participants", "patients", "phase "]
    return any(signal in lowered for signal in trial_signals) and any(
        signal in lowered for signal in context_signals
    )
