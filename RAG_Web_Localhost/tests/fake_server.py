"""Only used for localhost smoke testing; not the production entrypoint."""
from pathlib import Path
import tempfile

from app.core import Hit, RagStore
from app.main import create_app
from app.settings import Settings


class FakeProvider:
    def embed(self, texts):
        return [[1.0, float(len(t) % 11 + 1), 0.5] for t in texts]
    def chat(self, question, hits):
        return f"Localhost test answer [{hits[0].source}]"
    def health(self):
        return True, "Fake provider ready"


ROOT = Path(tempfile.mkdtemp(prefix="rag-localhost-smoke-"))
settings = Settings(base_dir=ROOT, data_dir=ROOT/"data", state_dir=ROOT/"state", log_dir=ROOT/"logs")
store = RagStore(settings, FakeProvider())
app = create_app(settings, store)
