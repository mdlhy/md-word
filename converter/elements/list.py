"""List element renderer for MD → .docx conversion.

Supports ordered (1. 2. 3.) and unordered (- * +) lists with multi-level
nesting up to 3 levels deep. Uses python-docx built-in list styles
(List Number / List Bullet) with level variants, falling back to manual
indent + numbering when styles are unavailable.
"""

from docx import Document
from docx.shared import Cm

from converter.md_parser import Token


def _extract_text(token: Token) -> str:
    if token.content:
        return token.content
    parts = []
    for child in token.children:
        t = _extract_text(child)
        if t:
            parts.append(t)
    return " ".join(parts)


def add_list_item(
    doc: Document,
    token: Token,
    template_config: dict,
    list_state: dict | None = None,
) -> list:
    """Add a list item from a parsed markdown token.

    Returns list of paragraphs created.
    list_state tracks current numbering across items.
    """
    if list_state is None:
        list_state = {"ordered": None, "counter": [0, 0, 0, 0]}

    results = []

    if token.type == "list":
        is_ordered = token.attrs.get("ordered", False)
        depth = token.attrs.get("depth", 0)
        list_state["ordered"] = is_ordered
        list_state["depth"] = depth
        for child in token.children:
            if child.type == "list_item":
                results.extend(add_list_item(doc, child, template_config, list_state))
        return results

    if token.type == "list_item":
        level = min(list_state.get("depth", 0), 2)  # 0-indexed, max 2 (3 levels)
        is_ordered = list_state.get("ordered", False)

        nested_lists = [c for c in token.children if c.type == "list"]
        non_list_children = [c for c in token.children if c.type != "list"]

        text_parts = []
        for child in non_list_children:
            t = _extract_text(child)
            if t:
                text_parts.append(t)

        text = " ".join(text_parts).strip()
        if not text:
            text = token.content.strip()

        if not text:
            # Still process nested lists even if this item has no text
            for nested in nested_lists:
                list_state_nested = {
                    "ordered": nested.attrs.get("ordered", False),
                    "counter": list_state["counter"],
                    "depth": nested.attrs.get("depth", 0),
                }
                for child in nested.children:
                    if child.type == "list_item":
                        results.extend(
                            add_list_item(doc, child, template_config, list_state_nested)
                        )
            return results

        if is_ordered:
            style_name = ["List Number", "List Number 2", "List Number 3"][level]
        else:
            style_name = ["List Bullet", "List Bullet 2", "List Bullet 3"][level]

        try:
            p = doc.add_paragraph(text, style=style_name)
        except KeyError:
            p = doc.add_paragraph(text)
            p.paragraph_format.left_indent = Cm(1.27 * (level + 1))
            if is_ordered:
                list_state["counter"][level] += 1
                prefixes = [
                    str(list_state["counter"][0]) + ".",
                    chr(ord('a') + list_state["counter"][1] - 1) + ".",
                    chr(ord('i') + list_state["counter"][2] - 1) + ".",
                ]
                p.text = prefixes[level] + " " + text

        results.append(p)

        for nested in nested_lists:
            list_state_nested = {
                "ordered": nested.attrs.get("ordered", False),
                "counter": list_state["counter"],
                "depth": nested.attrs.get("depth", 0),
            }
            for child in nested.children:
                if child.type == "list_item":
                    results.extend(
                        add_list_item(doc, child, template_config, list_state_nested)
                    )

        return results

    return results
