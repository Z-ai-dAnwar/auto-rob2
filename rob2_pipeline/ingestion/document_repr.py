from dataclasses import dataclass

from rob2_pipeline.docling_utils import export_table_markdown, label_name


@dataclass
class DocBlock:
    heading: str | None
    level: int
    text: str
    tables: list[str]
    page_start: int


@dataclass
class DocumentRepr:
    blocks: list[DocBlock]
    full_text: str

    def to_prompt_repr(self) -> str:
        parts = []
        for block in self.blocks:
            heading = block.heading or "Document"
            level = max(1, min(block.level or 1, 6))
            section_parts = [f"{'#' * level} {heading}"]
            if block.text.strip():
                section_parts.append(block.text.strip())
            for table in block.tables:
                if table.strip():
                    section_parts.append(f"[TABLE]\n{table.strip()}\n[/TABLE]")
            parts.append("\n\n".join(section_parts))
        return "\n\n".join(parts) if parts else self.full_text


def _page_no(item) -> int:
    prov = getattr(item, "prov", None) or []
    if prov:
        return int(getattr(prov[0], "page_no", 0) or 0)
    return 0


def _export_doc_markdown(doc) -> str:
    if hasattr(doc, "export_to_markdown"):
        return (doc.export_to_markdown() or "").strip()
    if hasattr(doc, "export_to_text"):
        return (doc.export_to_text() or "").strip()
    return ""


def build_document_repr(doc) -> DocumentRepr:
    blocks: list[DocBlock] = []
    current_heading: str | None = None
    current_level = 0
    current_text: list[str] = []
    current_tables: list[str] = []
    current_page = 0

    def flush() -> None:
        nonlocal current_text, current_tables, current_page
        text = "\n".join(part for part in current_text if part).strip()
        if text or current_tables:
            blocks.append(
                DocBlock(
                    heading=current_heading,
                    level=current_level,
                    text=text,
                    tables=list(current_tables),
                    page_start=current_page,
                )
            )
        current_text = []
        current_tables = []
        current_page = 0

    iterator = doc.iterate_items() if hasattr(doc, "iterate_items") else []
    for item, level in iterator:
        item_label_name = label_name(item)
        item_text = (getattr(item, "text", "") or "").strip()
        if item_label_name == "SECTION_HEADER":
            flush()
            current_heading = item_text or None
            current_level = int(level or 1)
            current_page = _page_no(item)
            continue
        if not current_page:
            current_page = _page_no(item)
        if item_label_name == "TABLE":
            table = export_table_markdown(item, doc)
            if table:
                current_tables.append(table)
            continue
        if (
            item_label_name
            in {"TEXT", "PARAGRAPH", "LIST_ITEM", "TITLE", "CAPTION", "FOOTNOTE"}
            and item_text
        ):
            current_text.append(item_text)

    flush()
    return DocumentRepr(blocks=blocks, full_text=_export_doc_markdown(doc))
