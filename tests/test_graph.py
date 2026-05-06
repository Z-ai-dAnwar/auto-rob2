from pathlib import Path
from unittest.mock import patch

import fitz

from rob2_pipeline.graph import build_rob2_graph
from rob2_pipeline.pipeline import run_assessment


def _make_pdf(path: Path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "Abstract",
                "This randomized controlled trial compared Drug A with placebo.",
                "Methods",
                "Participants were randomly assigned using a computer-generated sequence.",
                "Allocation was concealed centrally. The trial used intention-to-treat analysis.",
                "Blinding",
                "Participants and investigators were blinded.",
                "Outcomes",
                "The primary outcome was mortality.",
                "Results",
                "100 participants were randomized and all had outcome data.",
                "Trial registration",
                "ClinicalTrials.gov NCT00000000.",
            ]
        ),
    )
    doc.save(path)
    doc.close()


def _initial_state(pdf_path: str) -> dict:
    return {
        "pdf_path": pdf_path,
        "full_text": "",
        "sections": {},
        "is_rct": False,
        "rct_screen_evidence": "",
        "intervention": "Not reported",
        "comparator": "Not reported",
        "outcome": "",
        "outcome_type": "objective",
        "numerical_result": "Not reported",
        "effect_of_interest": "ITT",
        "registration_number": "Not reported",
        "n_randomized": "Not reported",
        "sources_consulted": [],
        "sq_answers": {},
        "domain_judgments": {},
        "domain_rationales": {},
        "overall_judgment": "",
        "overall_rationale": "",
        "ni_count": 0,
        "high_uncertainty_sqs": [],
        "human_review_priority": "HIGH",
        "markdown_report": "",
        "json_output": {},
        "errors": [],
        "llm_call_log": [],
    }


def _llm_response(*_args, node_name: str = ""):
    responses = {
        "rct_screener": """
        <screening><is_rct>YES</is_rct><evidence>"randomly assigned"</evidence><study_design>RCT</study_design><note></note></screening>
        """,
        "preliminary_info": """
        <preliminary_info>
          <experimental_intervention><value>Drug A</value><quote>"Drug A" (Abstract)</quote></experimental_intervention>
          <comparator_intervention><value>Placebo</value><quote>"placebo" (Abstract)</quote></comparator_intervention>
          <outcome_assessed><value>mortality</value><quote>"mortality" (Outcomes)</quote><is_primary>YES</is_primary></outcome_assessed>
          <outcome_type>objective</outcome_type>
          <numerical_result><value>RR 0.90 (95% CI 0.70-1.10)</value><quote>"RR 0.90" (Results)</quote></numerical_result>
          <n_randomized><value>100</value><quote>"100 participants" (Results)</quote></n_randomized>
          <trial_registration><number>NCT00000000</number><registry>ClinicalTrials.gov</registry><quote>"NCT00000000" (Registration)</quote></trial_registration>
        </preliminary_info>
        """,
        "domain1_sq": """
        <domain1>
          <sq_1_1><answer>Y</answer><quote>"computer-generated sequence" (Methods)</quote><justification>Random sequence stated.</justification></sq_1_1>
          <sq_1_2><answer>Y</answer><quote>"concealed centrally" (Methods)</quote><justification>Central concealment stated.</justification></sq_1_2>
          <sq_1_3><answer>N</answer><quote>"baseline balanced" (Results)</quote><justification>No concerning imbalance.</justification></sq_1_3>
        </domain1>
        """,
        "domain2_sq12": """
        <domain2_part1>
          <sq_2_1><answer>N</answer><quote>"blinded" (Blinding)</quote><justification>Participants were blinded.</justification></sq_2_1>
          <sq_2_2><answer>N</answer><quote>"investigators were blinded" (Blinding)</quote><justification>Personnel were blinded.</justification></sq_2_2>
        </domain2_part1>
        """,
        "domain2_analysis": """
        <domain2_analysis>
          <sq_2_6><answer>Y</answer><quote>"intention-to-treat analysis" (Methods)</quote><justification>ITT analysis was used.</justification></sq_2_6>
          <sq_2_7><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification></sq_2_7>
        </domain2_analysis>
        """,
        "domain3_sq": """
        <domain3>
          <sq_3_1><answer>Y</answer><quote>"all had outcome data" (Results)</quote><completeness_calculation>100/100 = 100%</completeness_calculation><justification>Outcome data were complete.</justification></sq_3_1>
          <sq_3_2><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification></sq_3_2>
          <sq_3_3><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification><uncertainty_flag>NORMAL</uncertainty_flag></sq_3_3>
          <sq_3_4><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification><uncertainty_flag>NORMAL</uncertainty_flag></sq_3_4>
        </domain3>
        """,
        "domain4_sq": """
        <domain4>
          <sq_4_1><answer>N</answer><quote>"mortality" (Outcomes)</quote><justification>Mortality is objective.</justification></sq_4_1>
          <sq_4_2><answer>N</answer><quote>"primary outcome was mortality" (Outcomes)</quote><justification>Same method used.</justification></sq_4_2>
          <sq_4_3><answer>N</answer><auto_set_reason></auto_set_reason><quote>"blinded" (Blinding)</quote><justification>Assessors were blinded.</justification></sq_4_3>
          <sq_4_4><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification></sq_4_4>
          <sq_4_5><answer>NA</answer><quote>Not applicable</quote><justification>Not applicable</justification><uncertainty_flag>NORMAL</uncertainty_flag></sq_4_5>
        </domain4>
        """,
        "domain5_sq": """
        <domain5>
          <sq_5_1><answer>Y</answer><quote>"NCT00000000" (Registration)</quote><justification>Trial was registered.</justification><registration_comparison>No discrepancy.</registration_comparison></sq_5_1>
          <sq_5_2><answer>N</answer><quote>"primary outcome was mortality" (Outcomes)</quote><justification>No selective measurement evident.</justification></sq_5_2>
          <sq_5_3><answer>N</answer><quote>"intention-to-treat analysis" (Methods)</quote><justification>No selective analysis evident.</justification></sq_5_3>
        </domain5>
        """,
    }
    return responses[node_name]


