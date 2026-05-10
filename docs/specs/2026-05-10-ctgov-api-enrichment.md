# CT.gov API Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand ClinicalTrials.gov API data extraction and route relevant registry metadata into each domain's SQ prompt, eliminating false-NI and false-PN answers without hardcoding trial-specific logic.

**Architecture:** Pull `DesignModule`, `DescriptionModule`, `OversightModule`, `SponsorCollaboratorsModule`, and results-section flow data from CT.gov; extract into typed dicts; format into clearly-labeled "authoritative registry metadata" blocks; inject into domain prompts that currently operate blind to this evidence. PDF evidence remains primary; CT.gov augments rather than overrides. Trials lacking CT.gov data see no change.

**Tech Stack:** Python 3.11+, httpx, LangGraph state machine, lxml; no new dependencies.

---

## Context

**Why:** The pipeline issues "Some concerns" on Domain 1 and Domain 5 for CHAARTED (and likely other registered trials) because:
- D1 Q1.1/Q1.2: LLM answers `NI` when the paper text lacks explicit randomization/concealment description, but CT.gov field `designInfo.allocationType = RANDOMIZED` and `oversightHasDmc = true` are authoritative evidence the LLM never sees.
- D5 Q5.1: LLM answers `PN` when `descriptionModule.detailedDescription` contains the pre-specified PRIMARY/SECONDARY/TERTIARY objectives—but we only fetch `OutcomesModule` and `IdentificationModule`.

