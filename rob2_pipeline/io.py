from pathlib import Path

from rob2_pipeline.constants import DEFAULT_OUTPUT_DIR


def discover_pdf_inputs(input_path: str) -> list[Path]:
    """Return PDF files from a single PDF path or a directory, sorted for stable batch runs."""
    path = Path(input_path)
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Input file is not a PDF: {path}")
        return [path]
    if path.is_dir():
        pdfs = sorted(p for p in path.glob("*.pdf") if p.is_file())
        if not pdfs:
            raise FileNotFoundError(f"No PDF files found in directory: {path}")
        return pdfs
    raise FileNotFoundError(f"Input path does not exist: {path}")


def default_output_dir() -> str:
    return DEFAULT_OUTPUT_DIR
