import httpx

from app.core import Hit, OllamaProvider
from app.settings import Settings


def test_ollama_http_contract(tmp_path):
    settings = Settings(base_dir=tmp_path, data_dir=tmp_path/"data", state_dir=tmp_path/"state", log_dir=tmp_path/"logs")
    provider = OllamaProvider(settings)
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.method, request.url.path, request.content))
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "embeddinggemma"}, {"name": "qwen3:1.7b"}]})
        if request.url.path == "/api/embed":
            body = __import__("json").loads(request.content)
            return httpx.Response(200, json={"embeddings": [[1.0, 2.0] for _ in body["input"]]})
        if request.url.path == "/api/chat":
            return httpx.Response(200, json={"message": {"content": "Supported [a.txt#chunk1]"}})
        return httpx.Response(404)

    provider.client.close()
    provider.client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    assert provider.health() == (True, "Ollama is ready")
    assert provider.embed(["a", "b"]) == [[1.0, 2.0], [1.0, 2.0]]
    answer = provider.chat("question", [Hit("a.txt#chunk1", "evidence", 0.9)])
    assert answer == "Supported [a.txt#chunk1]"
    assert {path for _, path, _ in seen} == {"/api/tags", "/api/embed", "/api/chat"}
