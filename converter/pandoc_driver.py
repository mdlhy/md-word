from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from converter.compat_report import CompatItem, CompatReport, generate_compat_report
from converter.formula_stats import FormulaDocumentStats, inspect_document_formulas
from converter.models import ConvertResult


class PandocUnavailableError(RuntimeError):
    pass


class PandocConversionError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, stderr: str = "", stdout: str = ""):
        self.command = command
        self.returncode = returncode
        self.stderr = _clean_pandoc_output(stderr)
        self.stdout = _clean_pandoc_output(stdout)
        detail = self.stderr or self.stdout or "Pandoc 未返回错误详情"
        super().__init__(f"Pandoc 转换失败（退出码 {returncode}）：{detail}")


@dataclass
class PandocResult:
    output_path: str
    compat_report: CompatReport
    formula_result: ConvertResult
    formula_document_stats: FormulaDocumentStats


@dataclass
class PreparedMarkdown:
    input_path: str
    resource_path: str | None
    diagram_count: int = 0


PANDOC_MARKDOWN_FORMAT = (
    "markdown"
    "+pipe_tables"
    "+fenced_code_blocks"
    "+backtick_code_blocks"
    "+strikeout"
    "+task_lists"
    "+tex_math_dollars"
    "+tex_math_single_backslash"
)

_FENCED_CODE_RE = re.compile(
    r"(?P<indent>^ {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n"
    r"(?P<code>[\s\S]*?)\n(?P=indent)(?P=fence)[ \t]*$",
    re.MULTILINE,
)


def resolve_pandoc_path(pandoc_path: str | None = None) -> str:
    candidate = pandoc_path or shutil.which("pandoc")
    if not candidate:
        raise PandocUnavailableError("pandoc 未安装或不在 PATH 中")
    return candidate


def is_pandoc_available(pandoc_path: str | None = None) -> bool:
    try:
        resolve_pandoc_path(pandoc_path)
        return True
    except PandocUnavailableError:
        return False


