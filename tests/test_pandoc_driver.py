import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from converter import pandoc_driver


def test_build_pandoc_command_uses_reference_doc(monkeypatch, tmp_path):
    monkeypatch.setattr(pandoc_driver, "resolve_pandoc_path", lambda pandoc_path=None: "/usr/bin/pandoc")

    command = pandoc_driver.build_pandoc_command(
        str(tmp_path / "in.md"),
        str(tmp_path / "out.docx"),
        template_name="academic",
        resource_path=str(tmp_path),
    )

    assert command[0] == "/usr/bin/pandoc"
    assert "-f" in command
    assert pandoc_driver.PANDOC_MARKDOWN_FORMAT in command
    assert "--reference-doc" in command
    assert command[command.index("--reference-doc") + 1].endswith("templates/academic.docx")
    assert "--resource-path" in command


def test_resolve_pandoc_path_reports_missing(monkeypatch):
    monkeypatch.setattr(pandoc_driver.shutil, "which", lambda name: None)

    with pytest.raises(pandoc_driver.PandocUnavailableError):
        pandoc_driver.resolve_pandoc_path()


def test_runtime_status_reports_install_hint_when_missing(monkeypatch):
    monkeypatch.setattr(pandoc_driver.shutil, "which", lambda name: None)
    monkeypatch.setattr(pandoc_driver, "pandoc_install_hint", lambda: "install pandoc")

    status = pandoc_driver.pandoc_runtime_status()

    assert status["available"] is False
    assert status["path"] is None
    assert status["install_hint"] == "install pandoc"


def test_convert_markdown_file_runs_pandoc_command(monkeypatch, tmp_path):
    md_file = tmp_path / "input.md"
    out_file = tmp_path / "output.docx"
    md_file.write_text("# Title", encoding="utf-8")
    calls = []

    monkeypatch.setattr(pandoc_driver, "resolve_pandoc_path", lambda pandoc_path=None: "/usr/bin/pandoc")

    def fake_run(command):
        calls.append(command)
        out_file.write_bytes(b"docx")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pandoc_driver, "_run_pandoc_command", fake_run)

    result = pandoc_driver.convert_markdown_file(
        str(md_file),
        str(out_file),
        postprocess=False,
    )

    assert result.output_path == str(out_file)
    assert calls
    assert calls[0][0] == "/usr/bin/pandoc"
    assert calls[0][calls[0].index("-o") + 1] == str(out_file)


def test_pandoc_command_error_is_sanitized(monkeypatch):
    command = ["/usr/bin/pandoc", "/tmp/input.md"]

    def fake_run(command, check, capture_output, text):
        raise pandoc_driver.subprocess.CalledProcessError(
            returncode=23,
            cmd=command,
            stderr="Pandoc failed at /private/var/folders/abc/secret/input.md",
        )

    monkeypatch.setattr(pandoc_driver.subprocess, "run", fake_run)

    with pytest.raises(pandoc_driver.PandocConversionError) as exc:
        pandoc_driver._run_pandoc_command(command)

    assert "退出码 23" in str(exc.value)
    assert "<temp>" in str(exc.value)
    assert "secret" not in str(exc.value)


def test_prepare_markdown_for_pandoc_renders_diagram(monkeypatch, tmp_path):
    def fake_render_diagram(code, language):
        assert language == "matrix"
        assert "1 2" in code
        return b"png-bytes", "矩阵 A"

    monkeypatch.setattr(
        "converter.diagram_renderer.render_diagram",
        fake_render_diagram,
    )

    prepared = pandoc_driver.prepare_markdown_for_pandoc(
        "Before\n\n```matrix\n1 2\n3 4\ncaption: 矩阵 A\n```\n\nAfter",
        str(tmp_path),
        base_dir=str(tmp_path / "assets"),
    )

    prepared_text = open(prepared.input_path, encoding="utf-8").read()

    assert prepared.diagram_count == 1
    assert "![矩阵 A](pandoc-diagram-1.png)" in prepared_text
    assert (tmp_path / "pandoc-diagram-1.png").read_bytes() == b"png-bytes"
    assert str(tmp_path) in prepared.resource_path
