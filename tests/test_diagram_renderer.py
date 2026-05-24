"""Unit tests for diagram renderer."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from converter.diagram_renderer import (
    is_diagram_language, render_diagram, HAS_MATPLOTLIB, HAS_NETWORKX,
)


def test_is_diagram_language():
    assert is_diagram_language("matrix") is True
    assert is_diagram_language("chart") is True
    assert is_diagram_language("graph") is True
    assert is_diagram_language("workflow") is True
    assert is_diagram_language("python") is False
    assert is_diagram_language("") is False
    assert is_diagram_language("MATRIX") is True


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
def test_render_matrix():
    code = """name: A
1 2 3
4 5 6
7 8 9
caption: Test Matrix"""
    img_bytes, caption = render_diagram(code, "matrix")
    assert img_bytes is not None
    assert caption == "Test Matrix"
    assert len(img_bytes) > 0


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
def test_render_chart_bar():
    code = """type: bar
title: Test Chart
labels: A, B, C
values: 10, 20, 30
caption: Bar Chart"""
    img_bytes, caption = render_diagram(code, "chart")
    assert img_bytes is not None
    assert caption == "Bar Chart"


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
def test_render_workflow():
    code = """title: Test Flow
[Start]
(Process Data)
[End]
caption: Simple Flow"""
    img_bytes, caption = render_diagram(code, "workflow")
    assert img_bytes is not None
    assert caption == "Simple Flow"


@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
def test_render_graph():
    code = """directed: true
title: Test Graph
A -> B: 5
B -> C: 3
caption: Simple Graph"""
    img_bytes, caption = render_diagram(code, "graph")
    assert img_bytes is not None
    assert caption == "Simple Graph"


def test_invalid_diagram_type():
    result = render_diagram("test", "python")
    assert result == (None, None)


def test_no_matplotlib_fallback():
    import converter.diagram_renderer as dr
    original = dr.HAS_MATPLOTLIB
    dr.HAS_MATPLOTLIB = False
    try:
        img_bytes, caption = render_diagram("1 2\n3 4", "matrix")
        assert img_bytes is None
    finally:
        dr.HAS_MATPLOTLIB = original
