"""Heading auto-numbering module for MD → .docx conversion.

Two-phase approach:
  1. Strip manual numbering from heading text (regex: "第1章", "1.1", "1.1.1", etc.)
  2. Apply Word auto-numbering via numbering.xml + w:numPr

All heading levels share one abstractNum so that multi-level counters
(%1, %2, %3) reference each other correctly.

Usage from md_converter:
    from converter.numbering import process_heading_numbering
    process_heading_numbering(doc, config)
"""

from __future__ import annotations

import re
import logging

from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt

from converter.format_units import to_half_pt

logger = logging.getLogger(__name__)

# Manual numbering patterns in AI-generated MD headings:
#   "第1章" / "第一章" / "第1节" / "第一节"  → Chinese chapter/section
#   "1." / "1.1" / "1.1.1"  → Arabic decimal
#   "1 " / "1  Title"  → Number + space (H1)
_STRIP_PATTERNS: dict[int, list[re.Pattern]] = {
    1: [
        re.compile(r"^第[一二三四五六七八九十百千\d]+[章节部篇]\s*"),
        re.compile(r"^(\d+)\s*[.、]\s*"),
        re.compile(r"^(\d+)\s+"),
    ],
    2: [
        re.compile(r"^[一二三四五六七八九十]+[、.]\s*"),
        re.compile(r"^(\d+[.、])\s*(\d+)\s*[.、]?\s*"),
    ],
    3: [
        re.compile(r"^问题\s*\d+\s*[：:]\s*"),
        re.compile(r"^(\d+[.、])\s*(\d+[.、])\s*(\d+)\s*[.、]?\s*"),
    ],
}


def strip_manual_numbering(paragraph, level: int) -> bool:
    """Strip manual numbering text from the beginning of a heading paragraph.

    Only modifies run text, preserving formatting. Returns True if numbering
    was found and stripped.

    Args:
        paragraph: python-docx Paragraph object
        level: Heading level (1, 2, or 3)

    Returns:
        True if manual numbering was stripped
    """
    patterns = _STRIP_PATTERNS.get(level, [])
    if not patterns or not paragraph.runs:
        return False

    full_text = paragraph.text
    for pattern in patterns:
        match = pattern.match(full_text)
        if match:
            stripped_len = match.end()
            # Walk through runs, removing the matched prefix
            remaining = stripped_len
            for run in paragraph.runs:
                if remaining <= 0:
                    break
                run_text = run.text
                if len(run_text) <= remaining:
                    remaining -= len(run_text)
                    run.text = ""
                else:
                    run.text = run_text[remaining:]
                    remaining = 0
            # Lstrip the first non-empty run
            for run in paragraph.runs:
                if run.text:
                    run.text = run.text.lstrip()
                    break
            logger.debug(f"Stripped manual numbering from H{level}: '{match.group()}'")
            return True

    return False


def _get_or_create_numbering_part(document):
    """Get existing numbering part or create a new one."""
    try:
        return document.part.numbering_part
    except (AttributeError, KeyError, NotImplementedError):
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.opc.packuri import PackURI
        from docx.parts.numbering import NumberingPart

        numbering_elm = OxmlElement("w:numbering")
        numbering_part = NumberingPart(
            PackURI("/word/numbering.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
            numbering_elm,
            document.part.package,
        )
        document.part.relate_to(numbering_part, RT.NUMBERING)
        return numbering_part


def _build_lvl_rPr(heading_config: dict) -> OxmlElement | None:
    """Build w:rPr for numbering level, matching heading font/size/bold.

    Returns None if no relevant properties to set.
    """
    rPr = OxmlElement("w:rPr")

    rFonts = OxmlElement("w:rFonts")
    has_font = False
    font_cn = heading_config.get("font_cn")
    font_en = heading_config.get("font_en")
    if font_cn:
        rFonts.set(qn("w:eastAsia"), font_cn)
        has_font = True
    if font_en:
        rFonts.set(qn("w:ascii"), font_en)
        rFonts.set(qn("w:hAnsi"), font_en)
        has_font = True
    if has_font:
        rPr.append(rFonts)

    size_val = heading_config.get("size")
    if size_val:
        half_pt = to_half_pt(size_val)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(half_pt))
        rPr.append(sz)
        szCs = OxmlElement("w:szCs")
        szCs.set(qn("w:val"), str(half_pt))
        rPr.append(szCs)

    if heading_config.get("bold"):
        b = OxmlElement("w:b")
        rPr.append(b)
        bCs = OxmlElement("w:bCs")
        rPr.append(bCs)

    if len(rPr) == 0:
        return None
    return rPr


def _detect_numFmt(template: str) -> str:
    if "第" in template and "章" in template:
        return "chineseCountingThousand"
    return "decimal"


