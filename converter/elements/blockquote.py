from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_LINE_SPACING

from converter.md_parser import Token
from converter.format_units import to_length, font_size_to_pt


def add_blockquote(doc: Document, token: Token, template_config: dict):
    """Add a blockquote from a parsed markdown token to a docx document.
    
    - Left indent: template config quote.indent (in cm, default 2)
    - Left border: template config quote.border_color (default CCCCCC), width 3pt
    - Each line is an independent paragraph sharing indent and border
    """
    quote_config = template_config.get("quote", {})
    indent_value = quote_config.get("indent", "2字符")
    border_color = quote_config.get("border_color", "CCCCCC")
    
    body_config = template_config.get("body", {})
    body_size_pt = font_size_to_pt(body_config.get("size", "小四"))
    
    paragraphs = []
    
    def add_quote_paragraph(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = to_length(indent_value, font_size_pt=body_size_pt)
        p.paragraph_format.space_after = Pt(4)
        
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        left_border = OxmlElement("w:left")
        left_border.set(qn("w:val"), "single")
        left_border.set(qn("w:sz"), "24")  # 3pt = 24 eighths of a point
        left_border.set(qn("w:space"), "4")
        left_border.set(qn("w:color"), border_color)
        pBdr.append(left_border)
        pPr.append(pBdr)
        
        if text:
            run = p.add_run(text)
            run.font.italic = True
        
        paragraphs.append(p)
        return p
    
    for child in token.children:
        if child.type == "paragraph":
            text_parts = []
            for sub in child.children:
                if sub.type == "text":
                    text_parts.append(sub.content)
                elif sub.type == "math":
                    text_parts.append(sub.content)
                else:
                    text_parts.append(sub.content)
            text = " ".join(t for t in text_parts if t).strip()
            add_quote_paragraph(text)
        elif child.type == "text":
            add_quote_paragraph(child.content)
        elif child.type == "blockquote":
            nested_indent_cm = to_length(indent_value, font_size_pt=body_size_pt).cm + 2
            nested_config = dict(template_config)
            nested_config["quote"] = dict(quote_config, indent=f"{nested_indent_cm}厘米")
            nested_ps = add_blockquote(doc, child, nested_config)
            paragraphs.extend(nested_ps)
    
    if not paragraphs:
        add_quote_paragraph(token.content)
    
    return paragraphs
