"""Conversion orchestrator: integrate parser + walker + replacer."""
import logging

from docx import Document

from .models import ConvertResult
from .walker import walk_all_paragraphs
from .replacer import replace_formulas_in_paragraph

logger = logging.getLogger(__name__)


def convert_docx_in_memory(doc: Document) -> ConvertResult:
    """Convert all LaTeX formulas in an already-loaded Document to OMML.
    
    Operates in-place on the Document object (no file I/O).
    
    Args:
        doc: A python-docx Document object
        
    Returns:
        ConvertResult with stats and per-formula details
    """
    result = ConvertResult()
    
    paragraphs = list(walk_all_paragraphs(doc))
    has_page_markers = any(getattr(paragraph, "contains_page_break", False) for paragraph in paragraphs)
    current_page = 1

    for paragraph in paragraphs:
        try:
            breaks = list(getattr(paragraph, "rendered_page_breaks", []))
            leading_breaks = sum(
                1 for page_break in breaks
                if page_break.preceding_paragraph_fragment is None
            )
            page = current_page + leading_breaks if has_page_markers else None
            replace_result = replace_formulas_in_paragraph(paragraph, page=page)
            result.total += replace_result.total
            result.converted += replace_result.converted
            result.failed += replace_result.failed
            result.skipped += replace_result.skipped
            result.details.extend(replace_result.details)
        except Exception as e:
            logger.error(f"Failed to process paragraph: {e}", exc_info=True)
            continue

        if has_page_markers:
            current_page += len(breaks)
    
    logger.info(f"In-memory conversion complete: {result.converted}/{result.total} converted, "
                f"{result.failed} failed, {result.skipped} skipped")
    return result


def convert_docx(input_path: str, output_path: str) -> ConvertResult:
    """Convert all LaTeX formulas in a .docx file to OMML.
    
    Args:
        input_path: Path to input .docx file
        output_path: Path to write converted .docx file
        
    Returns:
        ConvertResult with stats and per-formula details
    """
    doc = Document(input_path)
    result = convert_docx_in_memory(doc)
    doc.save(output_path)
    logger.info(f"Conversion complete: {result.converted}/{result.total} converted, "
                f"{result.failed} failed, {result.skipped} skipped")
    return result