**What we are NOT doing:**
- No hardcoded if-then rules ("if RANDOMIZED → Y")
- No special-casing of CHAARTED or any specific trial
- No changes to judge tables (they are correct)
- No removal of PDF-based evidence paths (CT.gov augments, doesn't replace)

---

## File Map

| File | Change |
|---|---|
| `rob2_pipeline/registration_api.py` | Expand `fields`, add `extract_design_info()`, `extract_description()`, `extract_participant_flow()`, `format_design_for_prompt()`, `format_description_for_prompt()`, `format_flow_for_prompt()` |
| `rob2_pipeline/state.py` | Add `ctgov_design`, `ctgov_description`, `ctgov_flow` fields |
| `rob2_pipeline/nodes/preliminary.py` | Call new extractors, populate new state fields |
| `rob2_pipeline/prompts.py` | Add `{ctgov_design}` to D1 and D2_SQ12; `{ctgov_flow}` to D3; `{ctgov_description}` to D5 |
| `rob2_pipeline/nodes/domain1.py` | Pass `ctgov_design` to prompt |
| `rob2_pipeline/nodes/domain2.py` | Pass `ctgov_design` to `PROMPT_DOMAIN2_SQ12` |
| `rob2_pipeline/nodes/domain3.py` | Pass `ctgov_flow` to prompt |
| `rob2_pipeline/nodes/domain5.py` | Pass `ctgov_description` to prompt |
| `rob2_pipeline/rag_queries.py` | Expand D1 and D5 query sets |
| `tests/test_registration_api.py` | New: unit tests for all new extractors and formatters |

---

## Task 1: Expand CT.gov API extraction

**Files:**
- Modify: `rob2_pipeline/registration_api.py`
- Create: `tests/test_registration_api.py`

The cache must be versioned so existing cached responses (which lack the new modules) are not reused. Add a `_CACHE_VERSION` constant and include it in the cache file name.

- [ ] **Step 1: Write failing tests for new extractors**

Create `tests/test_registration_api.py`:

```python
"""Tests for ClinicalTrials.gov API extraction functions."""
import pytest
from rob2_pipeline.registration_api import (
    extract_design_info,
    extract_description,
    extract_participant_flow,
    format_design_for_prompt,
    format_description_for_prompt,
    format_flow_for_prompt,
)

# Minimal CT.gov response matching real API shape for CHAARTED
SAMPLE_DATA = {
    "protocolSection": {
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE3"],
            "designInfo": {
                "allocationType": "RANDOMIZED",
                "interventionModel": "PARALLEL",
                "primaryPurpose": "TREATMENT",
                "maskingInfo": {
                    "masking": "NONE",
                    "whoMasked": [],
                },
            },
            "enrollmentInfo": {"count": 790, "enrollmentType": "ACTUAL"},
        },
        "descriptionModule": {
            "briefSummary": "Phase III trial of ADT plus docetaxel vs ADT alone.",
            "detailedDescription": "PRIMARY OBJECTIVE: Overall survival.\nSECONDARY OBJECTIVE: Time to castration resistance.",
        },
        "oversightModule": {
            "oversightHasDmc": True,
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {
                "name": "ECOG-ACRIN Cancer Research Group",
                "class": "NETWORK",
            },
        },
        "outcomesModule": {
            "primaryOutcomes": [{"measure": "Overall Survival"}],
            "secondaryOutcomes": [{"measure": "Time to CRPC"}],
        },
    },
    "resultsSection": {
        "participantFlowModule": {
            "recruitmentDetails": "Study activated 2006; 790 accrued.",
            "groups": [
                {"id": "FG000", "title": "ADT + Docetaxel"},
                {"id": "FG001", "title": "ADT Alone"},
            ],
            "periods": [
                {
                    "title": "Overall Study",
                    "milestones": [
                        {
                            "type": "STARTED",
                            "title": "STARTED",
                            "achievements": [
                                {"groupId": "FG000", "numSubjects": "397"},
                                {"groupId": "FG001", "numSubjects": "393"},
                            ],
                        },
                        {
                            "type": "COMPLETED",
                            "title": "COMPLETED",
                            "achievements": [
                                {"groupId": "FG000", "numSubjects": "391"},
                                {"groupId": "FG001", "numSubjects": "393"},
                            ],
                        },
                    ],
                    "dropWithdraws": [
                        {
                            "type": "Withdrawal by Subject",
                            "reasons": [
                                {"groupId": "FG000", "numSubjects": "6"},
                                {"groupId": "FG001", "numSubjects": "0"},
                            ],
                        }
                    ],
                }
            ],
        },
    },
}

EMPTY_DATA = {}


def test_extract_design_info_full():
    design = extract_design_info(SAMPLE_DATA)
    assert design["allocation"] == "RANDOMIZED"
    assert design["masking"] == "NONE"
    assert design["has_dmc"] is True
    assert design["sponsor_name"] == "ECOG-ACRIN Cancer Research Group"
    assert design["sponsor_class"] == "NETWORK"
    assert "PHASE3" in design["phases"]
    assert design["enrollment"] == 790


def test_extract_design_info_empty():
    design = extract_design_info(EMPTY_DATA)
    assert design == {}


def test_extract_description_full():
    desc = extract_description(SAMPLE_DATA)
    assert "PRIMARY OBJECTIVE" in desc
    assert "Overall survival" in desc
    assert "Phase III trial" in desc


def test_extract_description_empty():
    desc = extract_description(EMPTY_DATA)
    assert desc == ""


def test_extract_participant_flow_full():
    flow = extract_participant_flow(SAMPLE_DATA)
    assert "ADT + Docetaxel" in flow
    assert "ADT Alone" in flow
    assert "397" in flow
    assert "Withdrawal by Subject" in flow


def test_extract_participant_flow_no_results():
    data = {"protocolSection": SAMPLE_DATA["protocolSection"]}
    flow = extract_participant_flow(data)
    assert flow == ""


def test_format_design_for_prompt_includes_key_fields():
    design = extract_design_info(SAMPLE_DATA)
    text = format_design_for_prompt(design)
    assert "RANDOMIZED" in text
    assert "NONE" in text
    assert "ECOG-ACRIN" in text
    assert "ClinicalTrials.gov" in text


def test_format_design_for_prompt_empty():
    text = format_design_for_prompt({})
    assert "No design metadata" in text


def test_format_description_for_prompt():
    desc = extract_description(SAMPLE_DATA)
    text = format_description_for_prompt(desc)
    assert "PRIMARY OBJECTIVE" in text


def test_format_description_for_prompt_empty():
    text = format_description_for_prompt("")
    assert "No description" in text


def test_format_flow_for_prompt():
    flow = extract_participant_flow(SAMPLE_DATA)
    text = format_flow_for_prompt(flow)
    assert "ADT" in text


def test_format_flow_for_prompt_empty():
    text = format_flow_for_prompt("")
    assert "No participant flow" in text
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_registration_api.py -v
```

Expected: all tests FAIL with `ImportError` (functions don't exist yet).

- [ ] **Step 3: Implement new extractors and formatters in `registration_api.py`**

Replace the entire file content with:

```python
"""Fetch trial registration data from ClinicalTrials.gov API v2."""
import json
import re
from pathlib import Path
from typing import Optional

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
CACHE_DIR = Path(".rob2_cache/ctgov")
_CACHE_VERSION = "v2"  # bump to invalidate cached responses missing new modules

_FIELDS = ",".join([
    "OutcomesModule",
    "IdentificationModule",
    "DesignModule",
    "DescriptionModule",
    "OversightModule",
    "SponsorCollaboratorsModule",
    "ParticipantFlowModule",
])


def _cache_path(nct_id: str) -> Path:
    return CACHE_DIR / f"{nct_id}_{_CACHE_VERSION}.json"


def fetch_registration(nct_id: str, use_cache: bool = True) -> Optional[dict]:
    """Fetch study modules for an NCT trial. Returns None on failure."""
    nct_id = nct_id.upper().strip()
    if not re.match(r"NCT\d{8}", nct_id):
        return None
    cache_file = _cache_path(nct_id)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())
    url = f"{CTGOV_BASE}/{nct_id}"
    params = {"fields": _FIELDS}
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


# ---------------------------------------------------------------------------
# Outcomes (existing, unchanged)
# ---------------------------------------------------------------------------

def extract_outcomes(registration_data: dict) -> dict:
    """Extract primary and secondary outcomes from CT.gov response."""
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
        lines.append("PRIMARY: " + "; ".join(_xml_safe(v) for v in outcomes["primary"]))
    if outcomes["secondary"]:
        lines.append("SECONDARY: " + "; ".join(_xml_safe(v) for v in outcomes["secondary"]))
    if outcomes["other"]:
        lines.append("EXPLORATORY/OTHER: " + "; ".join(_xml_safe(v) for v in outcomes["other"]))
    if not any(outcomes.values()):
        lines.append("(No outcomes retrieved from registration)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Design metadata (NEW)
# ---------------------------------------------------------------------------

def extract_design_info(registration_data: dict) -> dict:
    """Extract design metadata: allocation, masking, DMC, sponsor, phase."""
    design: dict = {}
    try:
        protocol = registration_data.get("protocolSection", {})
        design_module = protocol.get("designModule", {})
        design_info = design_module.get("designInfo", {})
        masking_info = design_info.get("maskingInfo", {})
        oversight = protocol.get("oversightModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        lead_sponsor = sponsor_module.get("leadSponsor", {})
        enrollment = design_module.get("enrollmentInfo", {})
        phases = design_module.get("phases", [])

        design["allocation"] = design_info.get("allocationType", "")
        design["intervention_model"] = design_info.get("interventionModel", "")
        design["primary_purpose"] = design_info.get("primaryPurpose", "")
        design["masking"] = masking_info.get("masking", "")
        design["who_masked"] = masking_info.get("whoMasked", [])
        design["has_dmc"] = oversight.get("oversightHasDmc")
        design["sponsor_name"] = lead_sponsor.get("name", "")
        design["sponsor_class"] = lead_sponsor.get("class", "")
        design["enrollment"] = enrollment.get("count", "")
        design["phases"] = phases if isinstance(phases, list) else ([phases] if phases else [])
    except Exception:
        pass
    return design


def format_design_for_prompt(design: dict) -> str:
    """Format design metadata as a labeled text block for LLM prompts."""
    if not design:
        return "(No design metadata retrieved from ClinicalTrials.gov)"

    lines = ["Authoritative ClinicalTrials.gov registry design metadata:"]
    if design.get("allocation"):
        lines.append(f"  Allocation type: {design['allocation']}")
    if design.get("intervention_model"):
        lines.append(f"  Intervention model: {design['intervention_model']}")
    if design.get("masking"):
        who = (", ".join(design["who_masked"])
               if design.get("who_masked") else "not specified")
        lines.append(f"  Masking: {design['masking']} (masked parties: {who})")
    if design.get("has_dmc") is not None:
        lines.append(f"  Data monitoring committee (DMC): {'Yes' if design['has_dmc'] else 'No'}")
    if design.get("sponsor_name"):
        lines.append(f"  Lead sponsor: {design['sponsor_name']} (class: {design.get('sponsor_class', 'unknown')})")
    if design.get("phases"):
        lines.append(f"  Phase: {', '.join(design['phases'])}")
    if design.get("enrollment"):
        lines.append(f"  Total enrolled: {design['enrollment']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Study description (NEW)
# ---------------------------------------------------------------------------

def extract_description(registration_data: dict) -> str:
    """Extract brief summary and detailed description (pre-specified objectives)."""
    try:
        desc_module = (registration_data
                       .get("protocolSection", {})
                       .get("descriptionModule", {}))
        brief = (desc_module.get("briefSummary") or "").strip()
        detailed = (desc_module.get("detailedDescription") or "").strip()
        parts = []
        if brief:
            parts.append(f"Brief summary: {brief}")
        if detailed:
            parts.append(
                "Detailed description (pre-specified objectives and analysis):\n" + detailed
            )
        return "\n\n".join(parts)
    except Exception:
        return ""


def format_description_for_prompt(description: str) -> str:
    """Format description as a labeled text block for LLM prompts."""
    if not description:
        return "(No description retrieved from ClinicalTrials.gov)"
    return "Authoritative ClinicalTrials.gov registry description:\n" + description


# ---------------------------------------------------------------------------
# Participant flow (NEW)
# ---------------------------------------------------------------------------

def extract_participant_flow(registration_data: dict) -> str:
    """Extract arm-level participant flow and withdrawal data from resultsSection."""
    try:
        flow_module = (registration_data
                       .get("resultsSection", {})
                       .get("participantFlowModule", {}))
        if not flow_module:
            return ""

        lines = ["Participant flow (from ClinicalTrials.gov posted results):"]

        recruitment = (flow_module.get("recruitmentDetails") or "").strip()
        if recruitment:
            lines.append(f"  Recruitment: {recruitment}")

        groups = {g["id"]: g["title"] for g in flow_module.get("groups", [])}

        for period in flow_module.get("periods", []):
            for milestone in period.get("milestones", []):
                label = milestone.get("title") or milestone.get("type", "")
                counts = [
                    f"{groups.get(a['groupId'], a['groupId'])}: {a.get('numSubjects', '?')}"
                    for a in milestone.get("achievements", [])
                ]
                if counts:
                    lines.append(f"  {label}: {', '.join(counts)}")
            for dw in period.get("dropWithdraws", []):
                reason = dw.get("type", "Unknown")
                counts = [
                    f"{groups.get(r['groupId'], r['groupId'])}: {r.get('numSubjects', '?')}"
                    for r in dw.get("reasons", [])
                ]
                if counts:
                    lines.append(f"  Withdrawal — {reason}: {', '.join(counts)}")

        return "\n".join(lines)
    except Exception:
        return ""


def format_flow_for_prompt(flow: str) -> str:
    """Format participant flow as a labeled text block for LLM prompts."""
    if not flow:
        return "(No participant flow data retrieved from ClinicalTrials.gov)"
    return flow
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_registration_api.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add rob2_pipeline/registration_api.py tests/test_registration_api.py
git commit -m "feat: expand CT.gov API extraction to include design, description, and participant flow"
```

---

## Task 2: Add new state fields and populate them in preliminary node

**Files:**
- Modify: `rob2_pipeline/state.py`
- Modify: `rob2_pipeline/nodes/preliminary.py`

- [ ] **Step 1: Write failing test for new state fields**

Add to `tests/test_graph.py`:

```python
def test_preliminary_node_populates_ctgov_fields(monkeypatch):
    """preliminary_info_node should populate ctgov_design, ctgov_description, ctgov_flow."""
    import rob2_pipeline.registration_api as api_mod
    from rob2_pipeline.nodes.preliminary import preliminary_info_node

    fake_reg_data = {
        "protocolSection": {
            "designModule": {
                "phases": ["PHASE3"],
                "designInfo": {
                    "allocationType": "RANDOMIZED",
                    "interventionModel": "PARALLEL",
                    "primaryPurpose": "TREATMENT",
                    "maskingInfo": {"masking": "NONE", "whoMasked": []},
                },
                "enrollmentInfo": {"count": 790},
            },
            "descriptionModule": {
                "briefSummary": "Phase III RCT.",
                "detailedDescription": "PRIMARY: OS.",
            },
            "oversightModule": {"oversightHasDmc": True},
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Test Network", "class": "NETWORK"}
            },
            "outcomesModule": {
                "primaryOutcomes": [{"measure": "Overall Survival"}],
                "secondaryOutcomes": [],
                "otherOutcomes": [],
            },
        },
        "resultsSection": {},
    }

    # Patch at the module level so the inline import picks it up
    monkeypatch.setattr(api_mod, "fetch_registration", lambda nct_id, use_cache=True: fake_reg_data)

    state = _make_minimal_state(registration_number="NCT00309985")
    result = preliminary_info_node(state)

    assert "RANDOMIZED" in result.get("ctgov_design", "")
    assert "PRIMARY" in result.get("ctgov_description", "")
    assert result.get("ctgov_flow") is not None
```

Note: `_make_minimal_state` is a helper expected to already exist in `tests/test_graph.py`. If it does not, define it to return a `RoB2State`-shaped dict with the minimum fields `preliminary_info_node` requires: `evidence`, `full_text`, `outcome`, `effect_of_interest`, `registration_number`.

Also note: because `preliminary.py` imports `fetch_registration` inside the function body, monkeypatching `rob2_pipeline.registration_api.fetch_registration` (the module attribute) is correct here.

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_graph.py::test_preliminary_node_populates_ctgov_fields -v
```

Expected: FAIL — `ctgov_design` key does not exist in result.

- [ ] **Step 3: Add new state fields to `rob2_pipeline/state.py`**

In the `# === PRELIMINARY INFO ===` section, add three lines after `ctgov_outcomes`:

```python
    ctgov_design: Annotated[str, take_latest]
    ctgov_description: Annotated[str, take_latest]
    ctgov_flow: Annotated[str, take_latest]
```

- [ ] **Step 4: Update `rob2_pipeline/nodes/preliminary.py`**

Find the block that begins `if _nct_id.startswith("NCT"):` and replace it entirely:

```python
    # Fetch registration data from ClinicalTrials.gov
    import os
    from rob2_pipeline.registration_api import (
        extract_description,
        extract_design_info,
        extract_outcomes,
        extract_participant_flow,
        fetch_registration,
        format_description_for_prompt,
        format_design_for_prompt,
        format_flow_for_prompt,
        format_outcomes_for_prompt,
    )

    _nct_id = state.get("registration_number", "")
    _use_cache = os.getenv("ROB2_CTGOV_CACHE", "1") != "0"
    if _nct_id.startswith("NCT"):
        _reg_data = fetch_registration(_nct_id, use_cache=_use_cache)
        if _reg_data:
            _outcomes = extract_outcomes(_reg_data)
            state["ctgov_outcomes"] = format_outcomes_for_prompt(_outcomes)
            state["ctgov_design"] = format_design_for_prompt(extract_design_info(_reg_data))
            state["ctgov_description"] = format_description_for_prompt(extract_description(_reg_data))
            state["ctgov_flow"] = format_flow_for_prompt(extract_participant_flow(_reg_data))
            if _outcomes["secondary"]:
                state["registered_secondary_endpoints"] = "; ".join(_outcomes["secondary"])
            if _outcomes["primary"] and state.get("registered_endpoint") in ("Not reported", "", None):
                state["registered_endpoint"] = "; ".join(_outcomes["primary"])
        else:
            _unavailable = "(ClinicalTrials.gov data not available for this trial)"
            state["ctgov_outcomes"] = _unavailable
            state["ctgov_design"] = _unavailable
            state["ctgov_description"] = _unavailable
            state["ctgov_flow"] = _unavailable
    else:
        _skipped = "(No NCT registration number — ClinicalTrials.gov lookup skipped)"
        state["ctgov_outcomes"] = _skipped
        state["ctgov_design"] = _skipped
        state["ctgov_description"] = _skipped
        state["ctgov_flow"] = _skipped
```

- [ ] **Step 5: Run test to confirm it passes**

```
pytest tests/test_graph.py::test_preliminary_node_populates_ctgov_fields -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```
pytest tests/ -v --tb=short
```

Expected: all previously passing tests still PASS.

- [ ] **Step 7: Commit**

```
git add rob2_pipeline/state.py rob2_pipeline/nodes/preliminary.py
git commit -m "feat: add ctgov_design, ctgov_description, ctgov_flow to state and preliminary node"
```

---

## Task 3: Inject CT.gov design metadata into Domain 1 prompt

**Files:**
- Modify: `rob2_pipeline/prompts.py` (PROMPT_DOMAIN1)
- Modify: `rob2_pipeline/nodes/domain1.py`

- [ ] **Step 1: Write failing test**

```python
def test_prompt_domain1_accepts_ctgov_design():
    from rob2_pipeline.prompts import PROMPT_DOMAIN1
    result = PROMPT_DOMAIN1.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        randomization_text="Patients were randomized.",
        baseline_text="",
        consort_text="",
        ctgov_design="Authoritative ClinicalTrials.gov registry design metadata:\n  Allocation type: RANDOMIZED",
    )
    assert "RANDOMIZED" in result
    assert "registry" in result.lower()
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/ -k "test_prompt_domain1_accepts_ctgov_design" -v
```

Expected: FAIL — `KeyError: 'ctgov_design'`.

- [ ] **Step 3: Update PROMPT_DOMAIN1 in `rob2_pipeline/prompts.py`**

Find:

```
<consort_flow>
{consort_text}
</consort_flow>

Answer Domain 1 signaling questions: Bias arising from the randomization process.
```

Replace with:

```
<consort_flow>
{consort_text}
</consort_flow>

<registry_design_metadata>
{ctgov_design}
</registry_design_metadata>

Answer Domain 1 signaling questions: Bias arising from the randomization process.

If ClinicalTrials.gov design metadata is provided above, treat it as authoritative evidence about the trial's design:
- An allocation type of RANDOMIZED is direct evidence that a random method was used (supports Y or PY for Q1.1 depending on specificity of description).
- Masking = NONE confirms an open-label design (context for assessors, not directly scored in D1).
- Presence of a DMC and a research network lead sponsor (class = NETWORK) is consistent with central randomization infrastructure, which supports PY for Q1.2 when no explicit concealment description appears in the paper text.
Use NI only when both the paper text and registry metadata provide no meaningful basis for a judgment.
```

- [ ] **Step 4: Update `domain1_sq_node` in `rob2_pipeline/nodes/domain1.py`**

```python
    prompt = PROMPT_DOMAIN1.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        randomization_text=rag_contexts.get("d1") or format_evidence(evidence["d1_randomization"]) or format_evidence(evidence["methods"]),
        baseline_text="" if rag_contexts.get("d1") else format_evidence(evidence["baseline_table"]),
        consort_text="" if rag_contexts.get("d1") else format_evidence(evidence["consort_flow"]),
        ctgov_design=state.get("ctgov_design", "(No ClinicalTrials.gov design metadata available)"),
    )
