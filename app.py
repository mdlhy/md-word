import logging
import uuid
import os
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MD / Word 格式助手")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "MD2WPS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8972,http://localhost:8972",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_download_store: dict = {}
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TEXT_SIZE = 2 * 1024 * 1024
DOWNLOAD_TTL_SECONDS = 30 * 60


class PasteConvertRequest(BaseModel):
    text: str = ""


def _safe_unlink(file_path: str):
    try:
        os.unlink(file_path)
    except OSError:
        pass


def _cleanup_download_store():
    now = time.time()
    expired = [
        download_id
        for download_id, item in _download_store.items()
        if now - item["created_at"] > DOWNLOAD_TTL_SECONDS
    ]
    for download_id in expired:
        item = _download_store.pop(download_id, None)
        if item:
            _safe_unlink(item["path"])


def _register_download(file_path: str) -> str:
    _cleanup_download_store()
    download_id = str(uuid.uuid4())
    _download_store[download_id] = {
        "path": file_path,
        "created_at": time.time(),
    }
    return download_id


def _formula_result_payload(result, document_stats=None):
    if document_stats is not None:
        stats = document_stats.to_dict()
        stats["total"] = document_stats.document_total
        stats["converted"] = document_stats.postprocessed
    else:
        stats = {
            "total": result.total,
            "document_total": result.total,
            "native_omml": 0,
            "postprocessed": result.converted,
            "converted": result.converted,
            "failed": result.failed,
            "skipped": result.skipped,
            "residual_latex": 0,
        }

    return {
        "stats": stats,
        "items": [
            {"latex": f.latex, "status": f.status, "display": f.display, "page": f.page}
            for f in result.details
        ],
    }


def _conversion_error_detail(error: Exception) -> str:
    name = error.__class__.__name__
    if name == "PandocUnavailableError":
        return str(error)
    if name == "PandocConversionError":
        return str(error)
    if name == "UnknownEngineError":
        return str(error)
    return ""


def _parse_format_options_or_400(raw: str | None):
    try:
        from converter.format_options import parse_format_options

        return parse_format_options(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/convert")
async def convert_docx(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="请上传 .docx 文件")

    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="文件过大，最大支持 50MB")
            tmp.write(content)
            input_path = tmp.name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    output_path = None
    try:
        from converter.orchestrator import convert_docx as do_convert

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name

        result = do_convert(input_path, output_path)
        
        download_id = _register_download(output_path)
        output_path = None  # ownership transferred to store
        formula_payload = _formula_result_payload(result)
        
        return JSONResponse({
            "success": True,
            "stats": formula_payload["stats"],
            "formulas": formula_payload["items"],
            "download_id": download_id,
        })
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="转换失败，请重试")
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass
        if output_path:
            try:
                os.unlink(output_path)
            except OSError:
                pass


@app.get("/api/download/{download_id}")
async def download_docx(download_id: str):
    _cleanup_download_store()
    item = _download_store.pop(download_id, None)
    file_path = item["path"] if item else None
    if not file_path or not os.path.exists(file_path):
        if file_path:
            _safe_unlink(file_path)
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="converted.docx",
        background=BackgroundTask(_safe_unlink, file_path),
    )


@app.post("/api/convert-md")
async def convert_md(
    file: UploadFile = File(...),
    template: str = Form("academic"),
    three_line: str = Form("false"),
    engine: str = Form("auto"),
    format_options: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="请上传 .md 文件")

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件过大")
        md_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read .md file: {e}")
        raise HTTPException(status_code=500, detail="文件读取失败")

    output_path = None
    try:
        use_three_line = three_line == "true"
        parsed_format_options = _parse_format_options_or_400(format_options)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name

        from converter.markdown_pipeline import convert_markdown_text_to_docx

        result = convert_markdown_text_to_docx(
            md_text,
            output_path,
            template,
            use_three_line,
            engine=engine,
            format_options=parsed_format_options,
        )
        report = result.compat_report

        download_id = _register_download(output_path)
        output_path = None
        formula_payload = _formula_result_payload(
            result.formula_result,
            result.formula_document_stats,
        )

        return JSONResponse({
            "engine": result.engine,
            "download_id": download_id,
            "compat_report": {
                "summary": report.summary,
                "items": [
                    {"type": item.element_type, "risk": item.risk, "description": item.description}
                    for item in report.items
                ]
            },
            "stats": {
                "total": len(report.items),
                "converted": report.summary.get("low", 0) + report.summary.get("medium", 0),
                "failed": report.summary.get("high", 0),
                "skipped": 0,
            },
            "formula_stats": formula_payload["stats"],
            "formulas": formula_payload["items"],
        })
    except HTTPException:
        raise
    except Exception as e:
        detail = _conversion_error_detail(e)
        if detail:
            status_code = 400 if e.__class__.__name__ == "UnknownEngineError" else 422
            raise HTTPException(status_code=status_code, detail=detail)
        logger.error(f"MD conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="转换失败，请重试")
    finally:
        if output_path:
            try:
                os.unlink(output_path)
            except OSError:
                pass


@app.post("/api/repair")
async def repair(
    file: UploadFile = File(...),
    template: str = Form("academic"),
    format_options: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="请上传 .docx 文件")

    input_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="文件过大")
            tmp.write(content)
            input_path = tmp.name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    output_path = None
    try:
        from converter.docx_repair import repair_docx

        parsed_format_options = _parse_format_options_or_400(format_options)
        doc, report = repair_docx(input_path, template, format_options=parsed_format_options)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name
        doc.save(output_path)

        download_id = _register_download(output_path)
        output_path = None

        return JSONResponse({
            "download_id": download_id,
            "compat_report": {
                "summary": report.summary,
                "items": [
                    {"type": item.element_type, "risk": item.risk, "description": item.description}
                    for item in report.items
                ]
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Repair failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="修复失败，请重试")
    finally:
        if input_path:
            try:
                os.unlink(input_path)
            except OSError:
                pass
        if output_path:
            try:
                os.unlink(output_path)
            except OSError:
                pass


@app.get("/api/templates")
async def get_templates():
    from converter.templates import list_templates
    return JSONResponse({"templates": list_templates()})


@app.get("/api/format-presets")
async def get_format_presets():
    from converter.format_options import list_format_presets

    return JSONResponse(list_format_presets())


@app.get("/api/runtime")
async def runtime_status():
    from converter.pandoc_driver import pandoc_runtime_status
    from converter.reference_audit import audit_template_reference_docs

    return JSONResponse({
        "pandoc": pandoc_runtime_status(),
        "reference_docs": audit_template_reference_docs(),
        "remote_images": {
            "enabled": os.environ.get("MD2WPS_ALLOW_REMOTE_IMAGES", "").lower() in {"1", "true", "yes"},
        },
    })


@app.post("/api/paste-wps")
async def paste_wps(request: PasteConvertRequest):
    if len(request.text.encode("utf-8")) > MAX_TEXT_SIZE:
        raise HTTPException(status_code=413, detail="文本过大，最大支持 2MB")

    from converter.wps_paste import convert_paste_text

    return JSONResponse(convert_paste_text(request.text))


web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
