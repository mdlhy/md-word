import logging
import uuid
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LaTeX Formula Converter")

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

    try:
        from converter.orchestrator import convert_docx as do_convert

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out_tmp:
            output_path = out_tmp.name

        result = do_convert(input_path, output_path)
        
        download_id = str(uuid.uuid4())
        _download_store[download_id] = output_path
        
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
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


@app.get("/api/download/{download_id}")
async def download_docx(download_id: str):
    file_path = _download_store.get(download_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="converted.docx",
    )


web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
