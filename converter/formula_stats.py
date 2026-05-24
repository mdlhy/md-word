from __future__ import annotations

from dataclasses import asdict, dataclass

from docx import Document

from converter.models import ConvertResult
from converter.parser import parse_math_spans
from converter.walker import walk_all_paragraphs


@dataclass
class FormulaDocumentStats:
    document_total: int = 0
    native_omml: int = 0
    postprocessed: int = 0
    failed: int = 0
    skipped: int = 0
    residual_latex: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_document_formulas(
    doc: Document,
    conversion_result: ConvertResult | None = None,
) -> FormulaDocumentStats:
    conversion_result = conversion_result or ConvertResult()
    omml_total = _count_omml_formulas(doc)
    residual_latex = _count_residual_latex(doc)
    postprocessed = conversion_result.converted

    return FormulaDocumentStats(
        document_total=omml_total,
        native_omml=max(omml_total - postprocessed, 0),
        postprocessed=postprocessed,
        failed=conversion_result.failed,
        skipped=conversion_result.skipped,
        residual_latex=residual_latex,
    )


def _count_omml_formulas(doc: Document) -> int:
    ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    return len(doc.element.body.findall(".//m:oMath", ns))


def _count_residual_latex(doc: Document) -> int:
    total = 0
    for paragraph in walk_all_paragraphs(doc):
        total += len(parse_math_spans(paragraph.text or ""))
    return total