```

- [ ] **Step 5: Run tests**

```
pytest tests/ -v --tb=short
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add rob2_pipeline/prompts.py rob2_pipeline/nodes/domain1.py
git commit -m "feat: inject CT.gov design metadata into Domain 1 prompt"
```

---

## Task 4: Inject CT.gov design metadata into Domain 2 SQ1/2 prompt

**Files:**
- Modify: `rob2_pipeline/prompts.py` (PROMPT_DOMAIN2_SQ12)
- Modify: `rob2_pipeline/nodes/domain2.py`

- [ ] **Step 1: Write failing test**

```python
def test_prompt_domain2_sq12_accepts_ctgov_design():
    from rob2_pipeline.prompts import PROMPT_DOMAIN2_SQ12
    result = PROMPT_DOMAIN2_SQ12.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        blinding_text="Open-label trial.",
        methods_text="",
        ctgov_design="  Masking: NONE (masked parties: not specified)",
    )
    assert "NONE" in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/ -k "test_prompt_domain2_sq12_accepts_ctgov_design" -v
```

Expected: FAIL — `KeyError: 'ctgov_design'`.

- [ ] **Step 3: Update PROMPT_DOMAIN2_SQ12 in `rob2_pipeline/prompts.py`**

Find:

```
<methods_interventions>
{methods_text}
</methods_interventions>

