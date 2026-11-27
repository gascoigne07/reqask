"""Выгрузка замечаний в CSV: --export-csv report.json --output tickets.csv, без модели и ключа."""

import csv
from pathlib import Path

import pytest

from reqask import cli, export
from reqask.report import _active
from reqask.schemas import RunResult

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "report.json"


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


@pytest.fixture
def no_keys(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_export_of_committed_report(tmp_path, no_keys):
    out = tmp_path / "tickets.csv"
    assert cli.main(["--export-csv", str(REPORT), "--output", str(out)]) == cli.EXIT_OK
    result = RunResult.model_validate_json(REPORT.read_text(encoding="utf-8"))
    active = [f for f in result.findings if _active(f)]
    assert len(active) == 67
    headers, data = _read(out)
    assert headers == list(export.COLUMNS)
    assert len(data) == len(active)
    assert [r["Severity"] for r in data[:5]] == ["CRITICAL"] * 5
    order = [r["Severity"] for r in data]
    assert order == sorted(order, key=["CRITICAL", "MAJOR", "MINOR"].index)
    assert {r["Priority"] for r in data} <= {"Highest", "High", "Low"}
    assert all(r["Summary"].strip() and r["Description"].strip() for r in data)
    assert all(r["Issue Type"] == "Task" for r in data)
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    first = data[0]
    assert first["Summary"].startswith(first["Finding ID"] + ": ")
    assert first["Labels"].split()[:2] == ["reqask", "critical"]
    assert "строка " in first["Description"]


def test_lines_sorted_unique_and_inactive_skipped(tmp_path):
    result = RunResult.model_validate_json(REPORT.read_text(encoding="utf-8"))
    ids = {r["Finding ID"] for r in export.rows(result)}
    assert all(f.id in ids for f in result.findings if _active(f))
    assert not any(f.id in ids for f in result.findings if not _active(f))
    for r in export.rows(result):
        nums = [int(n) for n in r["Lines"].split(", ") if n]
        assert nums == sorted(set(nums))


def test_formula_protection():
    assert export.protect("=SUM(A1)") == "'=SUM(A1)"
    for start in ("+1", "-1", "@x", "\tx", "\rx"):
        assert export.protect(start).startswith("'")
    assert export.protect("обычный текст") == "обычный текст"


def test_formula_in_finding_is_protected_in_file(tmp_path):
    result = RunResult.model_validate_json(REPORT.read_text(encoding="utf-8"))
    for f in result.findings:
        if _active(f):
            f.title = "=HYPERLINK(\"http://x\")"
            f.id = "-D"
            break
    out = tmp_path / "t.csv"
    export.write_csv(result, out)
    _, data = _read(out)
    assert any(r["Finding ID"] == "'-D" for r in data)
    assert all(not r["Summary"].startswith("=") for r in data)


def test_bad_inputs_give_exit_2(tmp_path, no_keys, capsys):
    ok = str(tmp_path / "t.csv")
    bad = tmp_path / "bad.json"
    bad.write_text("{не json", encoding="utf-8")
    other = tmp_path / "other.json"
    other.write_text('{"a": 1}', encoding="utf-8")
    cases = [
        ["--export-csv", str(REPORT)],                                      # нет --output
        ["--export-csv", str(REPORT), "-o", str(tmp_path / "t.md")],        # не .csv
        ["--export-csv", str(REPORT), "-o", str(tmp_path)],                 # папка
        ["--export-csv", str(bad), "-o", ok],
        ["--export-csv", str(other), "-o", ok],
        ["--export-csv", str(tmp_path / "нет.json"), "-o", ok],
        ["--export-csv", str(REPORT), "-o", ok, "-i", "x.md"],
        ["--export-csv", str(REPORT), "-o", ok, "--check"],
        ["--export-csv", str(REPORT), "-o", ok, "--dry-run"],
        ["--export-csv", str(REPORT), "-o", ok, "--render", str(REPORT)],
        ["--export-csv", str(REPORT), "-o", ok, "--compare", str(REPORT), str(REPORT)],
    ]
    for argv in cases:
        assert cli.main(argv) == cli.EXIT_INPUT, argv
    assert not Path(ok).exists()
    capsys.readouterr()


def test_write_error_gives_exit_2(tmp_path, no_keys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert cli.main(["--export-csv", str(REPORT), "-o", str(blocker / "t.csv")]) == cli.EXIT_INPUT


def test_existing_modes_still_require_md(tmp_path, no_keys):
    assert cli.main(["--render", str(REPORT), "-o", str(tmp_path / "t.csv")]) == cli.EXIT_INPUT
    assert cli.main(["-i", "x.md", "-o", str(tmp_path / "t.csv")]) == cli.EXIT_INPUT
