"""User-facing document format options.

This module keeps the web UI's simple controls separate from the template
definitions. Options are intentionally small and whitelisted so uploaded JSON
cannot mutate arbitrary template fields.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from converter.templates import get_template


ALLOWED_CN_FONTS = {"宋体", "仿宋", "黑体", "微软雅黑", "楷体"}
ALLOWED_EN_FONTS = {"Times New Roman", "Arial", "Calibri", "Cambria", "Consolas"}
ALLOWED_FONT_SIZES = {"三号", "小三", "四号", "小四", "五号", "小五"}
ALLOWED_LINE_SPACING = {"1.15倍", "1.25倍", "1.5倍", "2倍", "20磅", "22磅", "24磅"}
ALLOWED_INDENTS = {"0字符", "1字符", "2字符"}
ALLOWED_ALIGNMENTS = {"左对齐", "居中对齐", "右对齐", "两端对齐"}

PAGE_MARGIN_PRESETS: dict[str, dict[str, str]] = {
    "normal": {
        "margin_top": "2.54厘米",
        "margin_bottom": "2.54厘米",
        "margin_left": "2.54厘米",
        "margin_right": "2.54厘米",
    },
    "thesis": {
        "margin_top": "2.54厘米",
        "margin_bottom": "2.54厘米",
        "margin_left": "3.17厘米",
        "margin_right": "3.17厘米",
    },
    "narrow": {
        "margin_top": "1.8厘米",
        "margin_bottom": "1.8厘米",
        "margin_left": "1.8厘米",
        "margin_right": "1.8厘米",
    },
}

FORMAT_PRESETS: dict[str, dict[str, Any]] = {
    "template": {
        "id": "template",
        "name": "跟随模板",
        "description": "只使用所选模板本身的格式。",
        "options": {},
    },
    "academic": {
        "id": "academic",
        "name": "论文常用",
        "description": "宋体小四、1.5 倍行距、首行缩进、论文页边距。",
        "options": {
            "body": {
                "font_cn": "宋体",
                "font_en": "Times New Roman",
                "size": "小四",
                "line_spacing": "1.5倍",
                "first_indent": "2字符",
                "alignment": "两端对齐",
            },
            "page": {"margin_preset": "thesis"},
            "heading": {"numbering": True, "alignment": "左对齐"},
            "table": {"three_line_default": True},
            "footer": {"page_number": True},
        },
    },
    "office": {
        "id": "office",
        "name": "办公清爽",
        "description": "微软雅黑五号、1.25 倍行距、窄首行缩进，适合报告。",
        "options": {
            "body": {
                "font_cn": "微软雅黑",
                "font_en": "Calibri",
                "size": "五号",
                "line_spacing": "1.25倍",
                "first_indent": "0字符",
                "alignment": "两端对齐",
            },
            "page": {"margin_preset": "normal"},
            "heading": {"numbering": True, "alignment": "左对齐"},
            "table": {"three_line_default": False},
            "footer": {"page_number": True},
        },
    },
    "compact": {
        "id": "compact",
        "name": "紧凑打印",
        "description": "五号字、1.15 倍行距、窄页边距，节省页数。",
        "options": {
            "body": {
                "font_cn": "宋体",
                "font_en": "Times New Roman",
                "size": "五号",
                "line_spacing": "1.15倍",
                "first_indent": "0字符",
                "alignment": "两端对齐",
            },
            "page": {"margin_preset": "narrow"},
            "heading": {"numbering": True, "alignment": "左对齐"},
            "table": {"three_line_default": False},
            "footer": {"page_number": True},
        },
    },
}


def list_format_presets() -> dict[str, Any]:
    return {
        "presets": [
            {
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
                "options": item["options"],
            }
            for item in FORMAT_PRESETS.values()
        ],
        "choices": {
            "font_cn": sorted(ALLOWED_CN_FONTS),
            "font_en": sorted(ALLOWED_EN_FONTS),
            "font_size": ["五号", "小四", "四号", "小三", "三号"],
            "line_spacing": ["1.15倍", "1.25倍", "1.5倍", "20磅", "22磅", "24磅"],
            "first_indent": ["0字符", "1字符", "2字符"],
            "alignment": ["左对齐", "居中对齐", "两端对齐"],
            "margin_preset": list(PAGE_MARGIN_PRESETS.keys()),
        },
    }


def parse_format_options(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return normalize_format_options(raw)
    if not isinstance(raw, str):
        raise ValueError("format_options 必须是 JSON 字符串")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError("format_options 不是有效 JSON") from e
    if not isinstance(data, dict):
        raise ValueError("format_options 必须是 JSON 对象")
    return normalize_format_options(data)


def normalize_format_options(options: dict[str, Any] | None) -> dict[str, Any]:
    if not options:
        return {}

    normalized: dict[str, Any] = {}

    body = options.get("body")
    if isinstance(body, dict):
        body_out: dict[str, Any] = {}
        _copy_if_allowed(body, body_out, "font_cn", ALLOWED_CN_FONTS)
        _copy_if_allowed(body, body_out, "font_en", ALLOWED_EN_FONTS)
        _copy_if_allowed(body, body_out, "size", ALLOWED_FONT_SIZES)
        _copy_if_allowed(body, body_out, "line_spacing", ALLOWED_LINE_SPACING)
        _copy_if_allowed(body, body_out, "first_indent", ALLOWED_INDENTS)
        _copy_if_allowed(body, body_out, "alignment", ALLOWED_ALIGNMENTS)
        if body_out:
            normalized["body"] = body_out

    heading = options.get("heading")
    if isinstance(heading, dict):
        heading_out: dict[str, Any] = {}
        if isinstance(heading.get("numbering"), bool):
            heading_out["numbering"] = heading["numbering"]
        _copy_if_allowed(heading, heading_out, "alignment", ALLOWED_ALIGNMENTS)
        if heading_out:
            normalized["heading"] = heading_out

    page = options.get("page")
    if isinstance(page, dict):
        margin_preset = page.get("margin_preset")
        if margin_preset in PAGE_MARGIN_PRESETS:
            normalized["page"] = {"margin_preset": margin_preset}

    table = options.get("table")
    if isinstance(table, dict):
        table_out: dict[str, Any] = {}
        if isinstance(table.get("three_line_default"), bool):
            table_out["three_line_default"] = table["three_line_default"]
        if isinstance(table.get("header_bold"), bool):
            table_out["header_bold"] = table["header_bold"]
        if table_out:
            normalized["table"] = table_out

    footer = options.get("footer")
    if isinstance(footer, dict):
        footer_out: dict[str, Any] = {}
        if isinstance(footer.get("page_number"), bool):
            footer_out["page_number"] = footer["page_number"]
        if footer_out:
            normalized["footer"] = footer_out

    return normalized


def build_effective_template(
    template_name: str | None = None,
    format_options: dict[str, Any] | None = None,
    three_line_override: bool | None = None,
) -> dict[str, Any]:
    config = copy.deepcopy(get_template(template_name))
    options = normalize_format_options(format_options)

    if "body" in options:
        config.setdefault("body", {}).update(options["body"])

    heading = options.get("heading", {})
    if heading:
        for level in ("heading1", "heading2", "heading3"):
            heading_config = config.setdefault(level, {})
            if "alignment" in heading:
                heading_config["alignment"] = heading["alignment"]
            if "numbering" in heading:
                numbering = heading_config.setdefault("numbering", {})
                numbering["enabled"] = heading["numbering"]

    page = options.get("page", {})
    if page.get("margin_preset") in PAGE_MARGIN_PRESETS:
        config.setdefault("page", {}).update(PAGE_MARGIN_PRESETS[page["margin_preset"]])

    if "table" in options:
        config.setdefault("table", {}).update(options["table"])
    if three_line_override is not None:
        config.setdefault("table", {})["three_line_default"] = three_line_override

    if "footer" in options:
        config.setdefault("footer", {}).update(options["footer"])

    return config


def _copy_if_allowed(src: dict[str, Any], dest: dict[str, Any], key: str, allowed: set[str]):
    value = src.get(key)
    if value in allowed:
        dest[key] = value
