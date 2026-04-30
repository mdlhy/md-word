"""Style template definitions for MD → .docx conversion.

All font sizes and spacing values use Chinese academic notation:
  字号: '小四', '三号', '五号', etc. (see format_units.FONT_SIZE_MAP)
  行距: '1.5倍', '20磅'
  缩进: '2字符'
  对齐: '居中对齐', '两端对齐', '左对齐'
"""

TEMPLATES = {
    'academic': {
        'name': '学术论文',
        'heading1': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': '三号', 'bold': True, 'alignment': '居中对齐',
            'space_before': '0.5行', 'space_after': '0.5行',
            'numbering': {'enabled': True, 'template': '第%1章', 'suffix': 'space'},
        },
        'heading2': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': '四号', 'bold': True, 'alignment': '左对齐',
            'space_before': '0.5行', 'space_after': '0.5行',
            'numbering': {'enabled': True, 'template': '%1.%2', 'suffix': 'space'},
        },
        'heading3': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': '小四', 'bold': True, 'alignment': '左对齐',
            'numbering': {'enabled': True, 'template': '%1.%2.%3', 'suffix': 'space'},
        },
        'body': {
            'font_cn': '宋体', 'font_en': 'Times New Roman',
            'size': '小四', 'line_spacing': '1.5倍', 'first_indent': '2字符',
            'alignment': '两端对齐',
        },
        'code': {
            'font': 'Consolas', 'size': '五号', 'bg_color': 'F5F5F5',
        },
        'quote': {
            'indent': '2字符', 'border_color': 'CCCCCC',
        },
        'table': {
            'three_line_default': True,
            'header_bold': True,
            'caption_position': 'above',
            'caption_prefix': '表',
            'caption_size': '五号',
        },
        'figure': {
            'caption_position': 'below',
            'caption_prefix': '图',
            'caption_size': '五号',
        },
        'abstract': {
            'title_size': '三号', 'title_font_cn': '黑体', 'title_alignment': '居中对齐',
            'content_size': '小四',
        },
        'keywords': {
            'label_font_cn': '黑体', 'label_size': '小四',
            'content_size': '小四', 'separator': '；',
        },
        'references': {
            'title_size': '三号', 'title_font_cn': '黑体', 'title_alignment': '居中对齐',
            'entry_size': '五号', 'entry_hanging_indent': '2字符',
            'entry_numbering': '[1], [2], ...',
        },
        'page': {
            'width': 'A4',
            'margin_top': '2.54厘米', 'margin_bottom': '2.54厘米',
            'margin_left': '3.17厘米', 'margin_right': '3.17厘米',
        },
        'header': {
            'text': '', 'size': '小五', 'font_cn': '宋体',
        },
        'footer': {
            'page_number': True, 'size': '小五',
        },
    },
    'report': {
        'name': '工作文档',
        'heading1': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': '三号', 'bold': True, 'alignment': '左对齐',
            'numbering': {'enabled': True, 'template': '%1', 'suffix': 'space'},
        },
        'heading2': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': '四号', 'bold': True, 'alignment': '左对齐',
            'numbering': {'enabled': True, 'template': '%1.%2', 'suffix': 'space'},
        },
        'heading3': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': '小四', 'bold': True, 'alignment': '左对齐',
            'numbering': {'enabled': True, 'template': '%1.%2.%3', 'suffix': 'space'},
        },
        'body': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': '五号', 'line_spacing': '1.15倍', 'first_indent': '0字符',
            'alignment': '两端对齐',
        },
        'code': {
            'font': 'Consolas', 'size': '五号', 'bg_color': 'F2F2F2',
        },
        'quote': {
            'indent': '1.5字符', 'border_color': '4472C4',
        },
        'table': {
            'three_line_default': False,
            'header_bold': True,
            'caption_position': 'above',
            'caption_prefix': '表',
            'caption_size': '五号',
        },
        'figure': {
            'caption_position': 'below',
            'caption_prefix': '图',
            'caption_size': '五号',
        },
        'page': {
            'width': 'A4',
            'margin_top': '2.5厘米', 'margin_bottom': '2.5厘米',
            'margin_left': '2.5厘米', 'margin_right': '2.5厘米',
        },
        'header': {
            'text': '', 'size': '小五', 'font_cn': '微软雅黑',
        },
        'footer': {
            'page_number': True, 'size': '小五',
        },
    },
    'dialectics': {
        'name': '自然辩证法论文',
        'title': {
            'font_cn': '方正小标宋简体', 'font_en': 'Times New Roman',
            'size': '小二', 'alignment': '居中对齐',
            'space_after': '0.5行',
        },
        'author': {
            'font_cn': '楷体', 'font_en': 'Times New Roman',
            'size': '小三', 'alignment': '居中对齐',
            'space_after': '1行',
        },
        'heading1': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': '三号', 'bold': True, 'alignment': '左对齐',
            'space_before': '0.5行', 'space_after': '0.5行',
            'numbering': {'enabled': False},
        },
        'heading2': {
            'font_cn': '楷体', 'font_en': 'Times New Roman',
            'size': '小三', 'bold': True, 'alignment': '左对齐',
            'space_before': '0.5行', 'space_after': '0.5行',
            'numbering': {'enabled': False},
        },
        'heading3': {
            'font_cn': '仿宋', 'font_en': 'Times New Roman',
            'size': '四号', 'bold': True, 'alignment': '左对齐',
            'numbering': {'enabled': False},
        },
        'body': {
            'font_cn': '仿宋', 'font_en': 'Times New Roman',
            'size': '小四', 'line_spacing': '22磅', 'first_indent': '2字符',
            'alignment': '两端对齐',
        },
        'code': {
            'font': 'Consolas', 'size': '五号', 'bg_color': 'F5F5F5',
        },
        'quote': {
            'indent': '2字符', 'border_color': 'CCCCCC',
        },
        'table': {
            'three_line_default': True,
            'header_bold': True,
            'caption_position': 'above',
            'caption_prefix': '表',
            'caption_size': '五号',
            'caption_font_cn': '仿宋',
        },
        'figure': {
            'caption_position': 'below',
            'caption_prefix': '图',
            'caption_size': '五号',
            'caption_font_cn': '仿宋',
        },
        'abstract': {
            'title_size': '三号', 'title_font_cn': '黑体', 'title_alignment': '居中对齐',
            'content_size': '小四',
        },
        'keywords': {
            'label_font_cn': '黑体', 'label_size': '小四',
            'content_size': '小四', 'separator': '；',
        },
        'references': {
            'title_size': '三号', 'title_font_cn': '黑体', 'title_alignment': '居中对齐',
            'entry_size': '五号', 'entry_hanging_indent': '2字符',
            'entry_numbering': '[1], [2], ...',
        },
        'page': {
            'width': 'A4',
            'margin_top': '2.6厘米', 'margin_bottom': '2.6厘米',
            'margin_left': '2.6厘米', 'margin_right': '2.6厘米',
        },
        'header': {
            'text': '', 'size': '小五', 'font_cn': '仿宋',
        },
        'footer': {
            'page_number': True, 'size': '小五',
        },
    },
}

DEFAULT_TEMPLATE = 'academic'


def get_template(name: str | None = None) -> dict:
    if name is None or name not in TEMPLATES:
        return TEMPLATES[DEFAULT_TEMPLATE]
    return TEMPLATES[name]


def list_templates() -> list[dict]:
    return [{'id': k, 'name': v['name']} for k, v in TEMPLATES.items()]
