"""Format unit conversion layer for Chinese academic document formatting.

Provides a single entry point `to_pt()` that converts Chinese font sizes,
spacing values, and length values to python-docx units (Pt, Cm, Emu).

Supports:
  - Chinese font sizes: '小四' → 12pt, '三号' → 16pt, etc.
  - Numeric pt values: 12 → 12pt, 10.5 → 10.5pt
  - Spacing with units: '20磅' → 20pt, '0.5行' → line spacing, '2字符' → indent
  - Length with units: '3cm' → Cm(3), '1inch' → Inches(1)

Usage:
    from converter.format_units import to_pt, to_spacing, to_length
    run.font.size = to_pt('小四')       # Pt(12)
    para.line_spacing = to_spacing('20磅')  # Pt(20)
    para.first_line_indent = to_length('2字符', font_size_pt=12)  # Cm(...)
"""

import re
from docx.shared import Pt, Cm, Emu, Inches


# ============================================================
# Chinese font size → pt mapping (GB/T 3705-1999)
# ============================================================

FONT_SIZE_MAP: dict[str, float] = {
    "一号": 26,
    "小一": 24,
    "二号": 22,
    "小二": 18,
    "三号": 16,
    "小三": 15,
    "四号": 14,
    "小四": 12,
    "五号": 10.5,
    "小五": 9,
    "六号": 7.5,
    "七号": 5.5,
    "八号": 5,
}

REVERSE_FONT_SIZE_MAP: dict[float, str] = {v: k for k, v in FONT_SIZE_MAP.items()}


def font_size_to_pt(size: str | int | float) -> float:
    """Convert Chinese font size name or numeric value to pt float.

    Args:
        size: Chinese name like '小四', or numeric pt value like 12

    Returns:
        Font size in pt as float

    Raises:
        ValueError: If size string is not a recognized font size name
    """
    if isinstance(size, (int, float)):
        return float(size)
    if isinstance(size, str):
        stripped = size.strip()
        if stripped in FONT_SIZE_MAP:
            return FONT_SIZE_MAP[stripped]
        try:
            return float(stripped)
        except ValueError:
            raise ValueError(
                f"无效字号 '{size}'，可选: {', '.join(FONT_SIZE_MAP.keys())} 或数字(pt)"
            )
    raise TypeError(f"字号类型错误: {type(size)}, 需要 str/int/float")


def pt_to_font_size_name(pt_value: float) -> str | None:
    """Convert pt value back to Chinese font size name, or None if no match."""
    return REVERSE_FONT_SIZE_MAP.get(pt_value)


def to_pt(size: str | int | float) -> Pt:
    """Convert Chinese font size or numeric to python-docx Pt object."""
    return Pt(font_size_to_pt(size))


def to_half_pt(size: str | int | float) -> int:
    """Convert font size to half-points for w:sz XML attributes.

    Word stores font sizes in half-points: 小四(12pt) → 24
    """
    return int(font_size_to_pt(size) * 2)


# ============================================================
# Unit-aware string parsing
# ============================================================

_UNIT_PATTERN = re.compile(
    r"^(\d+\.?\d*)\s*(磅|pt|厘米|cm|毫米|mm|英寸|inch|行|字符|倍|cm|mm|pt)$",
    re.IGNORECASE,
)

_UNIT_TO_STD = {
    "磅": "pt", "pt": "pt", "PT": "pt",
    "厘米": "cm", "cm": "cm", "CM": "cm",
    "毫米": "mm", "mm": "mm", "MM": "mm",
    "英寸": "inch", "inch": "inch", "Inch": "inch",
    "行": "hang",
    "字符": "char",
    "倍": "multi",
}


def parse_unit(value: str) -> tuple[float, str]:
    """Parse a unit-aware string like '20磅', '0.5行', '2字符', '3cm'.

    Returns:
        (numeric_value, standard_unit) where standard_unit is one of:
        'pt', 'cm', 'mm', 'inch', 'hang', 'char', 'multi'

    Raises:
        ValueError: If the string doesn't match any known unit pattern
    """
    if isinstance(value, (int, float)):
        return float(value), "pt"

    if isinstance(value, str):
        stripped = value.strip()

        if stripped in FONT_SIZE_MAP:
            return FONT_SIZE_MAP[stripped], "pt"

        m = _UNIT_PATTERN.match(stripped)
        if m:
            num = float(m.group(1))
            unit_raw = m.group(2)
            std_unit = _UNIT_TO_STD.get(unit_raw, "pt")
            return num, std_unit

        try:
            return float(stripped), "pt"
        except ValueError:
            raise ValueError(
                f"无法解析单位值 '{value}'，"
                f"支持: X磅/Xpt/X厘米/Xcm/X行/X字符/X倍/Xcm/Xmm"
            )

    raise TypeError(f"值类型错误: {type(value)}, 需要 str/int/float")


# ============================================================
# High-level converters for paragraph formatting
# ============================================================

def to_spacing(value: str | int | float) -> Pt | float:
    """Convert spacing value to python-docx compatible object.

    Args:
        value: '20磅' → Pt(20), '1.5倍' → 1.5 (for line_spacing),
               '0.5行' → Pt(12*0.5) if default body size, etc.

    Returns:
        Pt for fixed spacing, float for multiplier spacing
    """
    num, unit = parse_unit(value)

    if unit == "pt":
        return Pt(num)
    elif unit == "multi":
        return num
    elif unit == "hang":
        return num
    elif unit == "cm":
        return Cm(num)
    elif unit == "inch":
        return Inches(num)
    else:
        return Pt(num)


def to_length(value: str | int | float, font_size_pt: float = 12) -> Cm | Pt | Emu:
    """Convert length/indent value to python-docx length object.

    Args:
        value: '2字符' → indent in cm based on font_size_pt,
               '3cm' → Cm(3), '1inch' → Inches(1), '20磅' → Pt(20)
        font_size_pt: Font size in pt for character-unit conversion.
                      1 字符 ≈ font_size_pt * 0.035 cm (empirical for Chinese docs)

    Returns:
        python-docx length object
    """
    num, unit = parse_unit(value)

    if unit == "char":
        return Cm(num * font_size_pt * 0.035)
    elif unit == "cm":
        return Cm(num)
    elif unit == "mm":
        return Cm(num / 10)
    elif unit == "inch":
        return Inches(num)
    elif unit == "pt":
        return Pt(num)
    elif unit == "hang":
        return num
    elif unit == "multi":
        return num
    else:
        return Pt(num)


# ============================================================
# Alignment mapping
# ============================================================

ALIGNMENT_MAP: dict[str, str] = {
    "左对齐": "LEFT",
    "居中对齐": "CENTER",
    "居中": "CENTER",
    "右对齐": "RIGHT",
    "两端对齐": "JUSTIFY",
    "分散对齐": "DISTRIBUTE",
}


def to_alignment(value: str) -> int | None:
    """Convert Chinese alignment name to WD_ALIGN_PARAGRAPH constant.

    Args:
        value: '左对齐', '居中对齐', '右对齐', '两端对齐', '分散对齐'

    Returns:
        WD_ALIGN_PARAGRAPH constant, or None for unknown
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    mapped = ALIGNMENT_MAP.get(value)
    if mapped is None:
        if isinstance(value, str):
            mapped = value.upper()
        else:
            return None

    return getattr(WD_ALIGN_PARAGRAPH, mapped, None)
