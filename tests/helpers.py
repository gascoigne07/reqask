"""Общие заглушки и помощники тестов: документ, настройки, FakeLLM, запуск CLI, ответы сервера, заготовки отчёта."""

import re

from pydantic import BaseModel

from reqask import cli
from reqask.config import Settings
from reqask.llm import LLMFatal
from reqask.schemas import (
    BatchReviewOut,
    CriticOut,
    EdgeReviewOut,
    Evidence,
    Finding,
    FinalOut,
    GroundingStats,
    LLMStats,
    Requirement,
    RunResult,
    SegmentationOut,
    SetReviewOut,
    Verdict,
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


def _defect(criterion, severity, evidence, question=None, addressee=None, line=None):
    return {"criterion": criterion, "severity": severity, "evidence": evidence, "line": line,
            "problem": "п", "impact": "и", "recommendation": "р", "question": question, "addressee": addressee}


def _set_finding(kind, criterion, severity, title, evidence, req_ids=(), question=None, section=None, addressee=None,
                 divergence="none"):
    return {"kind": kind, "criterion": criterion, "severity": severity, "title": title, "req_ids": list(req_ids),
            "section": section, "evidence": [{"quote": q, "line": None} for q in evidence], "problem": "п",
            "impact": "и", "recommendation": "р", "question": question, "addressee": addressee,
            "divergence": divergence}


def _question(ids, n_options, recommended=None, addressee=None):
    return {"text": f"Вопрос про {ids[0]}?", "addressee": addressee,
            "options": [{"answer": f"вариант {i}", "consequence": "правка"} for i in range(1, n_options + 1)],
            "recommended": recommended, "why_recommended": "так проще" if recommended else None,
            "blocks": "нельзя реализовать", "doc_says": None, "finding_ids": list(ids)}


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
                    {"criterion": "SINGULAR", "status": "Pass", "note": ""},
                ], "defects": [
                    _defect("verifiable", "critical", "«быстро показывать»", "Какое время ответа, в секундах?", "Business"),
                    _defect("STYLE", "MAJOR", "быстро показывать результаты", "лишний вопрос", "qa"),
                ], "rewritten": "Система отвечает за <N секунд>."},
                {"req_id": "REQ-2", "checks": [
                    {"criterion": "UNAMBIGUOUS", "status": "pass", "note": "лишнее пояснение"},
                ], "defects": [
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
        if schema is EdgeReviewOut:
            # По умолчанию граничных случаев нет: остальные тесты считают замечания первых двух проходов.
            return EdgeReviewOut.model_validate({"findings": []})
        if schema is CriticOut:
            # По умолчанию критик оставляет все замечания из списка как есть.
            ids = re.findall(r"^([DS]-\d+) \|", user, re.MULTILINE)
            return CriticOut.model_validate({"decisions": [
                {"finding_id": i, "action": "keep", "severity": None, "into": None, "reason": "верно"} for i in ids]})
        if schema is FinalOut:
            return FinalOut.model_validate({"rationale": "Есть блокеры.", "top_fixes": [
                {"finding_ids": ["S-01", "X-404"], "action": "Оставить одно число."},
                {"finding_ids": ["нет"], "action": "Мимо."},
            ], "questions": [
                _question(["S-01", "D-99"], 2, recommended=1, addressee="business"),
                _question(["s-01"], 3),  # тот же набор замечаний: сливается с первым
                _question(["S-02", "S-03"], 1),  # один вариант: отброшен
                _question(["X-1"], 2),  # нет существующих замечаний: отброшен
                _question(["S-02"], 5, recommended=7),  # вариантов больше четырёх, номер рекомендации мимо
            ]})
        raise AssertionError(schema)


def use(monkeypatch, llm):
    monkeypatch.setattr(cli, "LLMClient", lambda settings, log=None: llm)
    return llm


def run(*extra):
    return cli.main(["-i", "spec.md", "-o", "out/report.md", "-q", *extra])


class FatalAt(FakeLLM):
    def __init__(self, schema, kind):
        super().__init__()
        self.fatal_schema, self.kind = schema, kind

    def complete_json(self, step, system, user, schema, kind="", **opts):
        if schema is self.fatal_schema:
            raise LLMFatal("суточная квота исчерпана", kind=self.kind)
        return super().complete_json(step, system, user, schema, kind)


class OneOut(BaseModel):
    answer: str


class TwoOut(BaseModel):
    value: str


ONE = '{"answer": "ок"}'
TWO = '{"value": "ок"}'


def completion(content: str, finish: str = "stop") -> dict:
    return {
        "id": "1", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def error(code: int, message: str, **extra) -> dict:
    return {"error": {"code": code, "message": message, **extra}}


def ask(client, schema=OneOut, **kw):
    return client.complete_json("шаг", "system", "user", schema, kind="review", **kw)


def _req(n: int, line: int, quote: str = "Система сохраняет порог.") -> Requirement:
    return Requirement(id=f"REQ-0{n}", source_id=None, section="Раздел", line_start=line, line_end=line,
                       kind="functional", summary="суть", quote=quote)


def _f(fid: str, scope: str, lines: list[int], req_ids: list[str], severity: str = "MAJOR", **kw) -> Finding:
    return Finding(id=fid, scope=scope, criterion="COMPLETE" if scope == "requirement" else "SET_COMPLETE",
                   severity=severity, req_ids=req_ids, problem=kw.pop("problem", f"Проблема {fid}."),
                   recommendation="Исправить.", evidence=[Evidence(quote=f"цитата {n}", line=n) for n in lines], **kw)


def _result(findings: list[Finding], requirements: list[Requirement] | None = None, **kw) -> RunResult:
    reqs = requirements or [_req(1, 10), _req(2, 20), _req(3, 30), _req(4, 40)]
    blockers = [f.id for f in sorted((f for f in findings if f.severity == "CRITICAL" and f.status in ("confirmed", "unreviewed")),
                                     key=lambda f: f.scope != "set")]
    verdict = kw.pop("verdict", None) or Verdict(
        decision="Не рекомендуется начинать" if blockers else "Условно допускается", ready_for_development="Нет",
        ready_for_testing="Нет", rule="правило", rationale="обоснование", blockers=blockers, critic_done=True)
    return RunResult(
        document_name="doc.md", document_format="md", document_lines=50, document_sha256="0" * 64,
        started_at="2026-11-27 10:00:00 +0500", provider="custom", model="fake", agent_version="test",
        requirements=reqs, findings=findings, verdict=verdict, grounding=GroundingStats(),
        llm=kw.pop("llm", None) or LLMStats(), **kw,
    )


class _Seg(FakeLLM):
    """Нарезка с заданным ответом, остальное как у FakeLLM."""

    def __init__(self, seg: dict | Exception, critic: Exception | None = None):
        super().__init__()
        self.seg, self.critic_error = seg, critic

    def complete_json(self, step, system, user, schema, kind=""):
        if schema is SegmentationOut:
            self.steps.append(step)
            self.stats.calls += 1
            if isinstance(self.seg, Exception):
                raise self.seg
            return SegmentationOut.model_validate(self.seg)
        if schema is CriticOut and self.critic_error:
            self.steps.append(step)
            raise self.critic_error
        return super().complete_json(step, system, user, schema, kind)


def _settings():
    from test_core import SETTINGS
    return SETTINGS
