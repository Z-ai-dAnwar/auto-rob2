import argparse
import os
from pathlib import Path
from pprint import pformat

from rob2_pipeline.config import get_default_effect_of_interest
from rob2_pipeline.debug import summarize_state
from rob2_pipeline.io import (
    default_output_dir,
    discover_pdf_inputs,
    discover_supplements_for_pdf,
)
from rob2_pipeline.pipeline import run_assessment


def main():
    """CLI entrypoint for running RoB 2 assessments."""
    parser = argparse.ArgumentParser(
        description="Run an automated RoB 2 assessment for an RCT PDF."
    )
    parser.add_argument(
        "input", help="Path to a PDF file or directory containing PDF files."
    )
    parser.add_argument(
        "--outcome", default=None, help="Optional specific outcome to assess."
    )
    parser.add_argument(
        "--effect",
        default=get_default_effect_of_interest(),
        help="Effect of interest; defaults to ITT.",
    )
    parser.add_argument(
        "--output-dir",
        default=default_output_dir(),
        help="Directory for Markdown and JSON outputs.",
    )
    parser.add_argument(
        "--supplement",
        action="append",
        default=[],
        help="Supplement PDF path. Can be passed multiple times.",
    )
    parser.add_argument(
        "--supplement-dir",
        default=None,
        help="Directory containing per-trial supplement folders named by primary PDF stem.",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Bypass prompt cache for this run."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print compact debug summary after each run.",
    )
    args = parser.parse_args()

    if args.no_cache:
        os.environ["ROB2_USE_CACHE"] = "0"

    pdf_paths = discover_pdf_inputs(args.input)
    if args.supplement and len(pdf_paths) > 1:
        parser.error(
            "--supplement can only be used with a single PDF input; "
            "use --supplement-dir for directory runs."
        )
    for pdf_path in pdf_paths:
        print(f"Assessing: {pdf_path}")
        supplement_paths = list(args.supplement or [])
        supplement_paths.extend(
            str(path)
            for path in discover_supplements_for_pdf(
                pdf_path, Path(args.supplement_dir) if args.supplement_dir else None
            )
        )
        state = run_assessment(
            pdf_path=str(pdf_path),
            outcome=args.outcome,
            effect_of_interest=args.effect,
            output_dir=args.output_dir,
            supplementary_paths=supplement_paths,
        )
        print(f"Overall judgment: {state.get('overall_judgment') or 'Not assessed'}")
        print(f"Human review priority: {state.get('human_review_priority', 'HIGH')}")
        if state.get("errors"):
            print("Errors:")
            for error in state["errors"]:
                print(f"- {error}")
        if args.debug:
            print("Debug summary:")
            print(pformat(summarize_state(state), sort_dicts=False))


if __name__ == "__main__":
    main()