Answer the first two Domain 2 signaling questions
```

Replace with:

```
<methods_interventions>
{methods_text}
</methods_interventions>

<registry_design_metadata>
{ctgov_design}
</registry_design_metadata>

Answer the first two Domain 2 signaling questions
```

After the sentence `Important RoB 2 principle: an open-label trial is not automatically high risk.`, add:

```
If ClinicalTrials.gov design metadata is provided above, use the masking field as authoritative confirmation: masking = NONE confirms participants and carers were aware of their assignment (supports Y for Q2.1 and Q2.2). Masking = DOUBLE or QUADRUPLE supports N or PN.
```

- [ ] **Step 4: Update `domain2_sq12_node` in `rob2_pipeline/nodes/domain2.py`**

```python
    prompt = PROMPT_DOMAIN2_SQ12.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        blinding_text=rag_contexts.get("d2_blinding") or format_evidence(evidence["d2_blinding"]),
        methods_text="" if rag_contexts.get("d2_blinding") else format_evidence(evidence["methods"]),
        ctgov_design=state.get("ctgov_design", "(No ClinicalTrials.gov design metadata available)"),
    )
```

- [ ] **Step 5: Run tests**

```
pytest tests/ -v --tb=short
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add rob2_pipeline/prompts.py rob2_pipeline/nodes/domain2.py
git commit -m "feat: inject CT.gov masking data into Domain 2 SQ1/2 prompt"
```

---

## Task 5: Inject CT.gov participant flow into Domain 3 prompt

**Files:**
- Modify: `rob2_pipeline/prompts.py` (PROMPT_DOMAIN3)
- Modify: `rob2_pipeline/nodes/domain3.py`

- [ ] **Step 1: Write failing test**

```python
def test_prompt_domain3_accepts_ctgov_flow():
    from rob2_pipeline.prompts import PROMPT_DOMAIN3
    result = PROMPT_DOMAIN3.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        n_randomized="790",
        consort_text="",
        missing_data_text="",
        sensitivity_text="",
        ctgov_flow="Participant flow:\n  STARTED: ADT + Docetaxel: 397, ADT Alone: 393",
    )
    assert "397" in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/ -k "test_prompt_domain3_accepts_ctgov_flow" -v
