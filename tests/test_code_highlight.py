"""Unit tests for code syntax highlighting."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from docx import Document
from converter.elements.code import add_code_block, _tokenize_code, _get_lexer, HAS_PYGMENTS
from converter.md_parser import Token


@pytest.fixture
def doc():
    return Document()


@pytest.fixture
def template_config():
    return {
        "code": {
            "font": "Consolas",
            "size": 10,
            "bg_color": "F5F5F5",
        }
    }


def test_empty_code_block(doc, template_config):
    token = Token(type="code", content="", attrs={})
    result = add_code_block(doc, token, template_config)
    assert result == []


def test_simple_code_block(doc, template_config):
    token = Token(type="code", content="print('hello')", attrs={})
    paragraphs = add_code_block(doc, token, template_config)
    assert len(paragraphs) >= 1


def test_multiline_code_block(doc, template_config):
    code = "def foo():\n    return 42\n"
    token = Token(type="code", content=code, attrs={})
    paragraphs = add_code_block(doc, token, template_config)
    assert len(paragraphs) >= 1


@pytest.mark.skipif(not HAS_PYGMENTS, reason="Pygments not installed")
def test_syntax_highlighting_with_language(doc, template_config):
    code = "def hello():\n    print('world')"
    token = Token(type="code", content=code, attrs={"language": "python"})
    paragraphs = add_code_block(doc, token, template_config)
    assert len(paragraphs) >= 2


@pytest.mark.skipif(not HAS_PYGMENTS, reason="Pygments not installed")
def test_lexer_aliases():
    from pygments.lexers import PythonLexer
    assert isinstance(_get_lexer("py"), PythonLexer)
    assert isinstance(_get_lexer("python"), PythonLexer)
    js_lexer = _get_lexer("js")
    assert js_lexer is not None


@pytest.mark.skipif(not HAS_PYGMENTS, reason="Pygments not installed")
def test_tokenize_code():
    tokens = _tokenize_code("x = 1", "python")
    assert len(tokens) > 0
    assert all(isinstance(t, tuple) and len(t) == 2 for t in tokens)


def test_no_pygments_fallback(doc, template_config):
    import converter.elements.code as code_module
    original = code_module.HAS_PYGMENTS
    code_module.HAS_PYGMENTS = False
    try:
        token = Token(type="code", content="x = 1", attrs={"language": "python"})
        paragraphs = add_code_block(doc, token, template_config)
        assert len(paragraphs) >= 1
    finally:
        code_module.HAS_PYGMENTS = original
