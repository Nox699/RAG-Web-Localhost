from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import Hit, RagStore
from app.main import create_app
from app.settings import Settings


class FakeProvider:
    """Deterministisk offline provider, så web/API kan testes uden Ollama."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lower = text.lower()
            # Simple deterministic dimensions that still let cosine ranking work.
            vectors.append([
                1.0 + lower.count("ssh") + lower.count("port 22"),
                1.0 + lower.count("eksamen") + lower.count("open book"),
                1.0 + (int(sha256(text.encode()).hexdigest()[:4], 16) % 7) / 10,
            ])
        return vectors

    def chat(self, question: str, hits: list[Hit]) -> str:
        return f"Svar på: {question} [{hits[0].source}]"

    def health(self):
        return True, "Fake provider ready"


def make_app(tmp_path: Path):
    settings = Settings(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=tmp_path / "state",
        log_dir=tmp_path / "logs",
        max_upload_bytes=1024 * 1024,
    )
    for folder in (settings.data_dir, settings.state_dir, settings.log_dir):
        folder.mkdir(parents=True, exist_ok=True)
    store = RagStore(settings, provider=FakeProvider())
    return create_app(settings=settings, store=store), settings


def test_full_web_flow(tmp_path):
    app, settings = make_app(tmp_path)
    client = TestClient(app)

    assert client.get("/").status_code == 200
    initial = client.get("/api/status").json()
    assert initial["index"]["ready"] is False

    upload = client.post(
        "/api/documents",
        files=[("files", ("network.txt", b"SSH uses port 22. Firewall rules protect services.", "text/plain"))],
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["warning"] is None

    docs = client.get("/api/documents").json()["documents"]
    assert docs[0]["name"] == "network.txt"
    assert docs[0]["indexed"] is True
    assert docs[0]["chunks"] >= 1

    ask = client.post("/api/ask", json={"question": "Which port does SSH use?", "top_k": 2})
    assert ask.status_code == 200, ask.text
    body = ask.json()
    assert "network.txt#chunk1" in body["answer"]
    assert body["evidence"][0]["source"] == "network.txt#chunk1"

    qa = client.get("/api/logs/qa").text
    evidence = client.get("/api/logs/evidence").text
    assert "Which port does SSH use?" in qa
    assert "ANSWER" in qa
    assert "EVIDENCE" in evidence
    assert "network.txt#chunk1" in evidence

    deleted = client.delete("/api/documents/network.txt")
    assert deleted.status_code == 200
    assert client.get("/api/documents").json()["documents"] == []


def test_rejects_unsupported_and_duplicate_files(tmp_path):
    app, _ = make_app(tmp_path)
    client = TestClient(app)
    bad = client.post("/api/documents", files=[("files", ("malware.exe", b"x", "application/octet-stream"))])
    assert bad.status_code == 400

    first = client.post("/api/documents", files=[("files", ("a.txt", b"hello world", "text/plain"))])
    assert first.status_code == 200
    second = client.post("/api/documents", files=[("files", ("a.txt", b"again", "text/plain"))])
    assert second.status_code == 400


def test_log_clear_and_download(tmp_path):
    app, _ = make_app(tmp_path)
    client = TestClient(app)
    client.post("/api/documents", files=[("files", ("a.txt", b"SSH port 22", "text/plain"))])
    client.post("/api/ask", json={"question": "SSH?", "top_k": 1})
    assert client.get("/api/logs/qa/download").status_code == 200
    assert client.delete("/api/logs/qa").status_code == 200
    assert client.get("/api/logs/qa").text == ""
