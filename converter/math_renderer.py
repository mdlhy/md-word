"""Alternative math rendering pipeline using latex2mathml.

Provides a fallback path for LaTeX → MathML → OMML conversion
when math2docx fails or produces incorrect results.

Usage:
    from converter.math_renderer import latex_to_omml, latex_to_omml_para
"""

import logging
import copy
from lxml import etree

logger = logging.getLogger(__name__)

OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"

HAS_LATEX2MATHML = False
try:
    import latex2mathml.converter
    HAS_LATEX2MATHML = True
except ImportError:
    pass


def _clean_latex(s):
    s = s.strip()
    s = s.replace(r"\R", r"\mathbb{R}")
    s = s.replace(r"\N", r"\mathbb{N}")
    s = s.replace(r"\Z", r"\mathbb{Z}")
    s = s.replace(r"\Q", r"\mathbb{Q}")
    s = s.replace(r"\C", r"\mathbb{C}")
    return s


def latex_to_mathml(latex_str):
    if not HAS_LATEX2MATHML:
        return None
    if not latex_str or not latex_str.strip():
        return None
    cleaned = _clean_latex(latex_str)
    try:
        return latex2mathml.converter.convert(cleaned)
    except Exception as e:
        logger.warning(f"latex2mathml failed for: {latex_str[:50]}... → {e}")
        return None


def _local(tag):
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def _get_text(elem):
    texts = []
    if elem.text:
        texts.append(elem.text)
    for child in elem:
        texts.append(_get_text(child))
        if child.tail:
            texts.append(child.tail)
    return "".join(texts).strip()


def _omml_run(text):
    r = etree.Element(f"{{{OMML_NS}}}r")
    t = etree.SubElement(r, f"{{{OMML_NS}}}t")
    t.text = text
    return r


def _append_flattened(parent, child):
    if _local(child.tag) == "oMath" and _local(parent.tag) == "oMath":
        for sub in list(child):
            parent.append(sub)
    else:
        parent.append(child)


