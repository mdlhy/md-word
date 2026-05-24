import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from converter import markdown_pipeline
from converter.compat_report import generate_compat_report
from converter.formula_stats import FormulaDocumentStats
from converter.models import ConvertResult
from converter.pandoc_driver import PandocResult, PandocUnavailableError


def test_auto_engine_falls_back_to_legacy_when_pandoc_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(markdown_pipeline, "is_pandoc_available", lambda: False)

    output_path = tmp_path / "out.docx"
    result = markdown_pipeline.convert_markdown_text_to_docx(
        "# Title\n\nBody",
        str(output_path),
        engine="auto",
    )

    assert result.engine == "legacy"
    assert output_path.exists()


def test_forced_pandoc_engine_requires_pandoc(monkeypatch, tmp_path):
    monkeypatch.setattr(markdown_pipeline, "is_pandoc_available", lambda: False)

    with pytest.raises(PandocUnavailableError):
        markdown_pipeline.convert_markdown_text_to_docx(
            "# Title",
            str(tmp_path / "out.docx"),
            engine="pandoc",
        )


def test_auto_engine_uses_pandoc_when_available(monkeypatch, tmp_path):
    output_path = tmp_path / "out.docx"
    calls = []

    monkeypatch.setattr(markdown_pipeline, "is_pandoc_available", lambda: True)

    def fake_convert(
        md_text,
        out,
        template_name,
        three_line,
        base_dir=None,
        postprocess=True,
        format_options=None,
    ):
        calls.append((md_text, out, template_name, three_line, base_dir, postprocess, format_options))
        output_path.write_bytes(b"docx")
        return PandocResult(
            output_path=str(output_path),
            compat_report=generate_compat_report([]),
            formula_result=ConvertResult(),
            formula_document_stats=FormulaDocumentStats(document_total=1, native_omml=1),
        )

    monkeypatch.setattr(markdown_pipeline, "convert_markdown_text_with_pandoc", fake_convert)

    result = markdown_pipeline.convert_markdown_text_to_docx(
        "# Title",
        str(output_path),
        template_name="academic",
        engine="auto",
    )

    assert result.engine == "pandoc"
    assert calls
    assert result.formula_document_stats.document_total == 1


def test_unknown_engine_is_rejected():
    with pytest.raises(markdown_pipeline.UnknownEngineError):
        markdown_pipeline.normalize_engine("unknown")


def test_directory_conversion_uses_pipeline(monkeypatch, tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "a.md").write_text("# A", encoding="utf-8")
    (input_dir / "b.md").write_text("# B", encoding="utf-8")
    calls = []

    def fake_convert(md_file, out_path, template_name, three_line, engine):
        calls.append((os.path.basename(md_file), os.path.basename(out_path), engine))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(b"docx")

    monkeypatch.setattr(markdown_pipeline, "convert_markdown_file_to_docx", fake_convert)

    results = markdown_pipeline.convert_markdown_directory_to_docx(
        str(input_dir),
        str(output_dir),
        engine="legacy",
    )

    assert len(results) == 2
    assert all(ok for _, _, ok, _ in results)
    assert calls == [("a.md", "a.docx", "legacy"), ("b.md", "b.docx", "legacy")]
