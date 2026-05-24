"""Unit tests for math renderer (latex2mathml pipeline)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from converter.math_renderer import (
    latex_to_mathml, latex_to_omml, latex_to_omml_para,
    HAS_LATEX2MATHML,
)


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_simple_latex_to_mathml():
    result = latex_to_mathml("x^2")
    assert result is not None
    assert "math" in result.lower()


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_fraction_latex_to_mathml():
    result = latex_to_mathml(r"\frac{a}{b}")
    assert result is not None
    assert "mfrac" in result.lower()


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_empty_latex():
    assert latex_to_mathml("") is None
    assert latex_to_mathml("   ") is None
    assert latex_to_mathml(None) is None


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_latex_to_omml():
    result = latex_to_omml("x^2")
    assert result is not None
    assert result.tag.endswith("}oMath")


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_latex_to_omml_para():
    result = latex_to_omml_para("x^2")
    assert result is not None
    assert result.tag.endswith("}oMathPara")


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_complex_formula():
    formula = r"\int_{0}^{\infty} e^{-x^2} dx"
    result = latex_to_omml(formula)
    assert result is not None


@pytest.mark.skipif(not HAS_LATEX2MATHML, reason="latex2mathml not installed")
def test_matrix_formula():
    formula = r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}"
    result = latex_to_omml(formula)
    assert result is not None


def test_no_latex2mathml_fallback():
    import converter.math_renderer as mr
    original = mr.HAS_LATEX2MATHML
    mr.HAS_LATEX2MATHML = False
    try:
        assert latex_to_mathml("x^2") is None
        assert latex_to_omml("x^2") is None
        assert latex_to_omml_para("x^2") is None
    finally:
        mr.HAS_LATEX2MATHML = original
