"""Style template definitions for MD → .docx conversion."""


TEMPLATES = {
    'academic': {
        'name': '学术论文',
        'heading1': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 16, 'bold': True, 'center': True,
        },
        'heading2': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 14, 'bold': True, 'center': False,
        },
        'heading3': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 12, 'bold': True, 'center': False,
        },
        'body': {
            'font_cn': '宋体', 'font_en': 'Times New Roman',
            'size': 12, 'line_spacing': 1.5, 'first_indent': 2,
        },
        'code': {
            'font': 'Consolas', 'size': 10, 'bg_color': 'F5F5F5',
        },
        'quote': {
            'indent': 2, 'border_color': 'CCCCCC',
        },
        'table': {
            'three_line_default': True,
            'header_bold': True,
        },
        'page': {
            'width': 'A4',
            'margin_top': 2.54, 'margin_bottom': 2.54,
            'margin_left': 3.17, 'margin_right': 3.17,
        },
    },
    'homework': {
        'name': '课程作业',
        'heading1': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 12, 'bold': True, 'center': True,
        },
        'heading2': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 10.5, 'bold': True, 'center': False,
        },
        'heading3': {
            'font_cn': '黑体', 'font_en': 'Times New Roman',
            'size': 10.5, 'bold': True, 'center': False,
        },
        'body': {
            'font_cn': '宋体', 'font_en': 'Times New Roman',
            'size': 10.5, 'line_spacing': 1.25, 'first_indent': 2,
        },
        'code': {
            'font': 'Consolas', 'size': 9, 'bg_color': 'F5F5F5',
        },
        'quote': {
            'indent': 2, 'border_color': 'CCCCCC',
        },
        'table': {
            'three_line_default': False,
            'header_bold': True,
        },
        'page': {
            'width': 'A4',
            'margin_top': 2.54, 'margin_bottom': 2.54,
            'margin_left': 2.54, 'margin_right': 2.54,
        },
    },
    'report': {
        'name': '工作文档',
        'heading1': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': 16, 'bold': True, 'center': False,
        },
        'heading2': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': 14, 'bold': True, 'center': False,
        },
        'heading3': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': 12, 'bold': True, 'center': False,
        },
        'body': {
            'font_cn': '微软雅黑', 'font_en': 'Calibri',
            'size': 10.5, 'line_spacing': 1.15, 'first_indent': 0,
        },
        'code': {
            'font': 'Consolas', 'size': 10, 'bg_color': 'F2F2F2',
        },
        'quote': {
            'indent': 1.5, 'border_color': '4472C4',
        },
        'table': {
            'three_line_default': False,
            'header_bold': True,
        },
        'page': {
            'width': 'A4',
            'margin_top': 2.5, 'margin_bottom': 2.5,
            'margin_left': 2.5, 'margin_right': 2.5,
        },
    },
}

DEFAULT_TEMPLATE = 'academic'


def get_template(name: str | None = None) -> dict:
    """Get template config by name. Returns default if name is None or invalid."""
    if name is None or name not in TEMPLATES:
        return TEMPLATES[DEFAULT_TEMPLATE]
    return TEMPLATES[name]


def list_templates() -> list[dict]:
    """List available templates as [{id, name}, ...]."""
    return [{'id': k, 'name': v['name']} for k, v in TEMPLATES.items()]
