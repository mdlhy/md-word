from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from converter.md_parser import Token
from converter.format_units import to_pt, to_alignment


def add_heading(doc: Document, token: Token, template_config: dict):
    """Add a heading from a parsed markdown token to a docx document.
    
    Maps MD heading level → Word Heading style (1→Heading 1, 2→Heading 2, 3→Heading 3).
    Applies template font/size/bold/center config. Strips residual # symbols.
    Level > 3 degrades to Heading 3 + bold.
    """
    level = token.attrs.get("level", token.level) or 1
    if level > 3:
        level = 3
    text = token.content.strip().lstrip("#").strip()
    if not text and token.children:
        text_parts = []
        for child in token.children:
            if child.type == "text":
                text_parts.append(child.content)
        text = " ".join(text_parts).strip()
    if not text:
        text = token.content
    
    heading_key = f"heading{level}"
    heading_config = template_config.get(heading_key, {})
    
    style_name = f"Heading {level}"
    p = doc.add_heading(text, level=level)
    
    for run in p.runs:
        font_en = heading_config.get("font_en", "Times New Roman")
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
        rfonts.set(qn("w:eastAsia"), heading_config.get("font_cn", "黑体"))
        
        if heading_config.get("size"):
            run.font.size = to_pt(heading_config["size"])
        if heading_config.get("bold"):
            run.font.bold = True
        rpr_main = run._element.find(qn("w:rPr"))
        if rpr_main is None:
            rpr_main = OxmlElement("w:rPr")
            run._element.insert(0, rpr_main)
        color_el = rpr_main.find(qn("w:color"))
        if color_el is None:
            color_el = OxmlElement("w:color")
            rpr_main.append(color_el)
        color_el.set(qn("w:val"), "000000")
        color_el.set(qn("w:themeColor"), "text1")
    
    alignment = to_alignment(heading_config.get("alignment", "左对齐"))
    if alignment is not None:
        p.alignment = alignment
    
    return p