```

Expected: FAIL.

- [ ] **Step 3: Update PROMPT_DOMAIN3 in `rob2_pipeline/prompts.py`**

Find:

```
<sensitivity_analyses>
{sensitivity_text}
</sensitivity_analyses>

Answer Domain 3 signaling questions
```

Replace with:

```
<sensitivity_analyses>
{sensitivity_text}
</sensitivity_analyses>

<registry_participant_flow>
{ctgov_flow}
</registry_participant_flow>

Answer Domain 3 signaling questions
```

After the Q3.1 guidance, add:

```
If ClinicalTrials.gov participant flow data is provided above, use it to calculate arm-level completion and dropout rates as supporting evidence for Q3.1. Registry-posted flow reflects the sponsor's own participant disposition accounting.
```

- [ ] **Step 4: Update `domain3_sq_node` in `rob2_pipeline/nodes/domain3.py`**

```python
    prompt = PROMPT_DOMAIN3.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        n_randomized=state.get("n_randomized", "Not reported"),
        consort_text="" if rag_contexts.get("d3") else format_evidence(evidence["consort_flow"]),
        missing_data_text=missing_data_text,
        sensitivity_text="" if rag_contexts.get("d3") else format_evidence(evidence["d4_outcome_meas"]),
        ctgov_flow=state.get("ctgov_flow", "(No ClinicalTrials.gov participant flow available)"),
    )
