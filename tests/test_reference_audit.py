import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docx import Document

from converter.reference_audit import audit_reference_doc, audit_template_reference_docs


def test_audit_reference_doc_reports_missing_file(tmp_path):
    result = audit_reference_doc(tmp_path / "missing.docx")

    assert result["exists"] is False
    assert result["ok"] is False
    assert "Normal" in result["missing_required"]


def test_audit_reference_doc_accepts_basic_template(tmp_path):
    path = tmp_path / "reference.docx"
    Document().save(path)

    result = audit_reference_doc(path)

    assert result["exists"] is True
    assert result["ok"] is True
    assert "Source Code" in result["missing_recommended"]


def test_project_reference_docs_have_required_styles():
    result = audit_template_reference_docs()

    assert result["ok"] is True
    assert result["items"]
