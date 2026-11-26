"""Правки по ревью кода 27.11 (audit3.md, раздел «Ревью кода», пункты 1-14)."""

from pathlib import Path

import pytest

from reqask import cli
from reqask.schemas import BatchReviewOut, SegmentationOut

from test_cli import FatalAt, run, use, workdir  # noqa: F401  фикстура workdir нужна тестам ниже
from test_core import FakeLLM, doc  # noqa: F401


# ---------- 1. фатальная ошибка до первого ответа не трогает прежний отчёт ----------


OLD_FILES = {
    "report.md": "# Вчерашний отчёт\n",
    "report.questions.md": "# Вчерашние вопросы\n",
    "report.json": '{"old": true}\n',
}


@pytest.mark.parametrize("kind", ["quota", "rate", "auth", "model"])
def test_fatal_before_first_answer_keeps_old_report(workdir, monkeypatch, capsys, kind):
    out = workdir / "out"
    out.mkdir()
    for name, text in OLD_FILES.items():
        (out / name).write_bytes(text.encode("utf-8"))
    use(monkeypatch, FatalAt(SegmentationOut, kind))
    assert run() == cli.EXIT_NO_MODEL
    for name, text in OLD_FILES.items():
        assert (out / name).read_bytes() == text.encode("utf-8")
    err = capsys.readouterr().err
    assert "отчёт не записан" in err and "суточная квота исчерпана" in err


def test_fatal_after_segmentation_still_gives_partial_report(workdir, monkeypatch):
    """Нарезка прошла, дальше квота: отчёт неполный, код 3, как раньше."""
    use(monkeypatch, FatalAt(BatchReviewOut, "quota"))
    assert run() == cli.EXIT_PARTIAL
    assert "Отчёт неполный" in (workdir / "out" / "report.md").read_text(encoding="utf-8")
