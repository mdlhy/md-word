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
from docx.oxml.ns import qn

from converter.md_parser import Token, parse_markdown
from converter.templates import get_template
from converter.compat_report import CompatItem, CompatReport, assess_formula_risk, assess_image_risk, generate_compat_report
from converter.elements.heading import add_heading
from converter.elements.table import add_table
from converter.elements.list import add_list_item
from converter.elements.blockquote import add_blockquote
from converter.elements.code import add_code_block
from converter.elements.image import add_image
from converter.format_units import to_pt
from converter.numbering import process_heading_numbering
from converter.elements.special_sections import (
    is_abstract_heading, is_references_heading, is_keywords_paragraph,
    format_abstract_heading, format_abstract_content, format_keywords_paragraph,
    format_references_heading, format_reference_entry,
)
from converter.elements.caption import add_figure_caption, add_table_caption

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
            text = child.content or "".join(
                c.content for c in child.children if c.type == "text"
            )
            run = paragraph.add_run(text)
            run.font.bold = True
        elif child.type == "em":
            text = child.content or "".join(
                c.content for c in child.children if c.type == "text"
            )
            run = paragraph.add_run(text)
            run.font.italic = True
        elif child.type == "codespan":
            run = paragraph.add_run(child.content)
            run.font.name = "Consolas"
            code_config = config.get("code", {})
            run.font.size = to_pt(code_config.get("size", "五号"))
        elif child.type == "math":
            _add_math_to_paragraph(
                paragraph, child.content, child.attrs.get("display", False)
            )
        elif child.type == "image":
            add_image(paragraph.part.document, child, config)
            alt_text = child.attrs.get("alt", "")
            if alt_text:
                add_figure_caption(paragraph.part.document, alt_text, config)


def _add_rich_paragraph(doc: Document, token: Token, config: dict):
    p = doc.add_paragraph()
    _add_inline_children(p, token.children, config)
    _apply_body_format(p, config)
    return p


def _apply_body_format(paragraph, config: dict):
    body_cfg = config.get("body", {})
    if not body_cfg:
        return

    for run in paragraph.runs:
        if body_cfg.get("font_cn"):
            run.font.name = body_cfg.get("font_en", "Times New Roman")
            r_elem = run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r_elem.insert(0, rpr)
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            rfonts.set(qn("w:eastAsia"), body_cfg["font_cn"])
        if body_cfg.get("size"):
            run.font.size = to_pt(body_cfg["size"])

    if body_cfg.get("line_spacing"):
        from converter.format_units import to_spacing
        spacing = to_spacing(body_cfg["line_spacing"])
        paragraph.paragraph_format.line_spacing = spacing

    if body_cfg.get("first_indent"):
        from converter.format_units import to_length, font_size_to_pt
        body_size_pt = font_size_to_pt(body_cfg.get("size", "小四"))
        indent = to_length(body_cfg["first_indent"], font_size_pt=body_size_pt)
        paragraph.paragraph_format.first_line_indent = indent

    from converter.format_units import to_alignment
    alignment = to_alignment(body_cfg.get("alignment", "两端对齐"))
    if alignment is not None:
        paragraph.alignment = alignment


_TOC_HEADING_RE = __import__("re").compile(
    r"^(目录|Table\s+of\s+Contents|Contents|TOC)$", __import__("re").IGNORECASE
)


def _is_toc_heading(text: str) -> bool:
    return bool(_TOC_HEADING_RE.match(text.strip()))


def _add_toc_field(doc: Document):
    """Insert a TOC field paragraph that generates a table of contents in Word."""
    p = doc.add_paragraph()

    run_begin = p.add_run()
    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    run_begin._element.append(fldChar_begin)

    run_instr = p.add_run()
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    run_instr._element.append(instrText)

    run_sep = p.add_run()
    fldChar_sep = OxmlElement("w:fldChar")
    fldChar_sep.set(qn("w:fldCharType"), "separate")
    run_sep._element.append(fldChar_sep)

    placeholder = p.add_run("请更新目录：右键 → 更新域")
    placeholder.font.color.rgb = None

    run_end = p.add_run()
    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")
    run_end._element.append(fldChar_end)

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


