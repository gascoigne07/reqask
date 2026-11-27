"""Схема report.json в docs/ совпадает с моделью RunResult.

Обновить файл: uv run python -c "import json, pathlib; from reqask.schemas import RunResult; pathlib.Path('docs/report.schema.json').write_text(json.dumps(RunResult.model_json_schema(), ensure_ascii=False, indent=2) + chr(10))"
"""

import json
from pathlib import Path

from reqask.schemas import RunResult

ROOT = Path(__file__).resolve().parents[1]


def test_published_schema_matches_model():
    published = json.loads((ROOT / "docs" / "report.schema.json").read_text(encoding="utf-8"))
    assert published == RunResult.model_json_schema()


def test_shipped_reports_fit_the_schema_model():
    for path in ("reports/report.json", "examples/answered/report.json", "examples/foreign-doc.report.json"):
        RunResult.model_validate_json((ROOT / path).read_text(encoding="utf-8"))
