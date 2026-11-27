"""Отчёты в репозитории совпадают с тем, что код рисует из их report.json (без модели, сети и ключа)."""

import hashlib
import json
from pathlib import Path

import pytest

from reqask import cli

ROOT = Path(__file__).resolve().parent.parent


def _render(json_path: Path, out_dir: Path, md_name: str, *extra: str) -> Path:
    """Имя отчёта то же, что в репозитории: в тексте отчёта есть ссылка на файл вопросов по его имени."""
    target = out_dir / md_name
    assert cli.main(["--render", str(json_path), "--output", str(target), *extra]) == cli.EXIT_OK
    return out_dir


def test_reports_dir_matches_render(tmp_path):
    src = ROOT / "reports"
    out = _render(src / "report.json", tmp_path, "report.md")
    for name in ("report.md", "report.html", "report.questions.md"):
        assert (out / name).read_bytes() == (src / name).read_bytes(), name


# Для примеров в examples/ лежат только .md и вопросы, html там нет: сверяем эти два файла.
EXAMPLES = sorted((ROOT / "examples").glob("*.report.json"))


def test_examples_are_found():
    assert EXAMPLES


@pytest.mark.parametrize("json_path", EXAMPLES, ids=lambda p: p.name)
def test_example_reports_match_render(json_path, tmp_path):
    base = json_path.name[: -len(".json")]
    # --no-html: в журнале шага 9 примеров перечислены md, вопросы и json, без html.
    out = _render(json_path, tmp_path, f"{base}.md", "--no-html")
    for name in (f"{base}.md", f"{base}.questions.md"):
        assert (out / name).read_bytes() == (json_path.parent / name).read_bytes(), name


def test_docs_requirements_is_the_checked_document():
    docs = (ROOT / "docs" / "requirements.md").read_bytes()
    assert docs == (ROOT / "input" / "requirements.md").read_bytes()
    recorded = json.loads((ROOT / "reports" / "report.json").read_text(encoding="utf-8"))["document_sha256"]
    assert hashlib.sha256(docs).hexdigest() == recorded


def test_reports_csv_matches_export(tmp_path):
    src = ROOT / "reports"
    target = tmp_path / "report.tickets.csv"
    assert cli.main(["--export-csv", str(src / "report.json"), "--output", str(target)]) == cli.EXIT_OK
    assert target.read_bytes() == (src / "report.tickets.csv").read_bytes()
