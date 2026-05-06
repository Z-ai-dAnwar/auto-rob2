import argparse

from rob2_pipeline.io import default_output_dir, discover_pdf_inputs
from rob2_pipeline.pipeline import run_assessment


def main():
    parser = argparse.ArgumentParser(description="Run an automated RoB 2 assessment for an RCT PDF.")
    parser.add_argument("input", help="Path to a PDF file or directory containing PDF files.")
    parser.add_argument("--outcome", default=None, help="Optional specific outcome to assess.")
    parser.add_argument("--effect", default="ITT", help="Effect of interest; defaults to ITT.")
    parser.add_argument("--output-dir", default=default_output_dir(), help="Directory for Markdown and JSON outputs.")
    args = parser.parse_args()

    pdf_paths = discover_pdf_inputs(args.input)
    for pdf_path in pdf_paths:
        print(f"Assessing: {pdf_path}")
        state = run_assessment(
            pdf_path=str(pdf_path),
            outcome=args.outcome,
            effect_of_interest=args.effect,
            output_dir=args.output_dir,
        )
        print(f"Overall judgment: {state.get('overall_judgment') or 'Not assessed'}")
        print(f"Human review priority: {state.get('human_review_priority', 'HIGH')}")
        if state.get("errors"):
            print("Errors:")
            for error in state["errors"]:
                print(f"- {error}")


if __name__ == "__main__":
    main()
