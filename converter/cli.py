"""Command-line interface for MD→WPS converter."""

import argparse
import logging
import os
import sys

from converter.markdown_pipeline import (
    convert_markdown_directory_to_docx,
    convert_markdown_file_to_docx,
)
from converter.pandoc_driver import pandoc_runtime_status
from converter.reference_audit import audit_template_reference_docs
from converter.templates import list_templates


def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def convert_single(input_path, output_path, template, three_line, verbose, engine="auto"):
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return False

    if not input_path.lower().endswith(".md"):
        print(f"Error: Expected a .md file: {input_path}", file=sys.stderr)
        return False

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".docx"

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        result = convert_markdown_file_to_docx(
            input_path,
            output_path,
            template,
            three_line,
            engine,
        )
        report = result.compat_report

        print(f"✓ {input_path} → {output_path}")
        if verbose:
            print(f"  Engine: {result.engine}")
            print(f"  Compatibility: {report.summary}")
        return True
    except Exception as e:
        print(f"✗ {input_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        prog="md2wps",
        description="MD→WPS 一键排版：将 Markdown 转换为 WPS 友好的 .docx 文件",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Markdown 文件或目录路径",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件或目录路径",
    )
    parser.add_argument(
        "-t", "--template",
        default="academic",
        choices=[t["id"] for t in list_templates()],
        help="样式模板 (默认: academic)",
    )
    parser.add_argument(
        "--three-line",
        action="store_true",
        help="使用三线表样式",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="递归处理子目录",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "pandoc", "legacy"],
        default=os.environ.get("MD2WPS_ENGINE", "auto"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="列出所有可用模板",
    )
    parser.add_argument(
        "--check-runtime",
        action="store_true",
        help="检查 Pandoc 等外部运行环境",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.list_templates:
        print("可用模板:")
        for t in list_templates():
            print(f"  {t['id']:15s} - {t['name']}")
        return 0

    if args.check_runtime:
        status = pandoc_runtime_status()
        reference_docs = audit_template_reference_docs()
        print("Pandoc:")
        print(f"  available: {status['available']}")
        print(f"  version: {status['version'] or '-'}")
        print(f"  path: {status['path'] or '-'}")
        if status["install_hint"]:
            print(f"  install: {status['install_hint']}")
        print("Reference docs:")
        print(f"  ok: {reference_docs['ok']}")
        for template_id, item in reference_docs["items"].items():
            missing = item["missing_required"]
            recommended = item["missing_recommended"]
            print(f"  {template_id}: {'ok' if item['ok'] else 'missing required'}")
            if missing:
                print(f"    missing: {', '.join(missing)}")
            if recommended:
                print(f"    recommended: {', '.join(recommended)}")
        return 0 if status["available"] and reference_docs["ok"] else 1

    if not args.input:
        parser.error("需要指定输入文件或目录")

    if os.path.isdir(args.input):
        results = convert_markdown_directory_to_docx(
            args.input, args.output, args.template,
            args.three_line, args.recursive, args.engine,
        )
        success = sum(1 for *_, ok, _ in results if ok)
        failed = len(results) - success
        print(f"\n完成: {success} 成功, {failed} 失败")
        return 0 if failed == 0 else 1
    else:
        ok = convert_single(
            args.input, args.output, args.template,
            args.three_line, args.verbose, args.engine,
        )
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
