from __future__ import annotations

import os
import glob as glob_module
from dataclasses import dataclass

from converter.compat_report import CompatReport
from converter.formula_stats import FormulaDocumentStats, inspect_document_formulas
from converter.models import ConvertResult
from converter.pandoc_driver import (
    PandocUnavailableError,
    convert_markdown_file as convert_markdown_file_with_pandoc,
    convert_markdown_text as convert_markdown_text_with_pandoc,
    is_pandoc_available,
)

Engine = str
SUPPORTED_ENGINES = {"auto", "pandoc", "legacy"}


class UnknownEngineError(ValueError):
    pass


@dataclass
class MarkdownConversion:
    output_path: str
    engine: str
    compat_report: CompatReport
    formula_result: ConvertResult
    formula_document_stats: FormulaDocumentStats


def normalize_engine(engine: str | None = None) -> str:
    selected = (engine or os.environ.get("MD2WPS_ENGINE", "auto")).strip().lower()
    if selected not in SUPPORTED_ENGINES:
        raise UnknownEngineError(f"未知转换引擎: {selected}")
    return selected


def convert_markdown_file_to_docx(
    input_path: str,
    output_path: str,
    template_name: str = "academic",
    three_line: bool = False,
    engine: str | None = None,
    format_options: dict | None = None,
) -> MarkdownConversion:
    selected = normalize_engine(engine)

    if selected in ("auto", "pandoc") and is_pandoc_available():
        result = convert_markdown_file_with_pandoc(
            input_path,
            output_path,
            template_name,
            three_line,
            format_options=format_options,
        )
        return MarkdownConversion(
            output_path=result.output_path,
            engine="pandoc",
            compat_report=result.compat_report,
            formula_result=result.formula_result,
            formula_document_stats=result.formula_document_stats,
        )

    if selected == "pandoc":
        raise PandocUnavailableError("pandoc 未安装或不在 PATH 中")

    return _convert_markdown_file_legacy(
        input_path,
        output_path,
        template_name,
        three_line,
        format_options=format_options,
    )


def convert_markdown_directory_to_docx(
    input_dir: str,
    output_dir: str | None = None,
    template_name: str = "academic",
    three_line: bool = False,
    recursive: bool = False,
    engine: str | None = None,
) -> list[tuple[str, str, bool, str | None]]:
    input_dir = os.path.abspath(input_dir)
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"Not a directory: {input_dir}")

    if output_dir is None:
        output_dir = input_dir
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    pattern = os.path.join(input_dir, "**", "*.md") if recursive else os.path.join(input_dir, "*.md")
    md_files = sorted(glob_module.glob(pattern, recursive=recursive))

    results: list[tuple[str, str, bool, str | None]] = []
    for md_file in md_files:
        rel_path = os.path.relpath(md_file, input_dir)
        out_path = os.path.join(output_dir, os.path.splitext(rel_path)[0] + ".docx")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        try:
            convert_markdown_file_to_docx(
                md_file,
                out_path,
                template_name,
                three_line,
                engine,
            )
            results.append((md_file, out_path, True, None))
        except Exception as e:
            results.append((md_file, out_path, False, str(e)))

    return results


def convert_markdown_text_to_docx(
    md_text: str,
    output_path: str,
    template_name: str = "academic",
    three_line: bool = False,
    base_dir: str | None = None,
    engine: str | None = None,
    format_options: dict | None = None,
) -> MarkdownConversion:
    selected = normalize_engine(engine)

    if selected in ("auto", "pandoc") and is_pandoc_available():
        result = convert_markdown_text_with_pandoc(
            md_text,
            output_path,
            template_name,
            three_line,
            base_dir=base_dir,
            postprocess=True,
            format_options=format_options,
        )
        return MarkdownConversion(
            output_path=result.output_path,
            engine="pandoc",
            compat_report=result.compat_report,
            formula_result=result.formula_result,
            formula_document_stats=result.formula_document_stats,
        )

    if selected == "pandoc":
        raise PandocUnavailableError("pandoc 未安装或不在 PATH 中")

    return _convert_markdown_text_legacy(
        md_text,
        output_path,
        template_name,
        three_line,
        base_dir,
        format_options=format_options,
    )


def _convert_markdown_file_legacy(
    input_path: str,
    output_path: str,
    template_name: str,
    three_line: bool,
    format_options: dict | None = None,
) -> MarkdownConversion:
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    return _convert_markdown_text_legacy(
        md_text,
        output_path,
        template_name,
        three_line,
        base_dir=os.path.dirname(os.path.abspath(input_path)),
        format_options=format_options,
    )


def _convert_markdown_text_legacy(
    md_text: str,
    output_path: str,
    template_name: str,
    three_line: bool,
    base_dir: str | None = None,
    format_options: dict | None = None,
) -> MarkdownConversion:
    from converter.md_converter import convert_md_to_docx

    doc, report = convert_md_to_docx(
        md_text,
        template_name,
        three_line,
        base_dir=base_dir,
        format_options=format_options,
    )
    doc.save(output_path)
    formula_document_stats = inspect_document_formulas(doc)
    return MarkdownConversion(
        output_path=os.path.abspath(output_path),
        engine="legacy",
        compat_report=report,
        formula_result=ConvertResult(),
        formula_document_stats=formula_document_stats,
    )