```

- [ ] **Step 5: Run tests**

```
pytest tests/ -v --tb=short
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add rob2_pipeline/prompts.py rob2_pipeline/nodes/domain3.py
git commit -m "feat: inject CT.gov participant flow into Domain 3 prompt"
```

---

## Task 6: Inject CT.gov description into Domain 5 prompt

**Files:**
- Modify: `rob2_pipeline/prompts.py` (PROMPT_DOMAIN5)
- Modify: `rob2_pipeline/nodes/domain5.py`

The `detailedDescription` field contains the pre-specified PRIMARY/SECONDARY/TERTIARY objectives — the evidence Q5.1 needs to answer PY instead of PN.

- [ ] **Step 1: Write failing test**

```python
def test_prompt_domain5_accepts_ctgov_description():
    from rob2_pipeline.prompts import PROMPT_DOMAIN5
    result = PROMPT_DOMAIN5.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        numerical_result="HR 0.61",
        registration_number="NCT00309985",
        registered_endpoint="Overall Survival",
        registered_secondary_endpoints="Time to CRPC",
        reported_endpoint="Overall Survival",
        ctgov_outcomes="PRIMARY: Overall Survival",
        ctgov_description="Authoritative ClinicalTrials.gov registry description:\nPRIMARY OBJECTIVE: Overall survival.",
        registration_text="",
        sap_text="",
        results_text="",
    )
    assert "PRIMARY OBJECTIVE" in result
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/ -k "test_prompt_domain5_accepts_ctgov_description" -v
```

Expected: FAIL — `KeyError: 'ctgov_description'`.

- [ ] **Step 3: Update PROMPT_DOMAIN5 in `rob2_pipeline/prompts.py`**

Find the existing `<authoritative_registration_data>` block:

```
<authoritative_registration_data>
{ctgov_outcomes}
</authoritative_registration_data>
```

Replace with:

```
<authoritative_registration_outcomes>
{ctgov_outcomes}
</authoritative_registration_outcomes>

