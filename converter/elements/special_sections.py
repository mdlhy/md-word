"""Special academic section formatting: abstract, keywords, references.

Detects special sections by heading text matching and applies
appropriate formatting per template config.

Detection rules:
  - Abstract: heading text matches '摘要' or 'Abstract' (case-insensitive)
  - Keywords: paragraph starting with '关键词：' or '关键词:' (bold label)
  - References: heading text matches '参考文献' or 'References'

Called from md_converter during the main token loop.
"""

from __future__ import annotations

import re

from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH

from converter.format_units import to_pt, to_alignment, to_length, font_size_to_pt

_ABSTRACT_HEADING_RE = re.compile(r"^(摘要|Abstract|ABSTRACT)$", re.IGNORECASE)
_REFERENCES_HEADING_RE = re.compile(r"^(参考文献|References|REFERENCES|Bibliography)$", re.IGNORECASE)
_KEYWORDS_LABEL_RE = re.compile(r"^(关键词|关键字|Keywords|Key\s*words)\s*[：:]\s*")


def is_abstract_heading(text: str) -> bool:
    """Check if heading text matches abstract section."""
    return bool(_ABSTRACT_HEADING_RE.match(text.strip()))


def is_references_heading(text: str) -> bool:
    """Check if heading text matches references section."""
    return bool(_REFERENCES_HEADING_RE.match(text.strip()))


def is_keywords_paragraph(text: str) -> bool:
    """Check if paragraph text starts with keywords label."""
    return bool(_KEYWORDS_LABEL_RE.match(text.strip()))


def format_abstract_heading(paragraph, config: dict):
    """Format abstract heading: centered, bold, title font/size."""
    abstract_cfg = config.get("abstract", {})
    for run in paragraph.runs:
        if abstract_cfg.get("title_font_cn"):
            run.font.name = abstract_cfg.get("title_font_en", "Times New Roman")
            r_elem = run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r_elem.insert(0, rpr)
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            rfonts.set(qn("w:eastAsia"), abstract_cfg["title_font_cn"])
        if abstract_cfg.get("title_size"):
            run.font.size = to_pt(abstract_cfg["title_size"])
        run.font.bold = True
        run.font.color.rgb = None

    alignment = to_alignment(abstract_cfg.get("title_alignment", "居中对齐"))
    if alignment is not None:
        paragraph.alignment = alignment


def format_abstract_content(paragraph, config: dict):
    """Format abstract body paragraph: smaller font, body alignment."""
    abstract_cfg = config.get("abstract", {})
    content_size = abstract_cfg.get("content_size", "小四")
    for run in paragraph.runs:
        run.font.size = to_pt(content_size)

    body_cfg = config.get("body", {})
    alignment = to_alignment(body_cfg.get("alignment", "两端对齐"))
    if alignment is not None:
        paragraph.alignment = alignment


def format_keywords_paragraph(paragraph, config: dict):
    """Format keywords paragraph: bold label + normal content, specific font.

    Input pattern: '关键词：A；B；C' where label may be bold in markdown.
    After parsing, the paragraph may have:
      - Single run with full text (plain markdown)
      - Multiple runs with bold label + normal content (rich markdown)
    """
    kw_cfg = config.get("keywords", {})
    body_cfg = config.get("body", {})
    content_size = to_pt(kw_cfg.get("content_size", "小四"))
    label_size = to_pt(kw_cfg.get("label_size", "小四"))

    full_text = paragraph.text
    match = _KEYWORDS_LABEL_RE.match(full_text)

    if match and len(paragraph.runs) == 1:
        run = paragraph.runs[0]
        label_end = match.end()
        label_text = full_text[:label_end]
        content_text = full_text[label_end:]

        run.text = ""
        label_run = paragraph.add_run(label_text)
        label_run.font.bold = True
        label_run.font.size = label_size
        if kw_cfg.get("label_font_cn"):
            label_run.font.name = kw_cfg.get("label_font_en", "Times New Roman")
            r_elem = label_run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r_elem.insert(0, rpr)
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            rfonts.set(qn("w:eastAsia"), kw_cfg["label_font_cn"])

        content_run = paragraph.add_run(content_text)
        content_run.font.size = content_size
    else:
        for i, run in enumerate(paragraph.runs):
            run.font.size = content_size
            if i == 0 and run.font.bold:
                if kw_cfg.get("label_font_cn"):
                    run.font.name = kw_cfg.get("label_font_en", "Times New Roman")
                    r_elem = run._element
                    rpr = r_elem.find(qn("w:rPr"))
                    if rpr is None:
                        rpr = OxmlElement("w:rPr")
                        r_elem.insert(0, rpr)
                    rfonts = rpr.find(qn("w:rFonts"))
                    if rfonts is None:
                        rfonts = OxmlElement("w:rFonts")
                        rpr.insert(0, rfonts)
                    rfonts.set(qn("w:eastAsia"), kw_cfg["label_font_cn"])
                run.font.size = label_size

    alignment = to_alignment(body_cfg.get("alignment", "两端对齐"))
    if alignment is not None:
        paragraph.alignment = alignment


def format_references_heading(paragraph, config: dict):
    """Format references heading: centered, bold, title font/size."""
    ref_cfg = config.get("references", {})
    for run in paragraph.runs:
        if ref_cfg.get("title_font_cn"):
            run.font.name = ref_cfg.get("title_font_en", "Times New Roman")
            r_elem = run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r_elem.insert(0, rpr)
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            rfonts.set(qn("w:eastAsia"), ref_cfg["title_font_cn"])
        if ref_cfg.get("title_size"):
            run.font.size = to_pt(ref_cfg["title_size"])
        run.font.bold = True
        run.font.color.rgb = None

    alignment = to_alignment(ref_cfg.get("title_alignment", "居中对齐"))
    if alignment is not None:
        paragraph.alignment = alignment


def format_reference_entry(paragraph, config: dict):
    """Format a single reference entry: small font + hanging indent."""
    ref_cfg = config.get("references", {})
    entry_size = ref_cfg.get("entry_size", "五号")
    hanging_indent = ref_cfg.get("entry_hanging_indent", "2字符")

    for run in paragraph.runs:
        run.font.size = to_pt(entry_size)

    body_size_pt = font_size_to_pt(config.get("body", {}).get("size", "小四"))
    indent_val = to_length(hanging_indent, font_size_pt=body_size_pt)
    pf = paragraph.paragraph_format
    pf.first_line_indent = -indent_val
    pf.left_indent = indent_val

    full_text = paragraph.text.strip()
    if full_text and len(paragraph.runs) > 0:
        entry_num_re = re.match(r"^[\[（(]\s*(\d+)\s*[\]）)]\s*", full_text)
        if not entry_num_re and not re.match(r"^\[?\d", full_text):
            pass