def _convert_mathml_element(elem):
    tag = _local(elem.tag)

    if tag == "math":
        omath = etree.Element(f"{{{OMML_NS}}}oMath")
        for child in elem:
            result = _convert_mathml_element(child)
            if result is not None:
                _append_flattened(omath, result)
        return omath

    elif tag == "mrow":
        children = list(elem)
        child_tags = [_local(c.tag) for c in children]

        if child_tags == ["mo", "mtable", "mo"]:
            open_delim = _get_text(children[0]) or "("
            close_delim = _get_text(children[2]) or ")"
            d = etree.Element(f"{{{OMML_NS}}}d")
            dPr = etree.SubElement(d, f"{{{OMML_NS}}}dPr")
            begChr = etree.SubElement(dPr, f"{{{OMML_NS}}}begChr")
            begChr.set(f"{{{OMML_NS}}}val", open_delim)
            endChr = etree.SubElement(dPr, f"{{{OMML_NS}}}endChr")
            endChr.set(f"{{{OMML_NS}}}val", close_delim)
            e_elem = etree.SubElement(d, f"{{{OMML_NS}}}e")
            mtable_omml = _convert_mathml_element(children[1])
            if mtable_omml is not None:
                e_elem.append(mtable_omml)
            return d

        if child_tags == ["mo", "mtable"]:
            open_delim = _get_text(children[0]) or "{"
            d = etree.Element(f"{{{OMML_NS}}}d")
            dPr = etree.SubElement(d, f"{{{OMML_NS}}}dPr")
            begChr = etree.SubElement(dPr, f"{{{OMML_NS}}}begChr")
            begChr.set(f"{{{OMML_NS}}}val", open_delim)
            endChr = etree.SubElement(dPr, f"{{{OMML_NS}}}endChr")
            endChr.set(f"{{{OMML_NS}}}val", "")
            e_elem = etree.SubElement(d, f"{{{OMML_NS}}}e")
            mtable_omml = _convert_mathml_element(children[1])
            if mtable_omml is not None:
                e_elem.append(mtable_omml)
            return d

        group = etree.Element(f"{{{OMML_NS}}}oMath")
        for child in children:
            result = _convert_mathml_element(child)
            if result is not None:
                _append_flattened(group, result)
        return group

    elif tag in ("mi", "mn", "mo", "mtext"):
        text = (elem.text or "").strip()
        if not text:
            return None
        r = etree.Element(f"{{{OMML_NS}}}r")
        if tag == "mi" and len(text) == 1:
            rPr = etree.SubElement(r, f"{{{OMML_NS}}}rPr")
            sty = etree.SubElement(rPr, f"{{{OMML_NS}}}sty")
            sty.set(f"{{{OMML_NS}}}val", "p" if text.isdigit() else "i")
        t = etree.SubElement(r, f"{{{OMML_NS}}}t")
        t.text = text
        return r

    elif tag == "mfrac":
        children = list(elem)
        if len(children) < 2:
            return None
        f = etree.Element(f"{{{OMML_NS}}}f")
        fPr = etree.SubElement(f, f"{{{OMML_NS}}}fPr")
        if elem.get("linethickness") == "0":
            type_el = etree.SubElement(fPr, f"{{{OMML_NS}}}type")
            type_el.set(f"{{{OMML_NS}}}val", "noBar")
        num = etree.SubElement(f, f"{{{OMML_NS}}}num")
        num_content = _convert_mathml_element(children[0])
        if num_content is not None:
            num.append(num_content)
        den = etree.SubElement(f, f"{{{OMML_NS}}}den")
        den_content = _convert_mathml_element(children[1])
        if den_content is not None:
            den.append(den_content)
        return f

    elif tag == "msqrt":
        rad = etree.Element(f"{{{OMML_NS}}}rad")
        radPr = etree.SubElement(rad, f"{{{OMML_NS}}}radPr")
        degHide = etree.SubElement(radPr, f"{{{OMML_NS}}}degHide")
        degHide.set(f"{{{OMML_NS}}}val", "1")
        deg = etree.SubElement(rad, f"{{{OMML_NS}}}deg")
        e_elem = etree.SubElement(rad, f"{{{OMML_NS}}}e")
        for child in elem:
            result = _convert_mathml_element(child)
            if result is not None:
                e_elem.append(result)
        return rad

    elif tag == "mroot":
        children = list(elem)
        rad = etree.Element(f"{{{OMML_NS}}}rad")
        radPr = etree.SubElement(rad, f"{{{OMML_NS}}}radPr")
        deg = etree.SubElement(rad, f"{{{OMML_NS}}}deg")
        if len(children) > 1:
            deg_content = _convert_mathml_element(children[1])
            if deg_content is not None:
                deg.append(deg_content)
        e_elem = etree.SubElement(rad, f"{{{OMML_NS}}}e")
        if children:
            base_content = _convert_mathml_element(children[0])
            if base_content is not None:
                e_elem.append(base_content)
        return rad

    elif tag == "msup":
        children = list(elem)
        if len(children) < 2:
            return None
        sSup = etree.Element(f"{{{OMML_NS}}}sSup")
        e_elem = etree.SubElement(sSup, f"{{{OMML_NS}}}e")
        base = _convert_mathml_element(children[0])
        if base is not None:
            e_elem.append(base)
        sup = etree.SubElement(sSup, f"{{{OMML_NS}}}sup")
        sup_content = _convert_mathml_element(children[1])
        if sup_content is not None:
            sup.append(sup_content)
        return sSup

    elif tag == "msub":
        children = list(elem)
        if len(children) < 2:
            return None
        sSub = etree.Element(f"{{{OMML_NS}}}sSub")
        e_elem = etree.SubElement(sSub, f"{{{OMML_NS}}}e")
        base = _convert_mathml_element(children[0])
        if base is not None:
            e_elem.append(base)
        sub = etree.SubElement(sSub, f"{{{OMML_NS}}}sub")
        sub_content = _convert_mathml_element(children[1])
        if sub_content is not None:
            sub.append(sub_content)
        return sSub

    elif tag == "msubsup":
        children = list(elem)
        if len(children) < 3:
            return None
        sSubSup = etree.Element(f"{{{OMML_NS}}}sSubSup")
        e_elem = etree.SubElement(sSubSup, f"{{{OMML_NS}}}e")
        base = _convert_mathml_element(children[0])
        if base is not None:
            e_elem.append(base)
        sub = etree.SubElement(sSubSup, f"{{{OMML_NS}}}sub")
        sub_c = _convert_mathml_element(children[1])
        if sub_c is not None:
            sub.append(sub_c)
        sup = etree.SubElement(sSubSup, f"{{{OMML_NS}}}sup")
        sup_c = _convert_mathml_element(children[2])
        if sup_c is not None:
            sup.append(sup_c)
        return sSubSup

    elif tag == "mover":
        children = list(elem)
        if len(children) < 2:
            return None
        acc = etree.Element(f"{{{OMML_NS}}}acc")
        accPr = etree.SubElement(acc, f"{{{OMML_NS}}}accPr")
        over_text = _get_text(children[1])
        if over_text:
            chr_el = etree.SubElement(accPr, f"{{{OMML_NS}}}chr")
            chr_el.set(f"{{{OMML_NS}}}val", over_text)
        e_elem = etree.SubElement(acc, f"{{{OMML_NS}}}e")
        base = _convert_mathml_element(children[0])
        if base is not None:
            e_elem.append(base)
        return acc

    elif tag == "munder":
        children = list(elem)
        if len(children) < 2:
            return None
        limLow = etree.Element(f"{{{OMML_NS}}}limLow")
        e_elem = etree.SubElement(limLow, f"{{{OMML_NS}}}e")
        base = _convert_mathml_element(children[0])
        if base is not None:
            e_elem.append(base)
        lim = etree.SubElement(limLow, f"{{{OMML_NS}}}lim")
        lim_c = _convert_mathml_element(children[1])
        if lim_c is not None:
            lim.append(lim_c)
        return limLow

    elif tag == "munderover":
        children = list(elem)
        if len(children) < 3:
            return None
        base_text = _get_text(children[0])
        nary_chars = {"∑", "∏", "∫", "∬", "∭", "⋃", "⋂", "⋁", "⋀"}
        if base_text in nary_chars:
            nary = etree.Element(f"{{{OMML_NS}}}nary")
            naryPr = etree.SubElement(nary, f"{{{OMML_NS}}}naryPr")
            chr_el = etree.SubElement(naryPr, f"{{{OMML_NS}}}chr")
            chr_el.set(f"{{{OMML_NS}}}val", base_text)
            sub = etree.SubElement(nary, f"{{{OMML_NS}}}sub")
            sub_c = _convert_mathml_element(children[1])
            if sub_c is not None:
                sub.append(sub_c)
            sup = etree.SubElement(nary, f"{{{OMML_NS}}}sup")
            sup_c = _convert_mathml_element(children[2])
            if sup_c is not None:
                sup.append(sup_c)
            e_elem = etree.SubElement(nary, f"{{{OMML_NS}}}e")
            return nary
        else:
            limLow = etree.Element(f"{{{OMML_NS}}}limLow")
            e_elem = etree.SubElement(limLow, f"{{{OMML_NS}}}e")
            base = _convert_mathml_element(children[0])
            if base is not None:
                e_elem.append(base)
            lim = etree.SubElement(limLow, f"{{{OMML_NS}}}lim")
            lim_c = _convert_mathml_element(children[1])
            if lim_c is not None:
                lim.append(lim_c)
            sSup = etree.Element(f"{{{OMML_NS}}}sSup")
            e2 = etree.SubElement(sSup, f"{{{OMML_NS}}}e")
            e2.append(limLow)
            sup = etree.SubElement(sSup, f"{{{OMML_NS}}}sup")
            sup_c = _convert_mathml_element(children[2])
            if sup_c is not None:
                sup.append(sup_c)
            return sSup

    elif tag == "mfenced":
        open_delim = elem.get("open", "(")
        close_delim = elem.get("close", ")")
        d = etree.Element(f"{{{OMML_NS}}}d")
        dPr = etree.SubElement(d, f"{{{OMML_NS}}}dPr")
        if open_delim:
            begChr = etree.SubElement(dPr, f"{{{OMML_NS}}}begChr")
            begChr.set(f"{{{OMML_NS}}}val", open_delim)
        if close_delim:
            endChr = etree.SubElement(dPr, f"{{{OMML_NS}}}endChr")
            endChr.set(f"{{{OMML_NS}}}val", close_delim)
        for child in elem:
            e_elem = etree.SubElement(d, f"{{{OMML_NS}}}e")
            result = _convert_mathml_element(child)
            if result is not None:
                e_elem.append(result)
        return d

    elif tag == "mtable":
        m = etree.Element(f"{{{OMML_NS}}}m")
        mPr = etree.SubElement(m, f"{{{OMML_NS}}}mPr")
        baseJc = etree.SubElement(mPr, f"{{{OMML_NS}}}baseJc")
        baseJc.set(f"{{{OMML_NS}}}val", "center")
        plcHide = etree.SubElement(mPr, f"{{{OMML_NS}}}plcHide")
        plcHide.set(f"{{{OMML_NS}}}val", "on")
        first_row = elem.find(f"{{{MATHML_NS}}}mtr")
        if first_row is None:
            first_row = elem.find("mtr")
        if first_row is not None:
            num_cols = len(list(first_row))
            mcs = etree.SubElement(mPr, f"{{{OMML_NS}}}mcs")
            mc = etree.SubElement(mcs, f"{{{OMML_NS}}}mc")
            mcPr = etree.SubElement(mc, f"{{{OMML_NS}}}mcPr")
            count = etree.SubElement(mcPr, f"{{{OMML_NS}}}count")
            count.set(f"{{{OMML_NS}}}val", str(num_cols))
            mcJc = etree.SubElement(mcPr, f"{{{OMML_NS}}}mcJc")
            mcJc.set(f"{{{OMML_NS}}}val", "center")
        for row_elem in elem:
            if _local(row_elem.tag) == "mtr":
                mr = etree.SubElement(m, f"{{{OMML_NS}}}mr")
                for cell_elem in row_elem:
                    if _local(cell_elem.tag) == "mtd":
                        e_elem = etree.SubElement(mr, f"{{{OMML_NS}}}e")
                        for cell_child in cell_elem:
                            result = _convert_mathml_element(cell_child)
                            if result is not None:
                                _append_flattened(e_elem, result)
                        if cell_elem.text and cell_elem.text.strip():
                            e_elem.append(_omml_run(cell_elem.text.strip()))
        return m

    elif tag == "mspace":
        return _omml_run("\u2003")

    elif tag in ("mpadded", "mstyle", "menclose"):
        group = etree.Element(f"{{{OMML_NS}}}oMath")
        for child in elem:
            result = _convert_mathml_element(child)
            if result is not None:
                _append_flattened(group, result)
        return group

    else:
        if elem.text and elem.text.strip():
            return _omml_run(elem.text.strip())
        group = etree.Element(f"{{{OMML_NS}}}oMath")
        for child in elem:
            result = _convert_mathml_element(child)
            if result is not None:
                _append_flattened(group, result)
        if len(group):
            return group
        return None


def latex_to_omml(latex_str):
    """Convert LaTeX math to an OMML element for inline math."""
    mathml = latex_to_mathml(latex_str)
    if mathml is None:
        return None
    try:
        if 'xmlns' not in mathml:
            mathml = mathml.replace('<math>', f'<math xmlns="{MATHML_NS}">')
        root = etree.fromstring(mathml.encode('utf-8'))
        return _convert_mathml_element(root)
    except Exception as e:
        logger.warning(f"MathML→OMML conversion failed: {e}")
        return None


def latex_to_omml_para(latex_str):
    """Convert LaTeX math to an OMML oMathPara element for display math."""
    omath = latex_to_omml(latex_str)
    if omath is None:
        return None
    oMathPara = etree.Element(f"{{{OMML_NS}}}oMathPara")
    oMathPara.append(omath)
    return oMathPara
