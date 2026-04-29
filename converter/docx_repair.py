"""DOCX repair pipeline: detect and fix formatting issues in .docx files.

Applies template formatting (fonts, sizes, spacing, margins) plus heuristic
detection of structural issues (bare # headings, unstyled lists, etc.).
"""

import re
from docx import Document
from docx.shared import Cm, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

from converter.compat_report import CompatItem, CompatReport, generate_compat_report
from converter.templates import get_template


def repair_docx(input_path: str, template_name: str = "academic") -> tuple[Document, CompatReport]:
    doc = Document(input_path)
    template_config = get_template(template_name)
    items = []

    _apply_page_margins(doc, template_config)
    items.extend(_fix_headings(doc, template_config))
    items.extend(_fix_lists(doc, template_config))
    items.extend(_fix_tables(doc, template_config))
    _apply_body_formatting(doc, template_config)
    items.extend(_fix_formulas(doc))

    report = generate_compat_report(items)
    return doc, report


# ---------------------------------------------------------------------------
# Page margins
# ---------------------------------------------------------------------------

def _apply_page_margins(doc: Document, template_config: dict):
    """Apply template page margins to all sections."""
    page = template_config.get("page", {})
    for section in doc.sections:
        if "margin_top" in page:
            section.top_margin = Cm(page["margin_top"])
        if "margin_bottom" in page:
            section.bottom_margin = Cm(page["margin_bottom"])
        if "margin_left" in page:
            section.left_margin = Cm(page["margin_left"])
        if "margin_right" in page:
            section.right_margin = Cm(page["margin_right"])


# ---------------------------------------------------------------------------
# Body formatting
# ---------------------------------------------------------------------------

def _apply_body_formatting(doc: Document, template_config: dict):
    """Apply template body font/size/spacing to all Normal paragraphs."""
    body_config = template_config.get("body", {})
    if not body_config:
        return

    font_cn = body_config.get("font_cn")
    font_en = body_config.get("font_en")
    font_size = body_config.get("size")
    line_spacing = body_config.get("line_spacing")
    first_indent = body_config.get("first_indent", 0)

    for para in doc.paragraphs:
        # Skip headings — they have their own formatting
        if para.style and para.style.name and para.style.name.startswith("Heading"):
            continue

        for run in para.runs:
            if font_en:
                run.font.name = font_en
                # Set East Asian font via XML
                r_elem = run._element
                rpr = r_elem.find(qn("w:rPr"))
                if rpr is None:
                    rpr = OxmlElement("w:rPr")
                    r_elem.insert(0, rpr)
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.insert(0, rfonts)
                if font_cn:
                    rfonts.set(qn("w:eastAsia"), font_cn)

            if font_size:
                run.font.size = Pt(font_size)

        # Paragraph-level formatting
        if line_spacing:
            pf = para.paragraph_format
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            pf.line_spacing = line_spacing

        if first_indent and first_indent > 0:
            # First line indent in chars → convert to cm (1 char ≈ 0.74 cm for 12pt)
            indent_cm = first_indent * (font_size or 12) * 0.0265
            para.paragraph_format.first_line_indent = Cm(indent_cm)


# ---------------------------------------------------------------------------
# Heading fixes
# ---------------------------------------------------------------------------

def _fix_headings(doc, template_config) -> list[CompatItem]:
    items = []
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$')

    for para in doc.paragraphs:
        if para.style.name != "Normal":
            continue

        text = para.text.strip()
        m = heading_re.match(text)
        if not m:
            continue

        level = min(len(m.group(1)), 3)
        title_text = m.group(2).strip()

        try:
            style_name = f"Heading {level}"
            _ = doc.styles[style_name]
            para.style = doc.styles[style_name]

            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = title_text
            else:
                para.add_run(title_text)

            # Apply template heading formatting
            heading_config = template_config.get(f"heading{level}", {})
            _apply_heading_formatting(para, heading_config)

            items.append(CompatItem(
                element_type="heading",
                risk="low",
                description=f"标题修复: '{text[:30]}' → {style_name}"
            ))
        except KeyError:
            pass

    # Also format existing headings with template styles
    for para in doc.paragraphs:
        if not (para.style and para.style.name and para.style.name.startswith("Heading")):
            continue
        # Extract level from style name
        try:
            level = int(para.style.name.split()[-1])
        except (ValueError, IndexError):
            continue
        if level > 3:
            continue
        heading_config = template_config.get(f"heading{level}", {})
        _apply_heading_formatting(para, heading_config)

    return items


