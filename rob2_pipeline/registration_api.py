"""Fetch trial registration data from ClinicalTrials.gov API v2."""
import json
import re
from pathlib import Path
from typing import Optional

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
CACHE_DIR = Path(".rob2_cache/ctgov")


def _cache_path(nct_id: str) -> Path:
    return CACHE_DIR / f"{nct_id}.json"


def fetch_registration(nct_id: str, use_cache: bool = True) -> Optional[dict]:
    """Fetch outcomes module for an NCT trial. Returns None on failure."""
    nct_id = nct_id.upper().strip()
    if not re.match(r"NCT\d{8}", nct_id):
        return None
    cache_file = _cache_path(nct_id)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())
    url = f"{CTGOV_BASE}/{nct_id}"
    params = {"fields": "OutcomesModule,IdentificationModule"}
    try:
        import httpx

        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data))
    return data


def extract_outcomes(registration_data: dict) -> dict:
    """Extract primary and secondary outcomes from ClinicalTrials.gov response."""
    outcomes: dict = {"primary": [], "secondary": [], "other": []}
    try:
        module = (registration_data
                  .get("protocolSection", {})
                  .get("outcomesModule", {}))
        for key, label in [("primaryOutcomes", "primary"),
                            ("secondaryOutcomes", "secondary"),
                            ("otherOutcomes", "other")]:
            for item in module.get(key, []):
                measure = item.get("measure", "").strip()
                if measure:
                    outcomes[label].append(measure)
    except Exception:
        pass
    return outcomes


def format_outcomes_for_prompt(outcomes: dict) -> str:
    """Format extracted outcomes into a text block for LLM prompts."""
    def _xml_safe(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = ["Registered outcomes from ClinicalTrials.gov:"]
    if outcomes["primary"]:
        lines.append("PRIMARY: " + "; ".join(_xml_safe(value) for value in outcomes["primary"]))
    if outcomes["secondary"]:
        lines.append("SECONDARY: " + "; ".join(_xml_safe(value) for value in outcomes["secondary"]))
    if outcomes["other"]:
        lines.append("EXPLORATORY/OTHER: " + "; ".join(_xml_safe(value) for value in outcomes["other"]))
    if not any(outcomes.values()):
        lines.append("(No outcomes retrieved from registration)")
    return "\n".join(lines)
