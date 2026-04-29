from dataclasses import dataclass, field
from typing import Literal


@dataclass
class MathSpan:
    """Represents a detected LaTeX math formula span in text."""
    start: int          # character offset where formula begins (including delimiter)
    end: int            # character offset where formula ends (after closing delimiter)
    content: str        # LaTeX content (without delimiters)
    display: bool       # True = display math ($$ or \[), False = inline ($ or \()
    delimiter_type: Literal["dollar", "double_dollar", "paren", "bracket"]


@dataclass
class FormulaDetail:
    latex: str
    status: Literal["converted", "failed", "skipped"]
    display: bool
    page: int | None = None


@dataclass
class ReplaceResult:
    total: int = 0
    converted: int = 0
    failed: int = 0
    skipped: int = 0
    details: list = field(default_factory=list)


@dataclass
class ConvertResult:
    total: int = 0
    converted: int = 0
    failed: int = 0
    skipped: int = 0
    details: list = field(default_factory=list)