def _apply_heading_formatting(para, heading_config: dict):
    """Apply template heading font/size/bold/center to a heading paragraph."""
    font_cn = heading_config.get("font_cn")
    font_en = heading_config.get("font_en")

    for run in para.runs:
        if font_en:
            run.font.name = font_en
            r_elem = run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r_elem.insert(0, rpr)
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            if font_cn:
                rfonts.set(qn("w:eastAsia"), font_cn)

        if heading_config.get("size"):
            run.font.size = Pt(heading_config["size"])
        if heading_config.get("bold"):
            run.font.bold = True

    if heading_config.get("center"):
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------------------------------------------------------------------------
# List fixes
# ---------------------------------------------------------------------------

def _fix_lists(doc, template_config) -> list[CompatItem]:
    items = []
    ordered_re = re.compile(r'^(\d+)\.\s+(.+)$')
    unordered_re = re.compile(r'^[-*+]\s+(.+)$')

    for para in doc.paragraphs:
        if para.style.name not in ("Normal", "List Number", "List Bullet"):
            continue

        text = para.text.strip()
        m_ord = ordered_re.match(text)
        m_unord = unordered_re.match(text)

        if m_ord:
            item_text = m_ord.group(2)
            try:
                para.style = doc.styles["List Number"]
                for run in para.runs:
                    run.text = ""
                if para.runs:
                    para.runs[0].text = item_text
                else:
                    para.add_run(item_text)
                items.append(CompatItem(
                    element_type="list",
                    risk="low",
                    description=f"列表修复: '{text[:30]}' → List Number"
                ))
            except KeyError:
                pass
        elif m_unord:
            item_text = m_unord.group(1)
            try:
                para.style = doc.styles["List Bullet"]
                for run in para.runs:
                    run.text = ""
                if para.runs:
                    para.runs[0].text = item_text
                else:
                    para.add_run(item_text)
                items.append(CompatItem(
                    element_type="list",
                    risk="low",
                    description=f"列表修复: '{text[:30]}' → List Bullet"
                ))
            except KeyError:
                pass

    return items


# ---------------------------------------------------------------------------
# Table fixes
# ---------------------------------------------------------------------------

def _fix_tables(doc, template_config) -> list[CompatItem]:
    items = []

    page_config = template_config.get("page", {})
    margin_left = page_config.get("margin_left", 3.17)
    margin_right = page_config.get("margin_right", 3.17)
    available_width = 21.0 - margin_left - margin_right

    for table in doc.tables:
        num_cols = len(table.columns)
        if num_cols == 0:
            continue

        col_width = Cm(available_width / num_cols)
        table.autofit = False

        for row in table.rows:
            for cell in row.cells:
                cell.width = col_width

        from converter.elements.table import _set_table_borders
        table_config = template_config.get("table", {})
        three_line = table_config.get("three_line_default", False)
        _set_table_borders(table, three_line=three_line)

        if table.rows:
            for cell in table.rows[0].cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True

        items.append(CompatItem(
            element_type="table",
            risk="low",
            description="表格修复: 固定列宽 + 边框优化"
        ))

    return items


# ---------------------------------------------------------------------------
# Formula fixes
# ---------------------------------------------------------------------------

def _fix_formulas(doc) -> list[CompatItem]:
    items = []
    try:
        from converter.orchestrator import convert_docx_in_memory
        result = convert_docx_in_memory(doc)
        if result.converted > 0:
            items.append(CompatItem(
                element_type="formula",
                risk="low",
                description=f"公式修复: {result.converted} 个公式转换成功"
            ))
        if result.failed > 0:
            items.append(CompatItem(
                element_type="formula",
                risk="high",
                description=f"公式修复: {result.failed} 个公式转换失败"
            ))
    except ImportError:
        for para in doc.paragraphs:
            text = para.text
            if '$' in text and '\\frac' in text:
                items.append(CompatItem(
                    element_type="formula",
                    risk="medium",
                    description=f"检测到未转换公式: '{text[:30]}...'"
                ))

    return items
