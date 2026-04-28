"""WPS compatibility risk assessment for document elements."""

from dataclasses import dataclass, field
from typing import Literal

RiskLevel = Literal["low", "medium", "high"]


@dataclass
class CompatItem:
    element_type: str   # formula, image, table, heading, list, blockquote, code
    risk: RiskLevel     # low, medium, high
    description: str


@dataclass
class CompatReport:
    summary: dict = field(default_factory=lambda: {"low": 0, "medium": 0, "high": 0})
    items: list[CompatItem] = field(default_factory=list)


# High-risk LaTeX patterns (known math2docx failures)
_HIGH_RISK_PATTERNS = [
    r'\begin{aligned}',
    r'\begin{CD}',
    r'\begin{align}',
    r'\begin{eqnarray}',
    r'\newcommand',
    r'\renewcommand',
    r'\def\\',
]

# Medium-risk LaTeX patterns
_MEDIUM_RISK_PATTERNS = [
    r'\begin{pmatrix}',
    r'\begin{bmatrix}',
    r'\begin{vmatrix}',
    r'\begin{cases}',
    r'\begin{array}',
    r'\begin{matrix}',
    r'\left',
    r'\right',
]


def assess_formula_risk(latex: str) -> RiskLevel:
    """Assess WPS compatibility risk for a LaTeX formula.
    
    Rules based on known math2docx/latex2mathml limitations:
    - High: aligned/align/CD/custom macros (known conversion failures)
    - Medium: matrices/cases/array/left-right (partial support)
    - Low: everything else (fractions, superscripts, roots, etc.)
    """
    for pattern in _HIGH_RISK_PATTERNS:
        if pattern in latex:
            return "high"
    
    # Check for nested \frac (medium risk)
    frac_count = latex.count(r'\frac')
    if frac_count >= 2:
        return "medium"
    
    for pattern in _MEDIUM_RISK_PATTERNS:
        if pattern in latex:
            return "medium"
    
    return "low"


def assess_image_risk(src: str) -> RiskLevel:
    """Assess risk for image elements."""
    if not src:
        return "low"
    src_lower = src.lower()
    if src_lower.startswith(('http://', 'https://')):
        if src_lower.endswith('.svg'):
            return "medium"  # SVG needs conversion
        if src_lower.endswith('.webp'):
            return "medium"  # WebP needs conversion
        return "medium"  # Remote images may fail to download
    return "low"


def assess_table_risk() -> RiskLevel:
    """Tables are generally low risk in WPS."""
    return "low"


def generate_compat_report(details: list[CompatItem]) -> CompatReport:
    """Generate a compatibility report from a list of items."""
    summary = {"low": 0, "medium": 0, "high": 0}
    for item in details:
        summary[item.risk] = summary.get(item.risk, 0) + 1
    return CompatReport(summary=summary, items=details)
