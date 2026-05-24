"""Centralized style presets for MD → DOCX conversion.

All visual constants (fonts, colors, spacing) are defined here.
Modules should import from this file instead of hardcoding values.

Usage:
    from converter.style_presets import CODE_FONT, CODE_BG_COLOR, SYNTAX_COLORS
"""

from docx.shared import Pt, RGBColor

# ============================================================
# Code Block Styles
# ============================================================

CODE_FONT = "Consolas"
CODE_FONT_SIZE = Pt(10)
CODE_BG_COLOR = "E8E8E8"
CODE_BORDER_COLOR = "CCCCCC"
CODE_LINE_SPACING = 1.0
CODE_INDENT_LEFT = Pt(10)
CODE_INDENT_RIGHT = Pt(10)
CODE_SPACE_BEFORE = Pt(2)
CODE_SPACE_AFTER = Pt(8)

# ============================================================
# Syntax Highlighting Colors (VS Code Light Theme)
# ============================================================

try:
    from pygments.token import Token as PygmentsToken

    SYNTAX_COLORS = {
        PygmentsToken.Keyword: RGBColor(0x00, 0x00, 0xCC),  # Blue
        PygmentsToken.Keyword.Constant: RGBColor(0x00, 0x00, 0xCC),
        PygmentsToken.Keyword.Declaration: RGBColor(0x00, 0x00, 0xCC),
        PygmentsToken.Keyword.Namespace: RGBColor(0x7B, 0x30, 0x7B),  # Purple
        PygmentsToken.Keyword.Type: RGBColor(0x26, 0x7F, 0x99),  # Teal
        PygmentsToken.Name.Function: RGBColor(0x79, 0x5E, 0x26),  # Dark Yellow
        PygmentsToken.Name.Function.Magic: RGBColor(0x79, 0x5E, 0x26),
        PygmentsToken.Name.Class: RGBColor(0x26, 0x7F, 0x99),  # Teal
        PygmentsToken.Name.Decorator: RGBColor(0x79, 0x5E, 0x26),  # Dark Yellow
        PygmentsToken.Name.Builtin: RGBColor(0x26, 0x7F, 0x99),  # Teal
        PygmentsToken.Name.Builtin.Pseudo: RGBColor(0x00, 0x00, 0xCC),
        PygmentsToken.Literal.String: RGBColor(0xA3, 0x15, 0x15),  # Red
        PygmentsToken.Literal.String.Doc: RGBColor(0xA3, 0x15, 0x15),
        PygmentsToken.Literal.String.Single: RGBColor(0xA3, 0x15, 0x15),
        PygmentsToken.Literal.String.Double: RGBColor(0xA3, 0x15, 0x15),
        PygmentsToken.Literal.String.Escape: RGBColor(0xEE, 0x00, 0x00),
        PygmentsToken.Literal.String.Interpol: RGBColor(0xEE, 0x00, 0x00),
        PygmentsToken.Literal.String.Affix: RGBColor(0x00, 0x00, 0xCC),
        PygmentsToken.Literal.Number: RGBColor(0x09, 0x88, 0x58),  # Green
        PygmentsToken.Literal.Number.Integer: RGBColor(0x09, 0x88, 0x58),
        PygmentsToken.Literal.Number.Float: RGBColor(0x09, 0x88, 0x58),
        PygmentsToken.Comment: RGBColor(0x6A, 0x99, 0x55),  # Olive Green
        PygmentsToken.Comment.Single: RGBColor(0x6A, 0x99, 0x55),
        PygmentsToken.Comment.Multiline: RGBColor(0x6A, 0x99, 0x55),
        PygmentsToken.Comment.Hashbang: RGBColor(0x6A, 0x99, 0x55),
        PygmentsToken.Operator: RGBColor(0x33, 0x33, 0x33),
        PygmentsToken.Operator.Word: RGBColor(0x00, 0x00, 0xCC),
        PygmentsToken.Punctuation: RGBColor(0x33, 0x33, 0x33),
        PygmentsToken.Name.Tag: RGBColor(0x80, 0x00, 0x00),  # HTML tags
        PygmentsToken.Name.Attribute: RGBColor(0xFF, 0x00, 0x00),  # HTML attrs
    }
except ImportError:
    SYNTAX_COLORS = {}


def get_syntax_color(token_type):
    """Get color for a Pygments token type, walking up the hierarchy."""
    t = token_type
    while t:
        if t in SYNTAX_COLORS:
            return SYNTAX_COLORS[t]
        t = t.parent
    return None


# ============================================================
# Table Styles
# ============================================================

TABLE_BORDER_COLOR = "000000"
TABLE_BORDER_SIZE_THICK = "12"
TABLE_BORDER_SIZE_THIN = "4"
TABLE_HEADER_BG = "E3F2FD"

# Three-line table (三线表) defaults
THREE_LINE_TOP_SIZE = "12"
THREE_LINE_BOTTOM_SIZE = "12"
THREE_LINE_HEADER_SIZE = "4"

# ============================================================
# Heading Styles
# ============================================================

HEADING_COLOR = "000000"

# ============================================================
# Blockquote Styles
# ============================================================

BLOCKQUOTE_BORDER_COLOR = "BBBBBB"
BLOCKQUOTE_TEXT_COLOR = RGBColor(0x55, 0x55, 0x55)
BLOCKQUOTE_INDENT = Pt(24)

# ============================================================
# Horizontal Rule
# ============================================================

HR_COLOR = "CCCCCC"
HR_SIZE = "12"

# ============================================================
# Math / Formula
# ============================================================

MATH_FALLBACK_FONT = "Consolas"
MATH_FALLBACK_ITALIC = True

# ============================================================
# Image
# ============================================================

IMAGE_MAX_WIDTH_CM = 15.0  # ~A4 content width
IMAGE_FETCH_TIMEOUT = 10  # seconds

# ============================================================
# Language Aliases for Code Highlighting
# ============================================================

LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "rb": "ruby",
    "cs": "csharp",
    "c++": "cpp",
    "c#": "csharp",
    "sh": "bash",
    "shell": "bash",
    "yml": "yaml",
    "md": "markdown",
    "tex": "latex",
    "rs": "rust",
    "kt": "kotlin",
    "m": "objectivec",
    "dockerfile": "docker",
    "plaintext": "text",
    "plain": "text",
    "txt": "text",
    "": "text",
}