def create_numbering_definition(document, template_config: dict) -> str | None:
    enabled_levels = []
    for level in (1, 2, 3):
        hcfg = template_config.get(f"heading{level}", {})
        num_cfg = hcfg.get("numbering", {})
        if num_cfg.get("enabled") and num_cfg.get("template"):
            enabled_levels.append((level, hcfg, num_cfg))

    if not enabled_levels:
        return None

    numbering_part = _get_or_create_numbering_part(document)
    numbering_elm = numbering_part._element

    max_abstract_num_id = -1
    max_num_id = 0
    for elem in numbering_elm.findall(qn("w:abstractNum")):
        aid = int(elem.get(qn("w:abstractNumId"), "0"))
        max_abstract_num_id = max(max_abstract_num_id, aid)
    for elem in numbering_elm.findall(qn("w:num")):
        nid = int(elem.get(qn("w:numId"), "0"))
        max_num_id = max(max_num_id, nid)

    abstract_num_id = max_abstract_num_id + 1
    num_id = max_num_id + 1

    abstract_num = OxmlElement("w:abstractNum")
    abstract_num.set(qn("w:abstractNumId"), str(abstract_num_id))

    multi_lvl = OxmlElement("w:multiLevelType")
    multi_lvl.set(qn("w:val"), "multilevel")
    abstract_num.append(multi_lvl)

    for level, hcfg, num_cfg in enabled_levels:
        ilvl = level - 1

        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(ilvl))

        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        lvl.append(start)

        numFmt = OxmlElement("w:numFmt")
        numFmt.set(qn("w:val"), _detect_numFmt(num_cfg["template"]))
        lvl.append(numFmt)

        lvlText = OxmlElement("w:lvlText")
        lvlText.set(qn("w:val"), num_cfg["template"])
        lvl.append(lvlText)

        suff = OxmlElement("w:suff")
        suff_val = num_cfg.get("suffix", "space")
        suffix_map = {"space": "space", "tab": "tab", "none": "nothing", "无": "nothing"}
        suff.set(qn("w:val"), suffix_map.get(suff_val, "space"))
        lvl.append(suff)

        lvlJc = OxmlElement("w:lvlJc")
        lvlJc.set(qn("w:val"), "left")
        lvl.append(lvlJc)

        pPr = OxmlElement("w:pPr")
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "0")
        ind.set(qn("w:hanging"), str((ilvl + 1) * 420))
        pPr.append(ind)
        lvl.append(pPr)

        rPr = _build_lvl_rPr(hcfg)
        if rPr is not None:
            lvl.append(rPr)

        abstract_num.append(lvl)

    numbering_elm.append(abstract_num)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_num_id_ref = OxmlElement("w:abstractNumId")
    abstract_num_id_ref.set(qn("w:val"), str(abstract_num_id))
    num.append(abstract_num_id_ref)
    numbering_elm.append(num)

    logger.debug(f"Created heading numbering: abstractNumId={abstract_num_id}, numId={num_id}")
    return str(num_id)


def apply_auto_numbering(paragraph, num_id: str, ilvl: int = 0):
    """Apply auto-numbering to a paragraph via w:numPr.

    Args:
        paragraph: python-docx Paragraph
        num_id: Numbering definition ID from create_numbering_definition
        ilvl: Level index (0-based)
    """
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        paragraph._element.insert(0, pPr)

    existing = pPr.find(qn("w:numPr"))
    if existing is not None:
        pPr.remove(existing)

    numPr = OxmlElement("w:numPr")
    ilvl_elem = OxmlElement("w:ilvl")
    ilvl_elem.set(qn("w:val"), str(ilvl))
    numId_elem = OxmlElement("w:numId")
    numId_elem.set(qn("w:val"), num_id)
    numPr.append(ilvl_elem)
    numPr.append(numId_elem)
    pPr.append(numPr)


def process_heading_numbering(document, template_config: dict, heading_paragraphs: list):
    """Process all heading paragraphs: strip manual numbering + apply auto-numbering.

    Called from md_converter after all headings are added.

    Args:
        document: python-docx Document
        template_config: Template config dict
        heading_paragraphs: List of (level, paragraph) tuples from conversion
    """
    num_id = create_numbering_definition(document, template_config)
    if num_id is None:
        logger.debug("Heading numbering disabled in template")
        return

    for level, paragraph in heading_paragraphs:
        hcfg = template_config.get(f"heading{level}", {})
        num_cfg = hcfg.get("numbering", {})

        if not num_cfg.get("enabled"):
            continue

        strip_manual_numbering(paragraph, level)
        apply_auto_numbering(paragraph, num_id, level - 1)

    logger.info(f"Processed heading numbering for {len(heading_paragraphs)} headings")
