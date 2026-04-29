"""Markdown parser using mistune v3 with custom math plugin.

Parses markdown into a structured Token list, with proper handling of
LaTeX math delimiters and currency disambiguation for $ symbols.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Match

import mistune
from mistune import BlockParser, BlockState, InlineParser, InlineState, Markdown

__all__ = ["Token", "parse_markdown"]


@dataclass
class Token:
    """Structured representation of a markdown element."""

    type: str  # heading, paragraph, table, list, blockquote, code, image, math, text, strong, em, codespan, thematic_break, list_item
    content: str = ""
    level: int = 0
    children: list["Token"] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)


_CURRENCY_RE = re.compile(r"^\d[\d,.\s]*[a-zA-Z]?$")


def _is_likely_currency(content: str) -> bool:
    """Return True if the content between $ delimiters looks like currency."""
    stripped = content.strip()
    if not stripped:
        return False
    return bool(_CURRENCY_RE.match(stripped))


def _is_preceded_by_digit(text: str, pos: int) -> bool:
    """Check if the character at *pos* is immediately preceded by a digit."""
    return pos > 0 and text[pos - 1].isdigit()


def _is_followed_by_currency_char(text: str, pos: int) -> bool:
    """Check if the character at *pos* is followed by a digit, space, comma, or period."""
    if pos + 1 >= len(text):
        return False
    nxt = text[pos + 1]
    return nxt.isdigit() or nxt in (" ", ",", ".")


_BLOCK_DOLLAR_PATTERN = r"^ {0,3}\$\$[ \t]*\n(?P<block_math_text>[\s\S]+?)\n\$\$[ \t]*$"
_BLOCK_BRACKET_PATTERN = r"^ {0,3}\\\[[ \t]*\n(?P<block_math_bracket_text>[\s\S]+?)\n\\[][ \t]*$"

_INLINE_DOUBLE_DOLLAR_PATTERN = r"(?<!\\)\$\$(?P<inline_math_dd_text>[\s\S]+?)\$\$"
_INLINE_DOLLAR_PATTERN = r"(?<!\\)\$(?!\s)(?P<inline_math_text>.+?)(?<!\s)\$"
_INLINE_PAREN_PATTERN = r"\\\((?P<inline_math_paren_text>.+?)\\\)"
_INLINE_BRACKET_PATTERN = r"\\\[(?P<inline_math_bracket_text>.+?)\\\]"


def _parse_block_math_dollar(block: BlockParser, m: Match[str], state: BlockState) -> int:
    text = m.group("block_math_text")
    state.append_token({"type": "block_math", "raw": text, "attrs": {"display": True}})
    return m.end() + 1


def _parse_block_math_bracket(block: BlockParser, m: Match[str], state: BlockState) -> int:
    text = m.group("block_math_bracket_text")
    state.append_token({"type": "block_math", "raw": text, "attrs": {"display": True}})
    return m.end() + 1


def _parse_inline_math_double_dollar(inline: InlineParser, m: Match[str], state: InlineState) -> int:
    text = m.group("inline_math_dd_text")
    state.append_token({"type": "inline_math", "raw": text, "attrs": {"display": True}})
    return m.end()


def _parse_inline_math_dollar(inline: InlineParser, m: Match[str], state: InlineState) -> int | None:
    text = m.group("inline_math_text")
    match_start = m.start()

    src = state.src
    if _is_preceded_by_digit(src, match_start) and _is_followed_by_currency_char(src, m.end() - 1):
        return None

    if _is_likely_currency(text):
        return None

    # Also reject if opening $ is followed directly by a digit (e.g. $5)
    if match_start + 1 < len(src) and src[match_start + 1].isdigit():
        return None

    state.append_token({"type": "inline_math", "raw": text, "attrs": {"display": False}})
    return m.end()


def _parse_inline_math_paren(inline: InlineParser, m: Match[str], state: InlineState) -> int:
    text = m.group("inline_math_paren_text")
    state.append_token({"type": "inline_math", "raw": text, "attrs": {"display": False}})
    return m.end()


def _parse_inline_math_bracket(inline: InlineParser, m: Match[str], state: InlineState) -> int:
    text = m.group("inline_math_bracket_text")
    state.append_token({"type": "inline_math", "raw": text, "attrs": {"display": True}})
    return m.end()


def plugin_math(md: Markdown) -> None:
    md.block.register("block_math_dollar", _BLOCK_DOLLAR_PATTERN, _parse_block_math_dollar, before="list")
    md.block.register("block_math_bracket", _BLOCK_BRACKET_PATTERN, _parse_block_math_bracket, before="list")

    # \(...\) and \[...\] must precede escape rule, which also matches \(
    md.inline.register("inline_math_paren", _INLINE_PAREN_PATTERN, _parse_inline_math_paren, before="escape")
    md.inline.register("inline_math_bracket", _INLINE_BRACKET_PATTERN, _parse_inline_math_bracket, before="escape")
    # $$ must appear before $ in rules so double-dollar matches first
    md.inline.register("inline_math_dollar", _INLINE_DOLLAR_PATTERN, _parse_inline_math_dollar, before="link")
    md.inline.register("inline_math_dd", _INLINE_DOUBLE_DOLLAR_PATTERN, _parse_inline_math_double_dollar, before="inline_math_dollar")

    md.block.insert_rule(md.block.block_quote_rules, "block_math_dollar", before="list")
    md.block.insert_rule(md.block.block_quote_rules, "block_math_bracket", before="list")
    md.block.insert_rule(md.block.list_rules, "block_math_dollar", before="list")
    md.block.insert_rule(md.block.list_rules, "block_math_bracket", before="list")


# ---------------------------------------------------------------------------
# AST → Token converter
# ---------------------------------------------------------------------------

_SKIP_TYPES = frozenset({"blank_line"})


def _convert_node(node: dict[str, Any]) -> Token | None:
    """Recursively convert a mistune AST dict to a Token."""

    ntype = node.get("type", "")

    if ntype in _SKIP_TYPES:
        return None

    token_type = _map_type(ntype, node)
    attrs: dict[str, Any] = dict(node.get("attrs") or {})
    content = ""
    children: list[Token] = []

    if ntype == "heading":
        attrs["level"] = (node.get("attrs") or {}).get("level", 1)

    elif ntype == "list":
        a = node.get("attrs") or {}
        attrs["ordered"] = a.get("ordered", False)
        if "start" in a:
            attrs["start"] = a["start"]

    elif ntype in ("block_math", "inline_math"):
        token_type = "math"
        a = node.get("attrs") or {}
        attrs["display"] = a.get("display", False)
        content = node.get("raw", "")

    elif ntype == "block_code":
        token_type = "code"
        content = node.get("raw", "")
        a = node.get("attrs") or {}
        if a.get("info"):
            attrs["lang"] = a["info"]
        attrs.pop("info", None)

    elif ntype == "codespan":
        content = node.get("raw", "")

    elif ntype == "image":
        a = node.get("attrs") or {}
        if a.get("url"):
            attrs["src"] = a["url"]

    elif ntype == "block_quote":
        token_type = "blockquote"

    raw_children = node.get("children") or []
    for child in raw_children:
        tok = _convert_node(child)
        if tok is not None:
            children.append(tok)

    if ntype == "text":
        content = node.get("raw", "")

    if not children and not content and "raw" in node and ntype not in ("block_code", "block_math", "inline_math"):
        content = node.get("raw", "")

    level = attrs.pop("level", 0) if "level" in attrs else 0
    if ntype == "heading":
        attrs["level"] = (node.get("attrs") or {}).get("level", 1)

    return Token(type=token_type, content=content, level=level, children=children, attrs=attrs)


_TYPE_MAP: dict[str, str] = {
    "heading": "heading",
    "paragraph": "paragraph",
    "table": "table",
    "list": "list",
    "list_item": "list_item",
    "block_quote": "blockquote",
    "block_code": "code",
    "image": "image",
    "text": "text",
    "strong": "strong",
    "emphasis": "em",
    "codespan": "codespan",
    "thematic_break": "thematic_break",
    "inline_math": "math",
    "block_math": "math",
    "table_head": "table_head",
    "table_body": "table_body",
    "table_row": "table_row",
    "table_cell": "table_cell",
    "block_text": "text",
}


def _map_type(ntype: str, node: dict[str, Any]) -> str:
    return _TYPE_MAP.get(ntype, ntype)


def parse_markdown(md_text: str) -> list[Token]:
    """Parse markdown text into a list of Token objects.

    Supports standard markdown plus LaTeX math ($...$, $$...$$, \\(...\\), \\[...\\])
    with currency disambiguation for $ symbols.
    """
    md = mistune.create_markdown(renderer="ast", plugins=["table", plugin_math])
    ast: list[dict[str, Any]] = md(md_text)

    tokens: list[Token] = []
    for node in ast:
        tok = _convert_node(node)
        if tok is not None:
            tokens.append(tok)
    return tokens
