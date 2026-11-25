"""Тесты без сети: модель подменена заглушкой."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from reqask.config import Settings
from reqask.grounding import TextIndex, normalize
from reqask.lint import lint
from reqask.llm import LLMClient, LLMError, LLMFatal, LLMTruncated, extract_json
from reqask.loader import LoadError, load_document
from reqask.pipeline import Pipeline, make_id
from reqask.report import render
from reqask.schemas import (
    BatchReviewOut,
    LLMStats,
    SegmentationOut,
    SetReviewOut,
    VerdictOut,
)

DOC = """# Библиотечный каталог

## Требования
* **FR-1.** Система должна быстро показывать результаты поиска книги.
* **FR-2.** Читатель может взять на руки не больше 5 книг.

## Данные

| Поле | Тип |
| :--- | :--- |
| `max_books` | Не больше 3 книг на читателя, integer |

## Тестирование
заполняется позже
"""

SETTINGS = Settings(provider="fake", base_url=None, api_key="x", model="fake-model", cache_dir=None, max_retries=0)


@pytest.fixture
def doc(tmp_path: Path):
    path = tmp_path / "spec.md"
    path.write_text(DOC, encoding="utf-8")
    return load_document(path)


def _defect(criterion, severity, evidence, question=None, addressee=None, line=None):
    return {"criterion": criterion, "severity": severity, "evidence": evidence, "line": line,
            "problem": "п", "impact": "и", "recommendation": "р", "question": question, "addressee": addressee}


def _set_finding(kind, criterion, severity, title, evidence, req_ids=(), question=None, section=None, addressee=None):
    return {"kind": kind, "criterion": criterion, "severity": severity, "title": title, "req_ids": list(req_ids),
            "section": section, "evidence": [{"quote": q, "line": None} for q in evidence], "problem": "п",
            "impact": "и", "recommendation": "р", "question": question, "addressee": addressee}


class FakeLLM:
    """Отдаёт заранее заданные ответы по типу схемы, как это делала бы модель."""

    def __init__(self):
        self.stats = LLMStats()
        self.steps: list[str] = []
        self.users: list[str] = []

    def complete_json(self, step, system, user, schema, kind=""):
        self.steps.append(step)
        self.users.append(user)
        self.stats.calls += 1
        if schema is SegmentationOut:
            return SegmentationOut.model_validate({"requirements": [
                {"line_start": 4, "line_end": 4, "source_id": "FR-1.", "section": "Требования",
                 "kind": "nonfunctional", "summary": "Быстрый поиск"},
                {"line_start": 5, "line_end": 5, "source_id": "FR-2", "section": "Требования",
                 "kind": "data", "summary": "Число книг на руках"},
                {"line_start": 9, "line_end": 11, "source_id": None, "section": "Данные",
                 "kind": "странный", "summary": "Поле max_books"},
            ], "skipped": [{"line_start": 13, "line_end": 14, "reason": "Template"}]})
        if schema is BatchReviewOut:
            return BatchReviewOut.model_validate({"reviews": [
                {"req_id": "REQ-001", "checks": [
                    {"criterion": "verifiable", "status": "fail", "note": "нет числа"},
                    {"criterion": "COMPLETE", "status": "fail", "note": "дефект не описан"},
                    {"criterion": "NECESSARY", "status": "NA", "note": "не применим"},
                    {"criterion": "STYLE", "status": "fail", "note": "нет такого критерия"},
                ], "defects": [
                    _defect("verifiable", "critical", "«быстро показывать»", "Какое время ответа, в секундах?", "Business"),
                    _defect("STYLE", "MAJOR", "быстро показывать результаты", "лишний вопрос", "qa"),
                ], "rewritten": "Система отвечает за <N секунд>."},
                {"req_id": "REQ-2", "checks": [], "defects": [
                    _defect("UNAMBIGUOUS", "MINOR", "такого текста в документе нет совсем"),
                ], "rewritten": None},
                {"req_id": "REQ-03", "checks": [], "defects": [], "rewritten": None},
            ]})
        if schema is SetReviewOut:
            if "согласованность" in step:
                return SetReviewOut.model_validate({
                    "analyses": [{"criterion": "SET_CONSISTENT", "status": "fail", "analysis": "Сравнил число книг."},
                                 {"criterion": "SET_COMPLETE", "status": "ok", "analysis": "чужой критерий"}],
                    "findings": [_set_finding(
                        "contradiction", "SET_CONSISTENT", "CRITICAL", "Разное число книг",
                        ["Читатель может взять на руки не больше 5 книг", "Не больше 3 книг на читателя, integer",
                         "выдуманная цитата абсолютно"],
                        req_ids=["REQ-002", "REQ-3", "REQ-999"], question="Сколько книг можно взять: 3 или 5?",
                        addressee="business",
                    )]})
            return SetReviewOut.model_validate({
                "analyses": [{"criterion": "SET_COMPLETE", "status": "partial", "analysis": "Раздел тестов пуст."}],
                "findings": [
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Пустой раздел", ["заполняется позже"],
                                 question="Кто и когда заполнит раздел тестирования?"),
                    _set_finding("other", "SET_RANKED", "MINOR", "Без опоры", ["нет такой цитаты нигде вообще"]),
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Нет требований к доступу", [],
                                 question="Кто может менять лимит книг?", section="Требования", addressee="security"),
                    _set_finding("gap", "SET_COMPLETE", "MAJOR", "Пробел без места", [], question="Вопрос?"),
                ]})
        if schema is VerdictOut:
            return VerdictOut.model_validate({"rationale": "Есть блокеры.", "top_fixes": [
                {"finding_ids": ["S-01", "X-404"], "action": "Оставить одно число."},
                {"finding_ids": ["нет"], "action": "Мимо."},
            ]})
        raise AssertionError(schema)


def test_loader_sections_and_content(doc):
    assert doc.n == 14
    assert doc.section_path(4) == "Требования"
    assert doc.is_heading(3) and not doc.is_content(3)
    assert not doc.is_content(10)  # разделитель таблицы
    assert doc.numbered(4, 4).startswith("L0004| ")


def test_loader_errors(tmp_path):
    with pytest.raises(LoadError):
        load_document(tmp_path / "missing.md")
    empty = tmp_path / "empty.md"
    empty.write_text("   \n")
    with pytest.raises(LoadError):
        load_document(empty)


def test_grounding(doc):
    index = TextIndex(doc)
    assert normalize("**FR-1.**  «Ёж»") == 'fr-1. "еж"'
    assert index.find("Читатель может взять на руки не больше 5 книг") == 5
    assert index.find("max_books | Не больше 3 книг") == 11  # разметка таблицы не мешает
    assert index.find("Система должна ... результаты поиска книги") == 4  # многоточие внутри
    assert index.find("Читатель может взять на руки не больше 5 книг", 9, 11) is None  # вне диапазона
    assert index.find("этого нет") is None
    assert index.fuzzy("Система обязана быстро показывать результаты поиска книги", 4, 4) == 4
    assert index.fuzzy("совершенно посторонний текст про погоду", 4, 4) is None


def test_lint():
    hints = lint("Система должна быстро и удобно работать и т.д.")
    assert len(hints) == 3
    assert lint("Порог от 1 000 до 1 000 000 включительно.") == []


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Вот ответ: {"a": {"b": 2}} конец') == '{"a": {"b": 2}}'
    with pytest.raises(ValueError):
        extract_json("нет json")


def test_pipeline_end_to_end(doc):
    llm = FakeLLM()
    result = Pipeline(llm, SETTINGS).run(doc, "test")

    reqs = result.requirements
    assert [r.id for r in reqs] == ["REQ-01", "REQ-02", "REQ-03"]  # две цифры при числе до 99
    assert reqs[0].source_id == "FR-1" and reqs[2].source_id is None
    assert reqs[0].quote == doc.line(4).text  # цитата вырезана из документа дословно
    assert (reqs[2].line_start, reqs[2].line_end) == (9, 11)  # таблица целиком, вместе с шапкой
    assert reqs[2].kind == "other"
    assert reqs[0].lint_hints and reqs[0].lint_confirmed == reqs[0].lint_hints  # «быстро» есть в цитате дефекта

    by_id = {f.id: f for f in result.findings}
    d1 = by_id["D-01"]
    assert d1.severity == "CRITICAL" and d1.criterion == "VERIFIABLE"
    assert d1.evidence[0].status == "exact" and d1.evidence[0].line == 4
    assert d1.question == "Какое время ответа, в секундах?" and d1.addressee == "business" and d1.impact == "и"
    assert by_id["D-02"].req_ids == ["REQ-02"]  # дефект с неверным критерием отброшен, порция цела
    assert by_id["D-02"].evidence[0].status == "anchor"  # выдуманная цитата заменена текстом требования
    assert by_id["D-02"].question is None and by_id["D-02"].addressee is None
    assert result.quality.dropped_defects == 1 and result.quality.dropped_checks == 1

    checks = {c.criterion: c for c in result.checks["REQ-01"]}
    assert len(checks) == 9 and checks["VERIFIABLE"].status == "fail"
    assert checks["COMPLETE"].status == "unknown"  # fail без дефекта
    assert checks["NECESSARY"].status == "na" and checks["SINGULAR"].status == "pass"
    assert {c.status for c in result.checks["REQ-03"]} == {"pass"}

    s1 = by_id["S-01"]
    assert s1.kind == "contradiction" and s1.req_ids == ["REQ-02", "REQ-03"]
    assert [e.line for e in s1.evidence] == [5, 11]
    assert s1.question and s1.addressee == "business"
    gap = next(f for f in result.findings if f.title == "Нет требований к доступу")
    assert gap.kind == "gap" and not gap.evidence and gap.section == "Требования" and gap.addressee == "security"
    titles = {f.title for f in result.findings}
    assert "Без опоры" not in titles and "Пробел без места" not in titles  # без опоры на текст отброшены
    assert result.grounding.dropped_findings == 2 and result.grounding.dropped_quotes == 2
    assert [a.criterion for a in result.set_analyses] == ["SET_CONSISTENT", "SET_COMPLETE"]
    assert result.set_analyses[1].status == "partial"  # чужой критерий из первого прохода не принят

    # Второй проход по набору видит замечания первого и просит их не повторять.
    assert "Разное число книг" in llm.users[3]

    assert result.verdict.ready_for_development == "Нет"
    assert result.verdict.ready_for_testing == "Нет"
    assert [fix.finding_ids for fix in result.verdict.top_fixes] == [["S-01"]]
    assert [(s.line_start, s.line_end, s.reason) for s in result.skipped_lines] == [(13, 14, "template")]
    assert result.uncovered_lines == []
    assert result.quality.ids_in_document == 2 and result.quality.ids_missing == []
    assert result.rewritten == {"REQ-01": "Система отвечает за <N секунд>."}

    report = render(result)
    for heading in ("## 1. Паспорт прогона", "## 2. Как агент нарезал требования", "## 3. Проверка каждого требования",
                    "## 4. Проверка набора требований", "## 5. Сводка", "## 6. Итог"):
        assert heading in report
    assert "fake-model" in report and "FR-1" in report and "D-01" in report and "S-01" in report
    assert "Вопрос заказчику (бизнес): Какое время ответа" in report
    assert "—" not in report and "–" not in report


def test_ids_lost_in_segmentation_are_reported(doc):
    class Lossy(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            out = super().complete_json(step, system, user, schema, kind)
            if schema is SegmentationOut:
                out.requirements[1].source_id = None
            return out

    result = Pipeline(Lossy(), SETTINGS).run(doc, "test")
    assert result.quality.ids_missing == ["FR-2"]
    assert "Не найдены в нарезке: FR-2" in render(result)


def test_ids_use_three_digits_over_99():
    assert make_id("REQ", 7, 99) == "REQ-07" and make_id("REQ", 7, 100) == "REQ-007"


def test_pipeline_survives_failed_steps(doc):
    class Flaky(FakeLLM):
        def complete_json(self, step, system, user, schema, kind=""):
            if schema in (BatchReviewOut, VerdictOut) or "полнота" in step:
                self.steps.append(step)
                raise LLMError("сбой")
            return super().complete_json(step, system, user, schema, kind)

    result = Pipeline(Flaky(), SETTINGS).run(doc, "test")
    assert result.unreviewed == ["REQ-01", "REQ-02", "REQ-03"]
    assert len(result.failed_steps) == 5  # три требования, проход по набору, итог
    assert [f.id for f in result.findings] == ["S-01"]
    assert result.verdict.generated_by_model is False and result.verdict.top_fixes
    assert "Неполнота прогона" in render(result)


def test_llm_repairs_invalid_json(monkeypatch):
    client = LLMClient(SETTINGS)
    answers = iter(["это не json", '{"rationale": "ок", "top_fixes": [{"finding_ids": ["D-001"]}]}',
                    '{"rationale": "ок", "top_fixes": []}'])
    seen = []

    def fake_chat(step, messages, schema, kind=""):
        seen.append(len(messages))
        return next(answers)

    monkeypatch.setattr(client, "_chat", fake_chat)
    out = client.complete_json("итог", "system", "user", VerdictOut)
    assert out.rationale == "ок" and client.stats.repairs == 2
    assert seen == [2, 4, 4]  # в повторе модель видит свой ответ и текст ошибки


def test_llm_gives_up_after_repairs(monkeypatch):
    client = LLMClient(SETTINGS)
    monkeypatch.setattr(client, "_chat", lambda *a: "мусор")
    with pytest.raises(LLMError):
        client.complete_json("итог", "system", "user", VerdictOut)


# ---------- клиент против локального сервера: что уходит провайдеру и как разбирается ответ ----------


@pytest.fixture
def client_with():
    """Настоящий LLMClient против локального HTTP-сервера. handler(тело запроса, номер) -> (код, тело ответа)."""
    servers = []

    def make(handler, **overrides):
        sent: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                sent.append(body)
                status, payload = handler(body, len(sent))
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        params = {"cache_dir": None, "max_retries": 0, **overrides}
        settings = Settings(provider="gemini", base_url=f"http://127.0.0.1:{server.server_port}/v1/", api_key="x",
                            model="m", **params)
        logs: list[str] = []
        return LLMClient(settings, logs.append), sent, logs

    yield make
    for server in servers:
        server.shutdown()
        server.server_close()


def _completion(content: str, finish: str = "stop") -> dict:
    return {
        "id": "1", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 40,
                  "completion_tokens_details": {"reasoning_tokens": 25}},
    }


VERDICT_JSON = '{"rationale": "ок", "top_fixes": []}'


def test_llm_request_params(client_with):
    client, sent, logs = client_with(lambda body, n: (200, _completion(VERDICT_JSON)), temperature=0.3)
    out = client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    client.complete_json("нарезка 1/1", "system", "user", VerdictOut, kind="segment")

    assert out.rationale == "ок"
    first, second = sent
    assert "temperature" not in first and "top_p" not in first and "seed" not in first
    assert any("LLM_TEMPERATURE" in line for line in logs)  # одно предупреждение, параметр не ушёл
    assert (first["reasoning_effort"], first["max_tokens"]) == ("medium", 16_000)
    assert (second["reasoning_effort"], second["max_tokens"]) == ("low", 16_000)
    assert first["response_format"]["type"] == "json_schema"  # режим parse: схему строит SDK
    assert first["response_format"]["json_schema"]["name"] == "VerdictOut"
    assert "JSON Schema" not in first["messages"][0]["content"]  # схема ушла один раз, в response_format (П-04)
    stats = client.stats
    assert (stats.calls, stats.prompt_tokens, stats.completion_tokens) == (2, 20, 10)
    assert (stats.total_tokens, stats.reasoning_tokens) == (80, 50)


def test_llm_json_mode_ladder(client_with):
    def handler(body, n):
        if "response_format" in body:
            return 400, {"error": {"message": "response_format is not supported", "code": 400}}
        return 200, _completion("Ответ:\n```json\n" + VERDICT_JSON + "\n```")

    client, sent, _ = client_with(handler)
    client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    formats = [(body.get("response_format") or {}).get("type") for body in sent]
    assert formats == ["json_schema", "json_schema", "json_object", None]  # parse, schema, object, none
    assert "strict" in sent[0]["response_format"]["json_schema"] and "strict" not in sent[1]["response_format"]["json_schema"]
    has_schema_text = ["JSON Schema" in body["messages"][0]["content"] for body in sent]
    assert has_schema_text == [False, False, True, True]  # текстом схема идёт только в object и none


def test_llm_drops_rejected_params_and_stops_on_bad_key(client_with):
    def handler(body, n):
        if "reasoning_effort" in body:
            return 400, [{"error": {"code": 400, "message": "Unknown parameter: reasoning_effort"}}]
        if "max_tokens" in body:
            return 400, {"error": {"message": "max_tokens is not supported, use max_completion_tokens"}}
        return 200, _completion(VERDICT_JSON)

    client, sent, _ = client_with(handler)
    client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    assert len(sent) == 3 and "reasoning_effort" not in sent[2] and "max_tokens" not in sent[2]
    assert sent[2]["response_format"]["type"] == "json_schema"  # режим JSON при этом не понижен

    # Gemini отдаёт тело ошибки списком, причина есть только в нём.
    client, sent, _ = client_with(lambda body, n: (400, [{"error": {"code": 400, "message": "Please pass a valid API key"}}]))
    with pytest.raises(LLMFatal):
        client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    assert len(sent) == 1  # без повторов и без понижения режимов


def test_llm_truncated_and_unparsed_answers(client_with):
    client, _, _ = client_with(lambda body, n: (200, _completion('{"rationale": "об', finish="length")))
    with pytest.raises(LLMTruncated):
        client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    assert client.stats.calls == 1

    # Ответ не по схеме: SDK его не разбирает, клиент отдаёт текст модели на исправление.
    answers = iter(['{"rationale": 5, "top_fixes": "нет"}', VERDICT_JSON])
    client, sent, _ = client_with(lambda body, n: (200, _completion(next(answers))))
    out = client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    assert out.rationale == "ок" and client.stats.repairs == 1 and len(sent[1]["messages"]) == 4


def test_llm_daily_quota_is_fatal_without_retries(client_with):
    body = [{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "message": "Quota exceeded: Generate content requests per day limit exceeded on Free Tier."}}]
    client, sent, _ = client_with(lambda request, n: (429, body), max_retries=3)
    with pytest.raises(LLMFatal):
        client.complete_json("итог", "system", "user", VerdictOut, kind="verdict")
    assert len(sent) == 1  # повторы суточную квоту не вернут, а запросы тратят
