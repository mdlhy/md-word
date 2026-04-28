import logging
import uuid
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MD→WPS 一键排版")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_download_store: dict = {}
MAX_FILE_SIZE = 50 * 1024 * 1024


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
        
        download_id = str(uuid.uuid4())
        _download_store[download_id] = output_path
        output_path = None  # ownership transferred to store
        
        return JSONResponse({
            "success": True,
            "stats": {
                "total": result.total,
                "converted": result.converted,
                "failed": result.failed,
                "skipped": result.skipped,
            },
            "formulas": [
                {"latex": f.latex, "status": f.status, "display": f.display}
                for f in result.details
            ],
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
    file_path = _download_store.pop(download_id, None)
    if not file_path or not os.path.exists(file_path):
        if file_path:
            try:
                os.unlink(file_path)
            except OSError:
                pass
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="converted.docx",
    )


@app.post("/api/convert-md")
async def convert_md(file: UploadFile = File(...), template: str = Form("academic"), three_line: str = Form("false")):
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
        from converter.md_converter import convert_md_to_docx

        doc, report = convert_md_to_docx(md_text, template, three_line == "true")

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name
        doc.save(output_path)

        download_id = str(uuid.uuid4())
        _download_store[download_id] = output_path
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
            "stats": {
                "total": len(report.items),
                "converted": report.summary.get("low", 0) + report.summary.get("medium", 0),
                "failed": report.summary.get("high", 0),
                "skipped": 0,
            },
            "formulas": [],
        })
    except Exception as e:
        logger.error(f"MD conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="转换失败，请重试")
    finally:
        if output_path:
            try:
                os.unlink(output_path)
            except OSError:
                pass


@app.post("/api/repair")
async def repair(file: UploadFile = File(...), template: str = Form("academic")):
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

        doc, report = repair_docx(input_path, template)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name
        doc.save(output_path)

        download_id = str(uuid.uuid4())
        _download_store[download_id] = output_path
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


web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
