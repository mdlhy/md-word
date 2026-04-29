"""In-place LaTeX formula replacement engine for .docx paragraphs."""
import copy
import logging

import math2docx
from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from .models import FormulaDetail, ReplaceResult
from .parser import parse_math_spans

logger = logging.getLogger(__name__)

NS_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS_M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'


def replace_formulas_in_paragraph(paragraph: Paragraph, page: int | None = None) -> ReplaceResult:
    """Find and replace LaTeX formulas in a paragraph with OMML elements.
    
    Uses the full-rebuild approach: concatenate all run text, find formulas,
    build segments, remove all runs, rebuild paragraph with text runs and OMML.
    """
    result = ReplaceResult()
    p_element = paragraph._p
    
    runs = paragraph.runs
    if not runs:
        return result
    
    run_texts = [r.text or '' for r in runs]
    full_text = ''.join(run_texts)
    
    if not full_text:
        return result
    
    spans = parse_math_spans(full_text)
    if not spans:
        return result
    
    result.total = len(spans)
    
    first_rpr = runs[0]._r.find(f'{NS_W}rPr')
    
    segments = []
    last_end = 0
    for span in spans:
        if span.start > last_end:
            segments.append(('text', full_text[last_end:span.start]))
        segments.append(('math', span.content, span.display))
        last_end = span.end
    if last_end < len(full_text):
        segments.append(('text', full_text[last_end:]))
    
    for child in list(p_element):
        if child.tag == f'{NS_W}r':
            p_element.remove(child)
    
    for seg in segments:
        if seg[0] == 'text':
            text = seg[1]
            if text:
                r = _create_text_run(text, first_rpr)
                p_element.append(r)
        elif seg[0] == 'math':
            latex = seg[1]
            display = seg[2]
            omml_elements, success = _latex_to_omml_children(latex, display)
            if success:
                for elem in omml_elements:
                    p_element.append(elem)
                result.converted += 1
                result.details.append(FormulaDetail(
                    latex=latex, status="converted", display=display, page=page
                ))
            else:
                delimiter = '$$' if display else '$'
                fallback = f'{delimiter}{latex}{delimiter}'
                r = _create_text_run(fallback, first_rpr)
                p_element.append(r)
                result.failed += 1
                result.details.append(FormulaDetail(
                    latex=latex, status="failed", display=display, page=page
                ))
    
    return result


def _latex_to_omml_children(latex_str: str, display: bool = False) -> tuple:
    """Convert LaTeX to OMML elements using temporary paragraph technique.
    
    Returns (omml_elements, success).
    """
    try:
        tmp_doc = Document()
        tmp_p = tmp_doc.add_paragraph()
        math2docx.add_math(tmp_p, latex_str)
        
        omath_elements = tmp_p._p.findall(f'{NS_M}oMath')
        if not omath_elements:
            return [], False
        
        if display:
            omath_para = OxmlElement('m:oMathPara')
            for elem in omath_elements:
                omath_para.append(copy.deepcopy(elem))
            return [omath_para], True
        else:
            return [copy.deepcopy(elem) for elem in omath_elements], True
    except Exception as e:
        logger.debug(f"LaTeX→OMML conversion failed for {repr(latex_str)}: {e}")
        return [], False


def _create_text_run(text: str, rpr_element=None):
    """Create a w:r element with optional formatting preservation."""
    r = OxmlElement('w:r')
    if rpr_element is not None:
        r.append(copy.deepcopy(rpr_element))
    t = OxmlElement('w:t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)
    return r
