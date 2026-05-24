import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from converter.wps_paste import convert_paste_text


def test_inline_dollar_math_to_wps_code():
    result = convert_paste_text("公式：$E=mc^2$")

    assert result["text"] == "公式：E=mc^2"
    assert result["stats"]["formula_count"] == 1
    assert result["stats"]["dollars_removed"] == 2


def test_display_dollar_math_to_wps_code():
    result = convert_paste_text("前文\n$$\n\\frac{a}{b}\n$$\n后文")

    assert result["text"] == "前文\n\\frac{a}{b}\n后文"
    assert result["stats"]["formula_count"] == 1
    assert result["stats"]["dollars_removed"] == 4


def test_parentheses_and_brackets_math_delimiters():
    result = convert_paste_text(r"\(x_1+x_2\) 与 \[\sum_i x_i\]")

    assert result["text"] == r"x_1+x_2 与 \sum_i x_i"
    assert result["stats"]["formula_count"] == 2


def test_remaining_dollar_characters_are_removed():
    result = convert_paste_text(r"价格 \$5，公式 $x^2$，未闭合 $y")

    assert result["text"] == "价格 5，公式 x^2，未闭合 y"
    assert result["stats"]["formula_count"] == 1
    assert result["stats"]["dollars_removed"] == 4
