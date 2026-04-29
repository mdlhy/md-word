"""MD → DOCX orchestrator.

Ties together markdown parsing, template loading, element converters,
and math OMML generation to produce a styled .docx with compatibility report.
"""

import copy
import logging
import os

import math2docx
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement

from converter.md_parser import Token, parse_markdown
from converter.templates import get_template
from converter.compat_report import CompatItem, CompatReport, assess_formula_risk, assess_image_risk, generate_compat_report
from converter.elements.heading import add_heading
from converter.elements.table import add_table
from converter.elements.list import add_list_item
from converter.elements.blockquote import add_blockquote
from converter.elements.code import add_code_block
from converter.elements.image import add_image

__all__ = ["convert_md_to_docx"]

logger = logging.getLogger(__name__)

NS_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def _clear_document_content(doc: Document):
    body = doc.element.body
    for child in list(body):
        if child.tag.endswith("}p") or child.tag.endswith("}tbl"):
            body.remove(child)
    doc.add_paragraph()


def _add_math_to_paragraph(paragraph, latex: str, display: bool):
    try:
        tmp_doc = Document()
        tmp_p = tmp_doc.add_paragraph()
        math2docx.add_math(tmp_p, latex)

        omath_elements = tmp_p._p.findall(f"{NS_M}oMath")
        if not omath_elements:
            raise ValueError("math2docx produced no oMath element")

        if display:
            omath_para = OxmlElement("m:oMathPara")
            for elem in omath_elements:
                omath_para.append(copy.deepcopy(elem))
            paragraph._p.append(omath_para)
        else:
            for elem in omath_elements:
                paragraph._p.append(copy.deepcopy(elem))
    except Exception:
        logger.warning(f"Math conversion failed for: {latex[:50]}")
        safe_text = latex.encode('utf-8', errors='replace').decode('utf-8')
        safe_text = ''.join(c for c in safe_text if ord(c) >= 32 or c in '\t\n')
        run = paragraph.add_run(safe_text)
        run.font.italic = True


def _add_inline_children(paragraph, children: list[Token], config: dict):
    for child in children:
        if child.type == "text":
            paragraph.add_run(child.content)
        elif child.type == "strong":
            run = paragraph.add_run(child.content)
            run.font.bold = True
        elif child.type == "em":
            run = paragraph.add_run(child.content)
            run.font.italic = True
        elif child.type == "codespan":
            run = paragraph.add_run(child.content)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif child.type == "math":
            _add_math_to_paragraph(
                paragraph, child.content, child.attrs.get("display", False)
            )
        elif child.type == "image":
            add_image(paragraph.part.document, child, config)


def _add_rich_paragraph(doc: Document, token: Token, config: dict):
    p = doc.add_paragraph()
    _add_inline_children(p, token.children, config)
    return p


def _add_thematic_break(doc: Document):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    for edge in ("top", "bottom"):
        el = OxmlElement(f"w:{edge}")
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "single")
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz", "6")
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space", "1")
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color", "CCCCCC")
        pBdr.append(el)
    pPr.append(pBdr)
    return p


def _collect_math_compat(token: Token, items: list[CompatItem]):
    if token.type == "math":
        risk = assess_formula_risk(token.content)
        items.append(CompatItem(
            element_type="formula", risk=risk,
            description=f"Formula: {token.content[:60]}",
        ))
    for child in token.children:
        _collect_math_compat(child, items)


def convert_md_to_docx(
    md_text: str,
    template_name: str = "academic",
    three_line: bool = False,
) -> tuple[Document, CompatReport]:
    """Convert markdown text to a python-docx Document with compatibility report.

    Args:
        md_text: Markdown source text.
        template_name: Template name (academic, homework, report).
        three_line: Force three-line table style.

    Returns:
        (Document, CompatReport) tuple.
    """
    tokens = parse_markdown(md_text)

    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates", f"{template_name}.docx"
    )
    doc = Document(template_path)
    _clear_document_content(doc)

    config = get_template(template_name)
    compat_items: list[CompatItem] = []

    for token in tokens:
        if token.type == "heading":
            add_heading(doc, token, config)

        elif token.type == "table":
            add_table(doc, token, config, three_line)
            compat_items.append(CompatItem(
                element_type="table", risk="low",
                description="Table element (low WPS risk)",
            ))

        elif token.type == "list":
            add_list_item(doc, token, config)

        elif token.type == "blockquote":
            add_blockquote(doc, token, config)

        elif token.type == "code":
            add_code_block(doc, token, config)

        elif token.type == "image":
            add_image(doc, token, config)
            src = token.attrs.get("src", "")
            risk = assess_image_risk(src)
            compat_items.append(CompatItem(
                element_type="image", risk=risk,
                description=f"Image: {src}",
            ))

        elif token.type == "math":
            _add_math_to_paragraph(
                doc.add_paragraph(), token.content, token.attrs.get("display", False)
            )
            risk = assess_formula_risk(token.content)
            compat_items.append(CompatItem(
                element_type="formula", risk=risk,
                description=f"Formula: {token.content[:60]}",
            ))

        elif token.type == "paragraph":
            _collect_math_compat(token, compat_items)
            if token.children:
                _add_rich_paragraph(doc, token, config)
            else:
                doc.add_paragraph(token.content)

        elif token.type == "thematic_break":
            _add_thematic_break(doc)

    report = generate_compat_report(compat_items)
    return doc, report