def pandoc_version(pandoc_path: str | None = None) -> str | None:
    try:
        candidate = resolve_pandoc_path(pandoc_path)
    except PandocUnavailableError:
        return None

    try:
        result = subprocess.run(
            [candidate, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    return first_line.strip() or None


def pandoc_install_hint() -> str:
    system = platform.system().lower()
    if system == "darwin":
        if shutil.which("brew"):
            return "brew install pandoc"
        return "安装 Homebrew 后运行：brew install pandoc"
    if system == "linux":
        return "使用系统包管理器安装，例如：sudo apt install pandoc"
    if system == "windows":
        return "使用 winget install JohnMacFarlane.Pandoc，或从 pandoc.org 下载安装包"
    return "请从 https://pandoc.org/installing.html 安装 Pandoc"


def pandoc_runtime_status() -> dict[str, str | bool | None]:
    path = shutil.which("pandoc")
    version = pandoc_version(path) if path else None
    return {
        "available": bool(path and version),
        "path": path,
        "version": version,
        "install_hint": None if path and version else pandoc_install_hint(),
    }


def _clean_pandoc_output(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    text = re.sub(r"/(?:private/)?var/folders/[^\s'\"<>]+", "<temp>", text)
    text = re.sub(r"/tmp/[^\s'\"<>]+", "<temp>", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _run_pandoc_command(command: list[str]):
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise PandocConversionError(
            command=command,
            returncode=e.returncode,
            stderr=e.stderr or "",
            stdout=e.stdout or "",
        ) from e


def reference_doc_path(template_name: str) -> str:
    path = Path(__file__).resolve().parent.parent / "templates" / f"{template_name}.docx"
    if not path.exists():
        raise FileNotFoundError(f"Reference docx not found: {path}")
    return str(path)


def build_pandoc_command(
    input_path: str,
    output_path: str,
    template_name: str = "academic",
    resource_path: str | None = None,
    pandoc_path: str | None = None,
) -> list[str]:
    command = [
        resolve_pandoc_path(pandoc_path),
        input_path,
        "-f",
        PANDOC_MARKDOWN_FORMAT,
        "-t",
        "docx",
        "--reference-doc",
        reference_doc_path(template_name),
        "-o",
        output_path,
    ]
    if resource_path:
        command.extend(["--resource-path", resource_path])
    return command


def prepare_markdown_for_pandoc(
    md_text: str,
    work_dir: str,
    base_dir: str | None = None,
) -> PreparedMarkdown:
    os.makedirs(work_dir, exist_ok=True)
    diagram_count = 0

    def replace_diagram(match: re.Match[str]) -> str:
        nonlocal diagram_count
        info = match.group("info").strip()
        language = info.split()[0] if info else ""
        if not language:
            return match.group(0)

        from converter.diagram_renderer import is_diagram_language, render_diagram

        if not is_diagram_language(language):
            return match.group(0)

        image_data, caption = render_diagram(match.group("code"), language)
        if not image_data:
            return match.group(0)

        diagram_count += 1
        filename = f"pandoc-diagram-{diagram_count}.png"
        image_path = os.path.join(work_dir, filename)
        with open(image_path, "wb") as f:
            f.write(image_data)

        alt_text = _escape_markdown_alt_text(caption or f"{language} diagram")
        return f"\n![{alt_text}]({filename})\n"

    prepared_text = _FENCED_CODE_RE.sub(replace_diagram, md_text)
    input_path = os.path.join(work_dir, "input.md")
    with open(input_path, "w", encoding="utf-8") as f:
        f.write(prepared_text)

    resource_paths = [work_dir]
    if base_dir:
        resource_paths.append(os.path.abspath(base_dir))

    return PreparedMarkdown(
        input_path=input_path,
        resource_path=os.pathsep.join(resource_paths),
        diagram_count=diagram_count,
    )


def _escape_markdown_alt_text(text: str) -> str:
    return text.replace("\n", " ").replace("[", "(").replace("]", ")").strip()


def convert_markdown_file(
    input_path: str,
    output_path: str,
    template_name: str = "academic",
    three_line: bool = False,
    pandoc_path: str | None = None,
    postprocess: bool = True,
    format_options: dict | None = None,
) -> PandocResult:
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    with tempfile.TemporaryDirectory(prefix="md2wps-pandoc-") as work_dir:
        prepared = prepare_markdown_for_pandoc(
            md_text,
            work_dir,
            base_dir=os.path.dirname(input_path),
        )
        command = build_pandoc_command(
            input_path=prepared.input_path,
            output_path=output_path,
            template_name=template_name,
            resource_path=prepared.resource_path,
            pandoc_path=pandoc_path,
        )
        _run_pandoc_command(command)

    if not postprocess:
        return PandocResult(
            output_path=output_path,
            compat_report=generate_compat_report([]),
            formula_result=ConvertResult(),
            formula_document_stats=FormulaDocumentStats(),
        )

    return postprocess_docx(output_path, template_name, three_line, format_options=format_options)


def convert_markdown_text(
    md_text: str,
    output_path: str,
    template_name: str = "academic",
    three_line: bool = False,
    base_dir: str | None = None,
    pandoc_path: str | None = None,
    postprocess: bool = True,
    format_options: dict | None = None,
) -> PandocResult:
    with tempfile.TemporaryDirectory(prefix="md2wps-pandoc-") as work_dir:
        prepared = prepare_markdown_for_pandoc(md_text, work_dir, base_dir=base_dir)
        command = build_pandoc_command(
            input_path=prepared.input_path,
            output_path=os.path.abspath(output_path),
            template_name=template_name,
            resource_path=prepared.resource_path,
            pandoc_path=pandoc_path,
        )
        _run_pandoc_command(command)

    if not postprocess:
        return PandocResult(
            output_path=os.path.abspath(output_path),
            compat_report=generate_compat_report([]),
            formula_result=ConvertResult(),
            formula_document_stats=FormulaDocumentStats(),
        )

    return postprocess_docx(output_path, template_name, three_line, format_options=format_options)


def postprocess_docx(
    output_path: str,
    template_name: str,
    three_line: bool = False,
    format_options: dict | None = None,
) -> PandocResult:
    from converter.docx_repair import repair_docx
    from converter.orchestrator import convert_docx_in_memory

    doc, compat_report = repair_docx(
        output_path,
        template_name,
        fix_formulas=False,
        format_options=format_options,
        three_line_override=three_line if three_line else None,
    )
    formula_result = convert_docx_in_memory(doc)
    formula_document_stats = inspect_document_formulas(doc, formula_result)
    compat_items = list(compat_report.items)
    if formula_result.converted > 0:
        compat_items.append(CompatItem(
            element_type="formula",
            risk="low",
            description=f"公式修复: {formula_result.converted} 个公式转换成功",
        ))
    if formula_result.failed > 0:
        compat_items.append(CompatItem(
            element_type="formula",
            risk="high",
            description=f"公式修复: {formula_result.failed} 个公式转换失败",
        ))
    compat_report = generate_compat_report(compat_items)
    doc.save(output_path)

    return PandocResult(
        output_path=os.path.abspath(output_path),
        compat_report=compat_report,
        formula_result=formula_result,
        formula_document_stats=formula_document_stats,
    )
