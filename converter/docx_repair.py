import re
from docx import Document
from docx.shared import Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH

from converter.compat_report import CompatItem, CompatReport, generate_compat_report
from converter.templates import get_template


def repair_docx(input_path: str, template_name: str = "academic") -> tuple[Document, CompatReport]:
    doc = Document(input_path)
    template_config = get_template(template_name)
    items = []

    items.extend(_fix_headings(doc, template_config))
    items.extend(_fix_lists(doc, template_config))
    items.extend(_fix_tables(doc, template_config))
    items.extend(_fix_formulas(doc))

    report = generate_compat_report(items)
    return doc, report


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

            heading_config = template_config.get(f"heading{level}", {})
            if heading_config.get("center"):
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            items.append(CompatItem(
                element_type="heading",
                risk="low",
                description=f"标题修复: '{text[:30]}' → {style_name}"
            ))
        except KeyError:
            pass

    return items


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
