import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app


def test_download_store_cleanup_removes_expired_file(tmp_path, monkeypatch):
    output = tmp_path / "old.docx"
    output.write_bytes(b"old")
    app._download_store["old"] = {
        "path": str(output),
        "created_at": time.time() - app.DOWNLOAD_TTL_SECONDS - 1,
    }

    app._cleanup_download_store()

    assert "old" not in app._download_store
    assert not output.exists()


def test_download_registration_stores_timestamp(tmp_path):
    output = tmp_path / "new.docx"
    output.write_bytes(b"new")

    download_id = app._register_download(str(output))
    try:
        item = app._download_store[download_id]
        assert item["path"] == str(output)
        assert isinstance(item["created_at"], float)
    finally:
        app._download_store.pop(download_id, None)
        if output.exists():
            os.unlink(output)


def test_cors_origins_are_not_wildcard():
    assert "*" not in app.ALLOWED_ORIGINS
