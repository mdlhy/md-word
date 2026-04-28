"""Conversion orchestrator: integrate parser + walker + replacer."""
import logging

from docx import Document

from .models import ConvertResult, FormulaDetail
from .walker import walk_all_paragraphs
from .replacer import replace_formulas_in_paragraph

logger = logging.getLogger(__name__)


def convert_docx(input_path: str, output_path: str) -> ConvertResult:
    """Convert all LaTeX formulas in a .docx file to OMML.
    
    Args:
        input_path: Path to input .docx file
        output_path: Path to write converted .docx file
        
    Returns:
        ConvertResult with stats and per-formula details
    """
    doc = Document(input_path)
    result = ConvertResult()
    
    for paragraph in walk_all_paragraphs(doc):
        try:
            replace_result = replace_formulas_in_paragraph(paragraph)
            result.total += replace_result.total
            result.converted += replace_result.converted
            result.failed += replace_result.failed
            result.skipped += replace_result.skipped
            result.details.extend(replace_result.details)
        except Exception as e:
            logger.error(f"Failed to process paragraph: {e}", exc_info=True)
            continue
    
    doc.save(output_path)
    logger.info(f"Conversion complete: {result.converted}/{result.total} converted, "
                f"{result.failed} failed, {result.skipped} skipped")
    return result
