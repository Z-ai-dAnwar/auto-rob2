from langgraph.graph import END, StateGraph

from rob2_pipeline.nodes.domain1 import domain1_judge_node, domain1_sq_node
from rob2_pipeline.nodes.domain2 import (
    d2_needs_conditional,
    domain2_analysis_node,
    domain2_conditional_node,
    domain2_judge_node,
    domain2_sq12_node,
)
from rob2_pipeline.nodes.domain3 import domain3_judge_node, domain3_sq_node
from rob2_pipeline.nodes.domain4 import domain4_judge_node, domain4_sq_node
from rob2_pipeline.nodes.domain5 import domain5_judge_node, domain5_sq_node
from rob2_pipeline.nodes.ingest import pdf_ingest_node, rct_screener_node, section_parser_node
from rob2_pipeline.nodes.overall import overall_judge_node
from rob2_pipeline.nodes.preliminary import preliminary_info_node
from rob2_pipeline.nodes.reporter import report_formatter_node
from rob2_pipeline.state import RoB2State


def build_rob2_graph():
    g = StateGraph(RoB2State)

    g.add_node("pdf_ingest", pdf_ingest_node)
    g.add_node("rct_screener", rct_screener_node)
    g.add_node("preliminary_info", preliminary_info_node)
    g.add_node("section_parser", section_parser_node)

    g.add_node("domain1_sq", domain1_sq_node)
    g.add_node("domain1_judge", domain1_judge_node)

    g.add_node("domain2_sq12", domain2_sq12_node)
    g.add_node("domain2_conditional", domain2_conditional_node)
    g.add_node("domain2_analysis", domain2_analysis_node)
    g.add_node("domain2_judge", domain2_judge_node)

    g.add_node("domain3_sq", domain3_sq_node)
    g.add_node("domain3_judge", domain3_judge_node)

    g.add_node("domain4_sq", domain4_sq_node)
    g.add_node("domain4_judge", domain4_judge_node)

    g.add_node("domain5_sq", domain5_sq_node)
    g.add_node("domain5_judge", domain5_judge_node)

    g.add_node("overall_judge", overall_judge_node)
    g.add_node("report_formatter", report_formatter_node)

    g.set_entry_point("pdf_ingest")
    g.add_edge("pdf_ingest", "rct_screener")
    g.add_conditional_edges(
        "rct_screener",
        lambda s: "continue" if s["is_rct"] else "stop",
        {"continue": "preliminary_info", "stop": END},
    )
    g.add_edge("preliminary_info", "section_parser")

    # Fan-out shape for future re-enable once rate-limit-safe parallelism is added:
    # for domain_start in ["domain1_sq", "domain2_sq12", "domain3_sq", "domain4_sq", "domain5_sq"]:
    #     g.add_edge("section_parser", domain_start)
    # for judge in ["domain1_judge", "domain2_judge", "domain3_judge", "domain4_judge", "domain5_judge"]:
    #     g.add_edge(judge, "overall_judge")

    g.add_edge("section_parser", "domain1_sq")
    g.add_edge("domain1_sq", "domain1_judge")
    g.add_edge("domain1_judge", "domain2_sq12")

    g.add_conditional_edges(
        "domain2_sq12",
        d2_needs_conditional,
        {"conditional": "domain2_conditional", "analysis": "domain2_analysis"},
    )
    g.add_edge("domain2_conditional", "domain2_analysis")
    g.add_edge("domain2_analysis", "domain2_judge")
    g.add_edge("domain2_judge", "domain3_sq")

    g.add_edge("domain3_sq", "domain3_judge")
    g.add_edge("domain3_judge", "domain4_sq")
    g.add_edge("domain4_sq", "domain4_judge")
    g.add_edge("domain4_judge", "domain5_sq")
    g.add_edge("domain5_sq", "domain5_judge")
    g.add_edge("domain5_judge", "overall_judge")
    g.add_edge("overall_judge", "report_formatter")
    g.add_edge("report_formatter", END)

    return g.compile()
