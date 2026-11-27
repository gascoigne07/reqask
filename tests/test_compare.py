"""Сравнение двух report.json без модели (--compare): сопоставление по цитатам и требованиям, не по номерам."""

from reqask import cli
from reqask.compare import SAME_DOC, compare, render_compare
from reqask.schemas import Evidence

from helpers import _f, _req, _result


def _reqs(shift: int = 0):
    reqs = [_req(1, 10 + shift, "Порог от 1 000 до 1 000 000."), _req(2, 20 + shift, "Месяц по дате покупки."),
            _req(3, 30 + shift, "Push один раз в месяц."), _req(4, 40 + shift, "Ответ 200.")]
    reqs[0].source_id, reqs[1].source_id = "ФТ-1", "ФТ-2"
    return reqs


def _q(f, text, line):
    f.evidence = [Evidence(quote=text, line=line)]
    return f


def _old():
    return _result([
        _q(_f("S-01", "set", [], ["REQ-02", "REQ-03"], severity="CRITICAL", status="confirmed",
              title="Месяц покупки задан по двум разным датам"), "Месяц определяется по дате совершения покупки", 20),
        _q(_f("S-02", "set", [], ["REQ-04"], severity="CRITICAL", status="confirmed",
              title="Сохранение настройки методом GET"), "REST type GET", 40),
        _q(_f("D-01", "requirement", [], ["REQ-01"], problem="Не сказано, что делать при пороге ниже 1 000."),
           "Порог от 1 000 до 1 000 000", 10),
        _q(_f("D-02", "requirement", [], ["REQ-04"], severity="MINOR", problem="Нет примера ответа с ошибкой."),
           "Ответ 200", 40),
    ], requirements=_reqs())


def _new(sha: str = "0" * 64):
    # Документ поправлен: строки сдвинулись на 3, номера замечаний другие.
    result = _result([
        _q(_f("S-07", "set", [], ["REQ-02", "REQ-03"], severity="CRITICAL", status="confirmed",
              title="Месяц покупки задан по двум датам"), "Месяц определяется по дате совершения покупки в Алматы", 23),
        _q(_f("S-01", "set", [], ["REQ-04"], severity="MAJOR", status="confirmed",
              title="Сохранение настройки методом GET"), "REST type GET", 43),
        _q(_f("D-05", "requirement", [], ["REQ-01"], problem="Не сказано, что делать, если порог ниже 1 000."),
           "Задаёт порог от 1 000 до 1 000 000 включительно", 13),
        _q(_f("S-03", "set", [], ["REQ-03"], severity="CRITICAL", status="confirmed",
              title="Повторный push после смены порога"), "Push один раз в месяц", 33),
    ], requirements=_reqs(3))
    result.document_sha256 = sha
    return result


def test_matching_ignores_numbers_and_lines():
    c = compare(_old(), _new())
    pairs = {(p.old.id, p.new.id) for p in c.pairs}
    assert ("S-01", "S-07") in pairs and ("S-02", "S-01") in pairs and ("D-01", "D-05") in pairs
    assert [f.id for f, _, _ in c.gone] == ["D-02"]
    assert [f.id for f, _ in c.added] == ["S-03"]


def test_blocker_lists_and_honest_words():
    c = compare(_old(), _new())
    text = render_compare(c, "old.json", "new.json")
    kept = text[text.index("### Осталось"): text.index("### Нет среди блокеров")]
    assert "S-01 -> S-07 [CRITICAL]" in kept
    gone = text[text.index("### Нет среди блокеров"): text.index("### Новые блокеры")]
    assert "S-02 [CRITICAL]" in gone and "в новом отчёте S-01 [MAJOR], не блокер" in gone
    new = text[text.index("### Новые блокеры"): text.index("## Остальные")]
    assert "S-03 [CRITICAL]" in new
    rest = text[text.index("## Остальные"):]
    assert "D-01 -> D-05 [MAJOR]" in rest and "D-02 [MINOR]" in rest
    assert "Как сопоставлены замечания" in text and "исправлен" not in text.lower()
    assert "| CRITICAL | 2 | 2 |" in text and "| Блокеров | 2 | 2 |" in text


def test_same_document_line():
    assert SAME_DOC in render_compare(compare(_old(), _new()))
    assert SAME_DOC not in render_compare(compare(_old(), _new("1" * 64)))


def test_cli_compare_without_key(tmp_path, monkeypatch, capsys):
    for name in ("LLM_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "old.json").write_text(_old().model_dump_json(), encoding="utf-8")
    (tmp_path / "new.json").write_text(_new().model_dump_json(), encoding="utf-8")
    assert cli.main(["--compare", "old.json", "new.json", "--output", "out/diff.md"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "Блокеры: было 2, стало 2; осталось 1, нет среди блокеров нового отчёта 1, новых 1." in out
    assert (tmp_path / "out" / "diff.md").read_text(encoding="utf-8").startswith("# Сравнение двух прогонов")
    # Без --output сравнение печатается целиком.
    assert cli.main(["--compare", "old.json", "new.json"]) == cli.EXIT_OK
    assert "## Блокеры" in capsys.readouterr().out
    (tmp_path / "bad.json").write_text("{}", encoding="utf-8")
    assert cli.main(["--compare", "old.json", "bad.json"]) == cli.EXIT_INPUT
    assert cli.main(["--compare", "old.json", "missing.json"]) == cli.EXIT_INPUT
    assert cli.main(["--compare", "old.json", "new.json", "--output", "new.json"]) == cli.EXIT_INPUT
    assert cli.main(["--compare", "old.json", "new.json", "--output", "diff.txt"]) == cli.EXIT_INPUT
    assert cli.main(["--compare", "old.json", "new.json", "-i", "spec.md"]) == cli.EXIT_INPUT
