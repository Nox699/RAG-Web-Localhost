from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from .core import DocumentError, IndexNotReady, RagError, RagStore
from .settings import Settings


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=8)


def create_app(settings: Settings | None = None, store: RagStore | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or RagStore(settings)
    app = FastAPI(title="Local RAG Web", version="1.0.0", docs_url="/api/docs", redoc_url=None)
    app.state.settings = settings
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(static_dir / "index.html")

    @app.get("/api/status")
    def status():
        index = store.index_status()
        ollama_ok, ollama_message = store.provider.health()
        return {"index": index, "ollama": {"ok": ollama_ok, "message": ollama_message}}

    @app.get("/api/documents")
    def documents():
        return {"documents": store.list_documents()}

    @app.post("/api/documents")
    async def upload_documents(files: list[UploadFile] = File(...)):
        if not files:
            raise HTTPException(400, "No files supplied")
        try:
            items = []
            for upload in files:
                content = await upload.read(settings.max_upload_bytes + 1)
                items.append((upload.filename or "", content))
            saved = store.save_uploads(items)
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        rebuild_warning = None
        try:
            store.rebuild_index()
        except Exception as exc:
            rebuild_warning = str(exc)
        return {"saved": saved, "index": store.index_status(), "warning": rebuild_warning}

    @app.delete("/api/documents/{filename}")
    def delete_document(filename: str):
        try:
            store.delete_document(filename)
            return {"deleted": filename, "index": store.index_status()}
        except DocumentError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/index/rebuild")
    def rebuild_index():
        try:
            return {"index": store.rebuild_index()}
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, f"Index rebuild failed: {exc}") from exc

    @app.post("/api/ask")
    def ask(payload: AskRequest):
        try:
            result = store.ask(payload.question, payload.top_k)
            return {
                "question": result.question,
                "answer": result.answer,
                "evidence": [
                    {"source": h.source, "text": h.text, "similarity": h.score} for h in result.hits
                ],
            }
        except IndexNotReady as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, RagError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, f"Model request failed: {exc}") from exc

    @app.get("/api/logs/{kind}")
    def read_log(kind: str):
        if kind not in {"qa", "evidence"}:
            raise HTTPException(404, "Unknown log")
        return PlainTextResponse(store.logger.read(kind), media_type="text/plain; charset=utf-8")

    @app.delete("/api/logs/{kind}")
    def clear_log(kind: str):
        if kind not in {"qa", "evidence"}:
            raise HTTPException(404, "Unknown log")
        store.logger.clear(kind)
        return {"cleared": kind}

    @app.get("/api/logs/{kind}/download")
    def download_log(kind: str):
        if kind not in {"qa", "evidence"}:
            raise HTTPException(404, "Unknown log")
        filename = "qa_history.txt" if kind == "qa" else "evidence_history.txt"
        path = settings.log_dir / filename
        if not path.exists():
            path.write_text("", encoding="utf-8")
        return FileResponse(path, filename=filename, media_type="text/plain")

    return app


app = create_app()