def test_graph_happy_path_with_mocked_llm(tmp_path):
    pdf_path = tmp_path / "trial.pdf"
    _make_pdf(pdf_path)

    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", side_effect=_llm_response
    ) as call_mock:
        state = build_rob2_graph().invoke(_initial_state(str(pdf_path)))

    assert state["overall_judgment"] == "Low"
    assert state["domain_judgments"] == {"D1": "Low", "D2": "Low", "D3": "Low", "D4": "Low", "D5": "Low"}
    assert "__debug_sections" in state
    assert state["__debug_sections"]["methods"]["detected"] is True
    assert "# RoB 2 Assessment" in state["markdown_report"]
    assert len(state["llm_call_log"]) == 8
    assert "domain2_conditional" not in [kwargs.get("node_name") for _, kwargs in call_mock.call_args_list]


def test_graph_stops_for_non_rct(tmp_path):
    pdf_path = tmp_path / "cohort.pdf"
    _make_pdf(pdf_path)

    def non_rct_response(*_args, node_name: str = ""):
        assert node_name == "rct_screener"
        return "<screening><is_rct>NO</is_rct><evidence>cohort</evidence><study_design>Cohort</study_design><note>Use ROBINS-I</note></screening>"

    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", side_effect=non_rct_response
    ):
        state = build_rob2_graph().invoke(_initial_state(str(pdf_path)))

    assert state["is_rct"] is False
    assert state["domain_judgments"] == {}
    assert state["markdown_report"] == ""
    assert state["errors"]


def test_rct_screener_prompt_includes_randomization_context(tmp_path):
    pdf_path = tmp_path / "trial.pdf"
    _make_pdf(pdf_path)
    captured = {}

    def capture_prompt(_llm, messages, node_name: str = ""):
        captured[node_name] = messages[0].content
        return _llm_response(_llm, messages, node_name=node_name)

    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", side_effect=capture_prompt
    ):
        build_rob2_graph().invoke(_initial_state(str(pdf_path)))

    assert "randomized controlled trial" in captured["rct_screener"]
    assert "computer-generated sequence" in captured["rct_screener"]


def test_run_assessment_writes_outputs(tmp_path):
    pdf_path = tmp_path / "trial.pdf"
    output_dir = tmp_path / "outputs"
    _make_pdf(pdf_path)

    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", side_effect=_llm_response
    ):
        state = run_assessment(str(pdf_path), output_dir=str(output_dir))

    assert state["overall_judgment"] == "Low"
    assert (output_dir / "trial_rob2_report.md").exists()
    assert (output_dir / "trial_rob2_data.json").exists()
