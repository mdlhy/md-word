from __future__ import annotations

from typing import Any

from .parser import parse_math_spans


def convert_paste_text(text: str) -> dict[str, Any]:
    """Convert pasted Markdown/LaTeX snippets into WPS-friendly formula code."""
    if text is None:
        text = ""

    stripped, formula_count = _strip_math_delimiters(text)
    output, remaining_dollars_removed = _remove_remaining_dollars(stripped)
    dollars_removed = max(text.count("$") - output.count("$"), remaining_dollars_removed)

    return {
        "text": output,
        "stats": {
            "formula_count": formula_count,
            "dollars_removed": dollars_removed,
            "remaining_dollars_removed": remaining_dollars_removed,
            "input_chars": len(text),
            "output_chars": len(output),
        },
    }


def _strip_math_delimiters(text: str) -> tuple[str, int]:
    spans = parse_math_spans(text)
    if not spans:
        return text, 0

    parts: list[str] = []
    last = 0

    for span in spans:
        if span.start < last:
            continue
        parts.append(text[last:span.start])
        content = span.content.strip() if span.display else span.content.strip()
        parts.append(content)
        last = span.end

    parts.append(text[last:])
    return "".join(parts), len(spans)


def _remove_remaining_dollars(text: str) -> tuple[str, int]:
    parts: list[str] = []
    removed = 0
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and text[i + 1] == "$":
            removed += 1
            i += 2
            continue
        if ch == "$":
            removed += 1
            i += 1
            continue
        parts.append(ch)
        i += 1

    return "".join(parts), removed
