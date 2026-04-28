from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from converter.md_parser import Token


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
            run.font.size = Pt(heading_config["size"])
        if heading_config.get("bold"):
            run.font.bold = True
    
    if heading_config.get("center"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    return p
