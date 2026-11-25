"""Схемы данных.

Классы с суффиксом Out описывают JSON, который обязана вернуть модель.
Остальные классы хранят итог прогона, из него строятся отчёт и report.json.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .criteria import REQ_CODES, SET_CODES

Severity = Literal["CRITICAL", "MAJOR", "MINOR"]
SEVERITY_SET = {"CRITICAL", "MAJOR", "MINOR"}
Kind = Literal[
    "functional", "nonfunctional", "data", "interface", "ui",
    "process", "constraint", "acceptance", "other",
]
KINDS = set(Kind.__args__)  # type: ignore[attr-defined]
Addressee = Literal["business", "analyst", "architect", "security", "qa"]
ADDRESSEE_SET = set(Addressee.__args__)  # type: ignore[attr-defined]
SkipReason = Literal["heading", "service", "history", "checklist", "template", "intro", "other"]
SKIP_REASONS = set(SkipReason.__args__)  # type: ignore[attr-defined]
FindingStatus = Literal[
    "confirmed", "unreviewed", "downgraded", "merged", "dropped", "quarantine", "question_only",
]


def _upper(value):
    return value.strip().upper() if isinstance(value, str) else value


def _lower(value):
    return value.strip().lower() if isinstance(value, str) else value


def _addressee(value):
    value = _lower(value)
    return value if value in ADDRESSEE_SET else None


def _enum_str(values, description: str):
    """Строка с перечнем допустимых значений в схеме, но без отказа при проверке.

    Модель видит enum и почти всегда попадает в него. Если промахнулась, код
    отбросит один этот элемент, а не весь ответ (К-04).
    """
    return Field(description=description, json_schema_extra={"enum": list(values)})


# ---------- ответы модели ----------
#
# С-01: в классах Out нет значений по умолчанию, необязательное поле объявлено как X | None.
# Строгая схема (parse, json_schema strict) требует все поля. Числовых и строковых
# ограничений (minimum, maxLength) тоже нет: Claude отвечает на них 400
# («For 'integer' type, property 'minimum' is not supported», живой вызов 26.11.2026),
# Gemini их молча отбрасывает. Границы проверяет код.


class SegItem(BaseModel):
    line_start: int = Field(description="Номер первой строки требования")
    line_end: int = Field(description="Номер последней строки требования")
    source_id: str | None = Field(description="Идентификатор требования в документе или null")
    section: str = Field(description="Заголовок ближайшего раздела")
    kind: Kind
    summary: str = Field(description="Суть требования своими словами, до 15 слов")

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value):
        value = _lower(value)
        return value if value in KINDS else "other"


class SkippedOut(BaseModel):
    line_start: int
    line_end: int
    reason: SkipReason = Field(description="Почему эти строки не требование")

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value):
        value = _lower(value)
        return value if value in SKIP_REASONS else "other"


class SegmentationOut(BaseModel):
    requirements: list[SegItem]
    skipped: list[SkippedOut] = Field(description="Строки с текстом, которые не являются требованиями")


class CriterionCheckOut(BaseModel):
    criterion: str = _enum_str(REQ_CODES, "Код критерия")
    status: str = _enum_str(("fail", "na", "unknown"), "fail нарушен, na не применим, unknown нельзя оценить по тексту")
    note: str = Field(description="До 20 слов: почему нарушен, не применим или не оценивается")

    _norm_c = field_validator("criterion", mode="before")(_upper)
    _norm_s = field_validator("status", mode="before")(_lower)


class DefectOut(BaseModel):
    criterion: str = _enum_str(REQ_CODES, "Код критерия")
    severity: str = _enum_str(("CRITICAL", "MAJOR", "MINOR"), "Уровень критичности")
    evidence: str = Field(description="Дословная цитата из текста требования")
    line: int | None = Field(description="Номер строки документа, где стоит цитата")
    problem: str = Field(description="Что не так, 1-2 предложения")
    impact: str = Field(description="Что из-за этого нельзя сделать: реализовать, проверить, оценить срок")
    recommendation: str = Field(description="Что сделать автору")
    question: str | None = Field(description="Вопрос автору ТЗ. Обязателен для CRITICAL и MAJOR")
    addressee: Addressee | None = Field(description="Кому вопрос. null только вместе с question: null")

    _norm = field_validator("criterion", "severity", mode="before")(_upper)
    _addr = field_validator("addressee", mode="before")(_addressee)


class ReqReviewOut(BaseModel):
    req_id: str
    checks: list[CriterionCheckOut] = Field(description="Оценки только по критериям со статусом не pass")
    defects: list[DefectOut]
    rewritten: str | None = Field(description="Исправленная формулировка или null")


class BatchReviewOut(BaseModel):
    reviews: list[ReqReviewOut]


class QuoteOut(BaseModel):
    quote: str = Field(description="Дословная цитата из одной строки документа")
    line: int | None = Field(description="Номер строки цитаты")


class SetFindingOut(BaseModel):
    kind: str = _enum_str(("contradiction", "gap", "other"), "contradiction противоречие, gap пробел, other прочее")
    criterion: str = _enum_str(SET_CODES, "Код критерия набора")
    severity: str = _enum_str(("CRITICAL", "MAJOR", "MINOR"), "Уровень критичности")
    title: str = Field(description="Суть замечания одной фразой")
    req_ids: list[str] = Field(description="Идентификаторы затронутых требований (REQ-...)")
    section: str | None = Field(description="Раздел документа, где должны быть сведения, или null")
    evidence: list[QuoteOut]
    problem: str
    impact: str = Field(description="Что из-за этого нельзя сделать")
    recommendation: str
    question: str | None = Field(description="Вопрос автору ТЗ. Обязателен для gap, CRITICAL и MAJOR")
    addressee: Addressee | None

    _norm = field_validator("criterion", "severity", mode="before")(_upper)
    _kind = field_validator("kind", mode="before")(_lower)
    _addr = field_validator("addressee", mode="before")(_addressee)


class SetAnalysisOut(BaseModel):
    criterion: str = _enum_str(SET_CODES, "Код критерия набора")
    status: str = _enum_str(("ok", "partial", "fail", "unknown"), "Итог по критерию")
    analysis: str = Field(description="1-3 предложения: что с чем сравнивали и что вышло")

    _norm_c = field_validator("criterion", mode="before")(_upper)
    _norm_s = field_validator("status", mode="before")(_lower)


class SetReviewOut(BaseModel):
    analyses: list[SetAnalysisOut]
    findings: list[SetFindingOut]


class TopFix(BaseModel):
    finding_ids: list[str] = Field(description="Идентификаторы замечаний из списка (D-... и S-...)")
    action: str = Field(description="Одно конкретное действие для аналитика")


class OptionOut(BaseModel):
    answer: str = Field(description="Вариант ответа")
    consequence: str = Field(description="Что придётся поменять в документе или в реализации при этом ответе")


class QuestionOut(BaseModel):
    text: str = Field(description="Один закрытый вопрос, до 40 слов")
    addressee: Addressee | None = Field(description="Кто знает ответ")
    options: list[OptionOut] = Field(description="2-4 варианта ответа")
    recommended: int | None = Field(description="Номер рекомендуемого варианта (с 1) или null, если выбрать может только бизнес")
    why_recommended: str | None = Field(description="Почему рекомендуем, одна фраза, или null")
    blocks: str = Field(description="Что нельзя сделать без ответа")
    doc_says: str | None = Field(description="Что документ говорит сейчас, одной фразой; null для пробела")
    finding_ids: list[str] = Field(description="Идентификаторы замечаний (D-..., S-...), которые закрывает ответ")

    _addr = field_validator("addressee", mode="before")(_addressee)


class FinalOut(BaseModel):
    rationale: str
    top_fixes: list[TopFix]
    questions: list[QuestionOut]


# ---------- итог прогона ----------


class Requirement(BaseModel):
    id: str
    source_id: str | None
    section: str
    line_start: int
    line_end: int
    page: int | None = None
    kind: str
    summary: str
    quote: str
    lint_hints: list[str] = Field(default_factory=list)
    # Подсказки линтера, слово из которых есть в цитате хотя бы одного дефекта (К-04).
    lint_confirmed: list[str] = Field(default_factory=list)


class CriterionCheck(BaseModel):
    criterion: str
    # pass ставит код для критериев, которые модель не назвала; fail, na, unknown приходят от модели.
    status: Literal["pass", "fail", "na", "unknown"]
    note: str = ""


class SetAnalysis(BaseModel):
    criterion: str
    status: Literal["ok", "partial", "fail", "unknown"]
    analysis: str


class SkippedSpan(BaseModel):
    line_start: int
    line_end: int
    reason: str


class Evidence(BaseModel):
    quote: str
    line: int | None = None
    # exact: цитата найдена в документе; fuzzy: восстановлена по близкому совпадению;
    # missing: в документе не найдена, приведена цитата модели (К-06).
    status: Literal["exact", "fuzzy", "missing"] = "exact"


class Finding(BaseModel):
    id: str = ""
    scope: Literal["requirement", "set"]
    kind: Literal["defect", "contradiction", "gap", "other"] = "defect"
    criterion: str
    severity: Severity
    title: str = ""
    req_ids: list[str] = Field(default_factory=list)
    section: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    problem: str
    impact: str = ""
    recommendation: str
    question: str | None = None
    addressee: str | None = None
    # Сводный вопрос раздела 7, который закрывает это замечание (К-08).
    question_id: str | None = None
    # unreviewed: критик не смотрел. Остальные статусы ставят критик и сверка цитат (4.6).
    status: FindingStatus = "unreviewed"
    # Решение критика (желательный шаг 7): причина и цель слияния.
    critic_reason: str | None = None
    merged_into: str | None = None
    # Места системного замечания, свёрнутого кодом из одинаковых (К-07, Р-11).
    places: list[str] = Field(default_factory=list)


# Замечания с этими статусами не входят в вердикт и сводку (К-06, К-07, К-09).
INACTIVE_STATUSES = {"dropped", "merged", "quarantine", "question_only"}


class Option(BaseModel):
    answer: str
    consequence: str


class Question(BaseModel):
    id: str
    text: str
    addressee: str
    options: list[Option] = Field(default_factory=list)
    recommended: int | None = None
    why_recommended: str | None = None
    blocks: str = ""
    doc_says: str | None = None
    finding_ids: list[str]
    # Считает код: вес уровня связанных замечаний плюс 0,25 за каждое затронутое требование (К-08).
    priority: float = 0.0
    req_ids: list[str] = Field(default_factory=list)
    # Цитаты со строками из связанных замечаний, подставляет код.
    quotes: list[Evidence] = Field(default_factory=list)
    # model: сводный вопрос от модели; fallback: собран кодом из поля question замечания.
    source: Literal["model", "fallback"] = "model"


Decision = Literal["Не рекомендуется начинать", "Условно допускается", "Допускается"]


class Verdict(BaseModel):
    # Решение по правилу К-09, его считает код.
    decision: Decision
    ready_for_development: str
    ready_for_testing: str
    rule: str
    rationale: str
    top_fixes: list[TopFix] = Field(default_factory=list)
    # CRITICAL, из-за которых разработку начинать не рекомендуется.
    blockers: list[str] = Field(default_factory=list)
    # Критик перепроверил критичные замечания (желательный шаг 7, пока не включён).
    critic_done: bool = False
    generated_by_model: bool = True
    # Сводные вопросы сформированы моделью; False значит запасной путь из полей question.
    questions_by_model: bool = True


class GroundingStats(BaseModel):
    exact: int = 0
    fuzzy: int = 0
    missing: int = 0
    # Замечание без опоры на текст: ни цитаты, ни требования, ни раздела. В отчёт не попадает.
    dropped_findings: int = 0
    # Замечание по требованию без единой найденной цитаты (К-06).
    quarantine: int = 0
    # Противоречие, подтверждённое меньше чем двумя цитатами из разных строк (К-06).
    question_only: int = 0
    # Одинаковые замечания в трёх и более местах свёрнуты в системные (К-07, Р-11).
    folded: int = 0


class QualityStats(BaseModel):
    # Доля содержательных строк, вошедших в требования или отмеченных моделью как не требования.
    content_lines: int = 0
    in_requirements: int = 0
    skipped_by_model: int = 0
    # Сверка нарезки с идентификаторами, которые код нашёл в документе (К-03).
    ids_in_document: int = 0
    ids_missing: list[str] = Field(default_factory=list)
    # Ответ модели прошёл схему, но элемент отброшен кодом (неверный код критерия, уровень и т.п.).
    dropped_defects: int = 0
    dropped_checks: int = 0
    defects_without_question: int = 0
    # Сводные вопросы: отброшены проверкой (нет ссылок, меньше двух вариантов), слиты как дубли,
    # добавлены кодом для CRITICAL, которые модель не покрыла вопросом.
    questions_dropped: int = 0
    questions_merged: int = 0
    questions_added: int = 0


class LLMStats(BaseModel):
    calls: int = 0
    cache_hits: int = 0
    retries: int = 0
    repairs: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0


class StepStat(BaseModel):
    """Итог одного шага конвейера (К-01, 4.6). Номера как в таблице шагов: 0-9 и 5в."""

    number: str
    name: str
    # ok: выполнен; degraded: выполнен частично; failed: не выполнен; skipped: шаг не включён.
    status: Literal["ok", "degraded", "failed", "skipped"] = "ok"
    calls: int = 0
    cache_hits: int = 0
    retries: int = 0
    seconds: float = 0.0
    summary: str = ""
    reason: str = ""


class RunResult(BaseModel):
    document_name: str
    document_format: str
    document_lines: int
    document_sha256: str
    started_at: str
    duration_sec: float = 0.0
    provider: str
    model: str
    agent_version: str
    requirements: list[Requirement]
    findings: list[Finding]
    rewritten: dict[str, str] = Field(default_factory=dict)
    unreviewed: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    uncovered_lines: list[tuple[int, int]] = Field(default_factory=list)
    skipped_lines: list[SkippedSpan] = Field(default_factory=list)
    checks: dict[str, list[CriterionCheck]] = Field(default_factory=dict)
    set_analyses: list[SetAnalysis] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    steps: list[StepStat] = Field(default_factory=list)
    # Режим ответа JSON, на котором закончился прогон: parse, schema, object, none.
    json_mode: str = ""
    verdict: Verdict
    grounding: GroundingStats
    quality: QualityStats = Field(default_factory=QualityStats)
    llm: LLMStats
