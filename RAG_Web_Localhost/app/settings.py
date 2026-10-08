from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    state_dir: Path
    log_dir: Path
    ollama_host: str = "http://127.0.0.1:11434"
    embed_model: str = "embeddinggemma"
    chat_model: str = "qwen3:1.7b"
    chunk_size: int = 100
    chunk_overlap: int = 20
    max_upload_bytes: int = 20 * 1024 * 1024
    max_top_k: int = 8
    embed_batch_size: int = 32

    @property
    def db_path(self) -> Path:
        return self.state_dir / "rag.sqlite3"

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "Settings":
        root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
        return cls(
            base_dir=root,
            data_dir=Path(os.getenv("RAG_DATA_DIR", root / "data")).resolve(),
            state_dir=Path(os.getenv("RAG_STATE_DIR", root / "state")).resolve(),
            log_dir=Path(os.getenv("RAG_LOG_DIR", root / "logs")).resolve(),
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            embed_model=os.getenv("RAG_EMBED_MODEL", "embeddinggemma"),
            chat_model=os.getenv("RAG_CHAT_MODEL", "qwen3:1.7b"),
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "100")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "20")),
            max_upload_bytes=int(os.getenv("RAG_MAX_UPLOAD_MB", "20")) * 1024 * 1024,
            max_top_k=int(os.getenv("RAG_MAX_TOP_K", "8")),
            embed_batch_size=int(os.getenv("RAG_EMBED_BATCH", "32")),
        )
