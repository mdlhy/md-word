from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

REQUIRED_REFERENCE_STYLES = (
    "Normal",
    "Heading 1",
    "Heading 2",
    "Heading 3",
    "Caption",
    "Table Grid",
    "List Bullet",
    "List Number",
)

RECOMMENDED_REFERENCE_STYLES = (
    "Source Code",
)


def audit_reference_doc(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "ok": False,
            "missing_required": list(REQUIRED_REFERENCE_STYLES),
            "missing_recommended": list(RECOMMENDED_REFERENCE_STYLES),
        }

    doc = Document(str(path))
    style_names = {style.name for style in doc.styles}
    missing_required = [name for name in REQUIRED_REFERENCE_STYLES if name not in style_names]
    missing_recommended = [name for name in RECOMMENDED_REFERENCE_STYLES if name not in style_names]

    return {
        "path": str(path),
        "exists": True,
        "ok": not missing_required,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }


def audit_template_reference_docs() -> dict[str, Any]:
    from converter.templates import list_templates
    from converter.pandoc_driver import reference_doc_path

    items = {}
    for template in list_templates():
        template_id = template["id"]
        items[template_id] = audit_reference_doc(reference_doc_path(template_id))

    return {
        "ok": all(item["ok"] for item in items.values()),
        "items": items,
    }
