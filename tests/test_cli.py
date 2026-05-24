"""Unit tests for CLI module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from converter.cli import main, convert_single
from converter.templates import list_templates


def test_list_templates(capsys):
    sys.argv = ["md2wps", "--list-templates"]
    result = main()
    assert result == 0
    captured = capsys.readouterr()
    assert "academic" in captured.out
    assert "report" in captured.out


def test_convert_single_file_not_found(tmp_path):
    result = convert_single(
        str(tmp_path / "nonexistent.md"),
        None, "academic", False, False,
    )
    assert result is False


def test_convert_single_not_md_file(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello")
    result = convert_single(str(txt_file), None, "academic", False, False)
    assert result is False


def test_convert_single_success(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nWorld")
    out_file = tmp_path / "test.docx"
    result = convert_single(str(md_file), str(out_file), "academic", False, False)
    assert result is True
    assert out_file.exists()


def test_convert_single_with_template(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nWorld")
    out_file = tmp_path / "test.docx"
    for t in list_templates():
        result = convert_single(str(md_file), str(out_file), t["id"], False, False)
        assert result is True
