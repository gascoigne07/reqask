"""Общие фикстуры тестов. Заглушки и помощники лежат в helpers.py."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from reqask.config import Settings
from reqask.llm import LLMClient
from reqask.loader import load_document

from helpers import DOC


@pytest.fixture
def doc(tmp_path: Path):
    path = tmp_path / "spec.md"
    path.write_text(DOC, encoding="utf-8")
    return load_document(path)


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch):
    """Чистая папка без .env: настройки только из переменных, кэш выключен, сети нет."""
    monkeypatch.chdir(tmp_path)
    for name in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_MODEL", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1/")
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setenv("LLM_MODEL", "fake")
    monkeypatch.setenv("REQASK_CACHE_DIR", "")
    (tmp_path / "spec.md").write_text(DOC, encoding="utf-8")
    return tmp_path


@pytest.fixture
def client_with():
    """handler(тело, номер запроса) -> (код, тело) или (код, тело, заголовки). Паузы не ждём, а записываем."""
    servers = []

    def make(handler, provider="gemini", **overrides):
        sent: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                sent.append(body)
                status, payload, *rest = handler(body, len(sent))
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                for name, value in (rest[0] if rest else {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        params = {"cache_dir": None, "max_retries": 5, **overrides}
        settings = Settings(provider=provider, base_url=f"http://127.0.0.1:{server.server_port}/v1/", api_key="x",
                            model="m", **params)
        client = LLMClient(settings)
        waits: list[float] = []
        client._sleep = waits.append
        return client, sent, waits

    yield make
    for server in servers:
        server.shutdown()
        server.server_close()