<authoritative_registration_description>
{ctgov_description}
</authoritative_registration_description>
```

After the Q5.1 NI bullet, add:

```
If a ClinicalTrials.gov registry description is provided above and lists PRIMARY, SECONDARY, or TERTIARY objectives, treat these as pre-specified endpoints. A trial with clearly enumerated objectives in the registry description provides strong evidence the analysis plan was pre-specified (supports PY for Q5.1). If the assessed outcome matches a listed primary or secondary objective without amendment, that further supports PY.
```

- [ ] **Step 4: Update `domain5_sq_node` in `rob2_pipeline/nodes/domain5.py`**

```python
    prompt = PROMPT_DOMAIN5.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        numerical_result=state.get("numerical_result", "Not reported"),
        registration_number=state.get("registration_number", "Not reported"),
        registered_endpoint=state.get("registered_endpoint", "Not reported"),
        registered_secondary_endpoints=state.get("registered_secondary_endpoints", "Not reported"),
        reported_endpoint=state.get("outcome", "Not reported"),
        ctgov_outcomes=state.get("ctgov_outcomes", ""),
        ctgov_description=state.get("ctgov_description", "(No ClinicalTrials.gov description available)"),
        registration_text=rag_contexts.get("d5") or format_evidence(evidence["d5_registration"]),
        sap_text="" if rag_contexts.get("d5") else format_evidence(evidence["d4_outcome_meas"]),
        results_text="" if rag_contexts.get("d5") else format_evidence(evidence["results"]),
    )
