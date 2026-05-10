from typing import Any


def label_name(item: Any) -> str:
    label = getattr(item, "label", None)
    return getattr(label, "name", str(label)).upper() if label is not None else ""


def export_table_markdown(item: Any, doc: Any) -> str:
    if hasattr(item, "export_to_markdown"):
        try:
            return (item.export_to_markdown(doc=doc) or "").strip()
        except TypeError:
            return (item.export_to_markdown() or "").strip()
    if hasattr(item, "export_to_dataframe"):
        try:
            return item.export_to_dataframe(doc=doc).to_markdown()
        except TypeError:
            return item.export_to_dataframe().to_markdown()
    return ""