def _apply_header_footer(doc: Document, config: dict):
    """Apply header (thesis title) and footer (page number) to all sections."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    header_cfg = config.get("header", {})
    footer_cfg = config.get("footer", {})

    first_h1_text = ""
    for p in doc.paragraphs:
        if p.style.name == "Heading 1":
            first_h1_text = p.text.strip()
            break

    for section in doc.sections:
        if header_cfg.get("text") or first_h1_text:
            header = section.header
            header.is_linked_to_previous = False
            hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hp.text = header_cfg.get("text") or first_h1_text
            header_size = to_pt(header_cfg.get("size", "小五"))
            for run in hp.runs:
                run.font.size = header_size
                run.font.name = "Times New Roman"
                r_elem = run._element
                rpr = r_elem.find(qn("w:rPr"))
                if rpr is None:
                    rpr = OxmlElement("w:rPr")
                    r_elem.insert(0, rpr)
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.insert(0, rfonts)
                rfonts.set(qn("w:eastAsia"), header_cfg.get("font_cn", "宋体"))

        if footer_cfg.get("page_number", True):
            footer = section.footer
            footer.is_linked_to_previous = False
            fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

            footer_size = to_pt(footer_cfg.get("size", "小五"))
            run = fp.add_run()
            run.font.size = footer_size

            fldChar_begin = OxmlElement("w:fldChar")
            fldChar_begin.set(qn("w:fldCharType"), "begin")
            run._element.append(fldChar_begin)

            instr_run = fp.add_run()
            instr_run.font.size = footer_size
            instrText = OxmlElement("w:instrText")
            instrText.set(qn("xml:space"), "preserve")
            instrText.text = " PAGE "
            instr_run._element.append(instrText)

            end_run = fp.add_run()
            end_run.font.size = footer_size
            fldChar_end = OxmlElement("w:fldChar")
            fldChar_end.set(qn("w:fldCharType"), "end")
            end_run._element.append(fldChar_end)


def _apply_title_author(doc: Document, config: dict, heading_paragraphs: list):
    """Apply title/author styles for templates that define them (e.g. dialectics).

    Detects the first H1 as title, the bold paragraph immediately after as author.
    Only applies if the template has 'title' and/or 'author' config blocks.
    """
    title_cfg = config.get("title")
    author_cfg = config.get("author")
    if not title_cfg and not author_cfg:
        return

    if not heading_paragraphs:
        return

    first_level, first_para = heading_paragraphs[0]
    if first_level != 1:
        return

    if title_cfg:
        for run in first_para.runs:
            if title_cfg.get("font_cn"):
                run.font.name = title_cfg.get("font_en", "Times New Roman")
                r_elem = run._element
                rpr = r_elem.find(qn("w:rPr"))
                if rpr is None:
                    rpr = OxmlElement("w:rPr")
                    r_elem.insert(0, rpr)
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.insert(0, rfonts)
                rfonts.set(qn("w:eastAsia"), title_cfg["font_cn"])
            if title_cfg.get("size"):
                run.font.size = to_pt(title_cfg["size"])
            run.font.bold = False
        from converter.format_units import to_alignment
        alignment = to_alignment(title_cfg.get("alignment", "居中对齐"))
        if alignment is not None:
            first_para.alignment = alignment

    if author_cfg:
        body = doc.element.body
        first_para_elem = first_para._element
        next_elem = first_para_elem.getnext()
        if next_elem is not None:
            for para in doc.paragraphs:
                if para._element is next_elem and para.runs:
                    all_bold = all(r.font.bold for r in para.runs if r.text.strip())
                    if all_bold:
                        for run in para.runs:
                            if author_cfg.get("font_cn"):
                                run.font.name = author_cfg.get("font_en", "Times New Roman")
                                r_elem = run._element
                                rpr = r_elem.find(qn("w:rPr"))
                                if rpr is None:
                                    rpr = OxmlElement("w:rPr")
                                    r_elem.insert(0, rpr)
                                rfonts = rpr.find(qn("w:rFonts"))
                                if rfonts is None:
                                    rfonts = OxmlElement("w:rFonts")
                                    rpr.insert(0, rfonts)
                                rfonts.set(qn("w:eastAsia"), author_cfg["font_cn"])
                            if author_cfg.get("size"):
                                run.font.size = to_pt(author_cfg["size"])
                            run.font.bold = False
                        from converter.format_units import to_alignment
                        alignment = to_alignment(author_cfg.get("alignment", "居中对齐"))
                        if alignment is not None:
                            para.alignment = alignment
                    break


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
    heading_paragraphs: list[tuple[int, object]] = []
    section_state = {"in_abstract": False, "in_references": False}

    for token in tokens:
        if token.type == "heading":
            heading_text = token.content.strip()
            if not heading_text and token.children:
                heading_text = " ".join(
                    c.content for c in token.children if c.type == "text"
                ).strip()

            if _is_toc_heading(heading_text):
                section_state["in_abstract"] = False
                section_state["in_references"] = False
                _add_toc_field(doc)
                continue

            p = add_heading(doc, token, config)
            level = token.attrs.get("level", token.level) or 1
            if level > 3:
                level = 3

            if is_abstract_heading(heading_text):
                section_state["in_abstract"] = True
                section_state["in_references"] = False
                format_abstract_heading(p, config)
            elif is_references_heading(heading_text):
                section_state["in_references"] = True
                section_state["in_abstract"] = False
                format_references_heading(p, config)
            else:
                section_state["in_abstract"] = False
                section_state["in_references"] = False
                heading_paragraphs.append((level, p))

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
            alt_text = token.attrs.get("alt", "") or token.content
            if alt_text:
                add_figure_caption(doc, alt_text, config)
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
                p = _add_rich_paragraph(doc, token, config)
            else:
                p = doc.add_paragraph(token.content)
                _apply_body_format(p, config)

            if section_state["in_abstract"]:
                para_text = p.text.strip()
                if is_keywords_paragraph(para_text):
                    format_keywords_paragraph(p, config)
                else:
                    format_abstract_content(p, config)
            elif section_state["in_references"]:
                format_reference_entry(p, config)

        elif token.type == "thematic_break":
            _add_thematic_break(doc)

    process_heading_numbering(doc, config, heading_paragraphs)
    _apply_title_author(doc, config, heading_paragraphs)
    _apply_header_footer(doc, config)

    report = generate_compat_report(compat_items)
    return doc, report