```

- [ ] **Step 5: Run tests**

```
pytest tests/ -v --tb=short
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add rob2_pipeline/prompts.py rob2_pipeline/nodes/domain5.py
git commit -m "feat: inject CT.gov pre-specified objectives into Domain 5 prompt"
```

---

## Task 7: Expand RAG query sets for D1 and D5

**Files:**
- Modify: `rob2_pipeline/rag_queries.py`

- [ ] **Step 1: Write test**

```python
def test_d1_rag_queries_cover_key_concepts():
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES
    d1 = " ".join(DOMAIN_QUERIES["d1"])
    assert "block" in d1.lower() or "stratif" in d1.lower()
    assert "central" in d1.lower()
    assert "minimi" in d1.lower()


def test_d5_rag_queries_cover_sap_concepts():
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES
    d5 = " ".join(DOMAIN_QUERIES["d5"])
    assert "statistical analysis plan" in d5.lower()
    assert "pre-specified" in d5.lower()
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/ -k "test_d1_rag_queries or test_d5_rag_queries" -v
```

- [ ] **Step 3: Update `rob2_pipeline/rag_queries.py`**

Replace the `"d1"` and `"d5"` entries:

```python
    "d1": [
        "allocation sequence randomization random number concealed envelope",
        "allocation concealment sealed envelope central randomization independent",
        "method of sequence generation block stratified minimization computer generated",
        "central allocation telephone internet randomization service independent pharmacist",
        "baseline characteristics demographics imbalance groups comparable",
        "allocation procedure concealment of treatment assignment randomization procedure",
    ],
    ...
    "d5": [
        "trial registration protocol pre-specified primary outcome analysis plan",
        "ClinicalTrials.gov ISRCTN registered protocol amendment statistical analysis plan",
        "reported outcomes selective reporting pre-planned endpoints",
        "statistical analysis plan SAP finalized pre-specified analysis",
        "primary endpoint pre-specified registered endpoint outcome switching amendment",
        "protocol deviation amendment change outcome definition time point analysis method",
    ],
```

- [ ] **Step 4: Run tests**

```
pytest tests/ -v --tb=short
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add rob2_pipeline/rag_queries.py
git commit -m "feat: expand D1 and D5 RAG query sets with phrasing-diverse variants"
```

---

## Task 8: End-to-end verification

- [ ] **Step 1: Clear stale CT.gov cache for CHAARTED**

```powershell
Remove-Item -Path ".rob2_cache\ctgov\NCT00309985_v1.json" -ErrorAction SilentlyContinue
```

- [ ] **Step 2: Run pipeline on CHAARTED**

```
python run_pipeline.py --trial CHAARTED
```

Inspect `outputs/benchmark/CHAARTED_rob2_report.md`. Expected:
- D1: Low
- D5: Low
- Overall: Low
- Q1.1 answer: Y or PY (not NI)
- Q1.2 answer: Y or PY (not NI)
- Q5.1 answer: PY or Y (not PN)

- [ ] **Step 3: Run full benchmark**

```
python benchmark.py
```

Compare domain-level agreement vs. pre-change baseline. No domain should regress. D1 and D5 should improve.

---

## Verification Checklist

| Check | Command | Expected |
|---|---|---|
| New extractor unit tests | `pytest tests/test_registration_api.py -v` | All PASS |
| Prompt format tests | `pytest tests/ -k "prompt" -v` | All PASS |
| Full test suite | `pytest tests/ --tb=short` | All PASS |
| CHAARTED D1 | Inspect report | Low |
| CHAARTED D5 | Inspect report | Low |
| CHAARTED overall | Inspect report | Low |
| Full benchmark | `python benchmark.py` | No regressions |
