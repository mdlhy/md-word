from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from converter.md_parser import Token


def add_code_block(doc: Document, token: Token, template_config: dict):
    """Add a code block from a parsed markdown token to a docx document.
    
    - Each line of code is a separate paragraph
    - Monospace font (Consolas or template config)
    - Font size from template config (default 10pt)
    - Gray background shading (w:shd)
    - Left indent: 2 characters
    - Preserves original indentation (no space compression)
    - No syntax highlighting
    """
    code_config = template_config.get("code", {})
    font_name = code_config.get("font", "Consolas")
    font_size = code_config.get("size", 10)
    bg_color = code_config.get("bg_color", "F5F5F5")
    
    raw_code = token.content
    if not raw_code:
        for child in token.children:
            if child.type == "text":
                raw_code += child.content
    
    if not raw_code:
        return []
    
    lines = raw_code.split("\n")
    paragraphs = []
    
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        
        # Left indent: 2 characters (about 420 twips)
        p.paragraph_format.left_indent = Cm(1.2)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        
        # Add shading (gray background) to paragraph
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), bg_color)
        pPr.append(shd)
        
        if i < len(lines) - 1 or line:  # skip only the last line if empty
            run = p.add_run(line if line else " ")
            run.font.name = font_name
            run.font.size = Pt(font_size)
            # Set eastAsia font too
            r_elem = run._element
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is not None:
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is not None:
                    rfonts.set(qn("w:eastAsia"), font_name)
        
        paragraphs.append(p)
    
    # Add empty paragraph after code block for spacing
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(6)
    paragraphs.append(spacer)
    
    return paragraphs
