"""Конвейер проверки. Номера шагов те же, что в журнале прогона и в отчёте.

Шаги:
0. Чтение документа: строки с номерами, разметка таблиц и заголовков (loader, pdfread).
3. Нарезка: модель размечает границы требований по номерам строк, цитаты вырезает код.
   Требование со своим идентификатором, которое модель пропустила, код добавляет сам.
4. Проверка каждого требования порциями, с подсказками словаря и контекстом документа.
5. Набор целиком: три прохода (согласованность, затем полнота и остальное, затем неописанные
   граничные случаи по классам). Каждый следующий видит найденное раньше и не повторяет его.
6. Нумерация и свёртка замечаний. Цитаты модели сверяются с документом раньше, сразу при
   разборе ответов шагов 4 и 5 (_ground); здесь в журнал идут итоговые счётчики сверки.
7. Критик: второй ревьюер по CRITICAL и MAJOR (оставить, понизить, снять, слить).
8. Итог: решение считает правило (К-09), модель пишет обоснование, порядок исправлений
   и сводные вопросы автору; ссылки, варианты, приоритет и цитаты вопросов проверяет код (К-08).
9. Запись отчёта: делает командная строка (cli).

Номера 1 и 2 в нумерации не заняты, номера остальных шагов от этого не меняются. Словарь
расплывчатых формулировок (lint) работает внутри шагов 3 и 4.

Сбой одного шага не роняет прогон: обрезанная порция делится пополам, непроверенное
перечисляется в отчёте. Фатальная ошибка модели (квота, лимит, сеть) ловится на шаге:
оставшиеся шаги с моделью пропускаются, отчёт пишется частичным (К-10). Без отчёта
прогон останавливает только фатальная ошибка до первого ответа модели: тогда прежний
отчёт остаётся на месте.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel

from . import prompts
from .config import Settings
from .criteria import REQ_CODES, SET_CODES, SEVERITY_ORDER
from .grounding import TextIndex, clean_quote, distinct_quotes, normalize
from .lint import lint, placeholders
from .llm import LLMError, LLMFatal, LLMNetworkError, LLMSchemaError, LLMTruncated
from .loader import Document
from .schemas import (
    DIVERGENCE_RAISE,
    DIVERGENCES,
    INACTIVE_STATUSES,
    SEVERITY_SET,
    BatchReviewOut,
    CriterionCheck,
    CriticOut,
    CriticStats,
    Evidence,
    FinalOut,
    Finding,
    GroundingStats,
    LLMStats,
    Option,
    QualityStats,
    Question,
    ReqReviewOut,
    Requirement,
    RunResult,
    SegItem,
    SegmentationOut,
    SetAnalysis,
    EdgeReviewOut,
    SetReviewOut,
    SkippedSpan,
    StepStat,
    TopFix,
    Verdict,
)

T = TypeVar("T", bound=BaseModel)

SEG_CHUNK_LINES = 350
FULL_CONTEXT_CHARS = 60_000
CONTEXT_MARGIN_LINES = 40
# Критик на длинном документе видит строки вокруг цитат, а не весь текст.
CRITIC_MARGIN_LINES = 8
MAX_EVIDENCE_CHARS = 300
_NO_ID = {"", "-", "null", "none", "нет", "n/a", "отсутствует"}
_REQ_REF_RE = re.compile(r"REQ-?(\d+)", re.IGNORECASE)
# Идентификатор требования в начале строки: «FR-1.», «**ФТ-2**», «| NFR-3.1 |». Буквы, дефис, номер.
_DOC_ID_RE = re.compile(r"^[\s>|#*_`-]*\**([A-ZА-ЯЁ][A-Za-zА-Яа-яЁё]{0,7}-\d+(?:\.\d+)*)\**[.:)]?(?=[\s*|`]|$)")
_ADDRESSEE_DEFAULT = "analyst"
STEP_STATUS_WORD = {"failed": "не выполнен", "degraded": "частично"}
# Названия шагов в журнале и отчёте. Шаг 6 не сверяет цитаты сам: сверка идёт при разборе ответов шагов 4 и 5.
STEP_NAMES = {
    "4": "Проверка каждого требования",
    "5": "Набор требований целиком (три прохода)",
    "6": "Нумерация и свёртка замечаний, итог сверки цитат",
    "7": "Критик",
    "8": "Итог и сводные вопросы",
}
EDGE_STEP = "набор: граничные случаи"
NO_REQUIREMENTS = "В документе не найдено требований: все строки с текстом отмечены как не требования."

# Критерии, без которых нельзя писать тесты: дефект CRITICAL по ним блокирует тестирование.
TESTING_BLOCKERS = {"VERIFIABLE", "UNAMBIGUOUS", "COMPLETE", "SET_CONSISTENT", "SET_COMPLETE", "SET_VALIDATABLE"}
DECISIONS = ("Не рекомендуется начинать", "Условно допускается", "Допускается")
# Отчёт неполный и CRITICAL не найден: положительного решения быть не может (К-10).
NO_DECISION, NOT_DEFINED = "Не вынесен", "Не определена"
# Правило вердикта К-09. Печатается в отчёте как есть.
DECISION_RULE = (
    "«Не рекомендуется начинать», если есть хотя бы одно замечание CRITICAL, которое не снято критиком "
    "и не ушло в карантин из-за ненайденной цитаты. «Условно допускается», если CRITICAL нет, но есть MAJOR. "
    "«Допускается», если есть только MINOR или замечаний нет. "
    "Готовность к тестированию считается отдельно: «Нет», если есть CRITICAL по проверяемости, однозначности, "
    "полноте, согласованности или валидируемости; «Да, с оговорками», если есть другие CRITICAL или MAJOR; иначе «Да». "
    "Если отчёт неполный, а CRITICAL не найден, решение «Не вынесен», готовность «Не определена»."
)
# Потолок сводных вопросов в одном ответе модели: больше не влезает в лимит длины (живой прогон 26.11).
MAX_QUESTIONS = 15
# Сводный вопрос с двумя знаками вопроса или с «и/или» склеивает два решения (К-08).
_DOUBLE_QUESTION = re.compile(r"\?.*\?|\bи\s*/\s*или\b", re.S)
# Свёртка: одинаковое замечание минимум в стольких требованиях становится системным (К-07).
FOLD_MIN_PLACES = 3
# Вес уровня в приоритете сводного вопроса (К-08).
SEVERITY_WEIGHT = {"CRITICAL": 5.0, "MAJOR": 2.0, "MINOR": 0.5}
# Сколько требований учитывается в весе сводного вопроса (по 0,25 за каждое).
REQ_BONUS_MAX = 2


class JsonLLM(Protocol):
    stats: LLMStats

    def complete_json(self, step: str, system: str, user: str, schema: type[T], kind: str = "", **opts) -> T: ...


_RANGE_DASH_RE = re.compile(r"(\w)\s*[\u2013\u2014]\s*(\w)")
# Куски текста модели, где тире принадлежит документу: «цитата в ёлочках» и `код`.
_KEEP_DASH_RE = re.compile(r"«[^«»\n]*»|`[^`\n]+`")
_FENCE_LINE_RE = re.compile(r"^\s*(```|~~~)")


def tidy(text: str | None) -> str | None:
    """Текст, который написала модель: без длинных и коротких тире (правило стиля отчёта).

    Диапазон «1–64» становится «1-64», вставка « — » становится запятой. Текст документа не
    меняется: тире внутри «ёлочек», `кода`, блоков кода и строк таблицы остаются, строка из одного
    тире (пустое значение) тоже. Цитаты замечаний этой функцией не обрабатываются.
    """
    if not text:
        return text
    # Разметка строк из промпта (L0068) в тексте модели: в отчёт идёт «строка 68». Короткие L68 не трогаем:
    # в чужом документе это может быть обозначение, а не номер строки. Критик правится отдельно.
    text = _plain_lines(text, padded_only=True)
    lines, fenced = [], False
    for line in text.split("\n"):
        if _FENCE_LINE_RE.match(line):
            fenced = not fenced
            lines.append(line)
        elif fenced or line.lstrip().startswith("|") or re.fullmatch(r"\s*[\u2013\u2014-]\s*", line):
            lines.append(line)
        else:
            parts, pos = [], 0
            for m in _KEEP_DASH_RE.finditer(line):
                parts += [_tidy_dashes(line[pos:m.start()]), m.group(0)]
                pos = m.end()
            lines.append("".join(parts) + _tidy_dashes(line[pos:]))
    return "\n".join(lines)


def _tidy_dashes(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"(\d)\s*[\u2013\u2014]\s*(\d)", r"\1-\2", text)
    # Диапазон идентификаторов «ФТ-1 — ФТ-4»: остаётся диапазоном, через дефис.
    text = re.sub(r"(\d)\s+[\u2013\u2014]\s+(?=\w+-\d)", r"\1 - ", text)
    text = re.sub(r"\s+[\u2013\u2014]\s+", ", ", text)
    text = _RANGE_DASH_RE.sub(r"\1-\2", text)
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _tidy_result(result: "RunResult") -> None:
    for r in result.requirements:
        r.summary = tidy(r.summary)
    for f in result.findings:
        f.title, f.problem, f.impact = tidy(f.title), tidy(f.problem), tidy(f.impact)
        f.recommendation, f.question = tidy(f.recommendation), tidy(f.question)
    result.rewritten = {k: tidy(v) for k, v in result.rewritten.items()}
    for checks in result.checks.values():
        for c in checks:
            c.note = tidy(c.note)
    for a in result.set_analyses:
        a.analysis = tidy(a.analysis)
    v = result.verdict
    v.rationale = tidy(v.rationale)
    for fix in v.top_fixes:
        fix.action = tidy(fix.action)
    for q in result.questions:
        q.text, q.blocks, q.doc_says, q.why_recommended = tidy(q.text), tidy(q.blocks), tidy(q.doc_says), tidy(q.why_recommended)
        for o in q.options:
            o.answer, o.consequence = tidy(o.answer), tidy(o.consequence)


_LINE_MARK = r"L0*\d+(?![\w-])"
_LINE_MARK_RE = re.compile(
    rf"(?<![\w-])(?P<pre>(?:в|на)\s+)?(?P<word>строк[а-я]*\s+)?(?P<marks>{_LINE_MARK}(?:\s*(?:,|и)\s*{_LINE_MARK})*)")


def _plain_lines(text: str, padded_only: bool = False) -> str:
    """Служебные номера строк из разметки промпта (L0068) в обычные слова: «в строке 68», «строки 68 и 72»."""

    def repl(m: re.Match) -> str:
        if padded_only and not re.fullmatch(r"(?:L0\d{3}(?:\s*(?:,|и)\s*)?)+", m.group("marks")):
            return m.group(0)
        numbers = [str(int(n)) for n in re.findall(r"L0*(\d+)", m.group("marks"))]
        listed = numbers[0] if len(numbers) == 1 else ", ".join(numbers[:-1]) + " и " + numbers[-1]
        if m.group("word"):
            return f"{m.group('pre') or ''}{m.group('word')}{listed}"
        if m.group("pre"):
            return f"{m.group('pre')}{'строке' if len(numbers) == 1 else 'строках'} {listed}"
        return f"{'строка' if len(numbers) == 1 else 'строки'} {listed}"

    return _LINE_MARK_RE.sub(repl, text)


_STEP_PREFIX_RE = re.compile(r"^\[[^\]]*\]\s*")


def error_reason(exc: Exception, limit: int = 200) -> str:
    """Причина сбоя для журнала: вид (обрезка, схема, другое) и короткий текст ошибки."""
    text = _STEP_PREFIX_RE.sub("", " ".join(str(exc).split()))
    if isinstance(exc, LLMTruncated):
        kind = "обрезка"
    elif isinstance(exc, LLMSchemaError) or "валидный JSON" in text:
        kind = "схема"
    elif isinstance(exc, LLMNetworkError):
        kind = "сеть"
    else:
        kind = "другое"
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return f"{kind}: {text}" if text else kind


def make_id(prefix: str, number: int, total: int) -> str:
    """REQ-01, D-01: две цифры, три при числе больше 99 (К-03, О-03)."""
    return f"{prefix}-{number:0{3 if total > 99 else 2}d}"


def _norm_doc_id(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").strip().strip("*`.:)")).upper()


def _id_prefix(ident: str) -> str:
    """Буквенная часть идентификатора: «ФТ-5» и «NFR-3.1» дают «ФТ» и «NFR»."""
    return _norm_doc_id(ident).split("-", 1)[0]


def _with_trailing_dash(quote: str, line: str) -> str:
    """Цитата обрывается перед тире, которым строка документа кончается («Адрес: —» как «Адрес:»):
    тире возвращается, иначе пустое значение в документе выглядит обрезанной цитатой."""
    q, full = normalize(quote), normalize(line)
    raw = line.rstrip(" |*\t")
    if q and raw and raw[-1] in "\u2014\u2013-" and full.endswith(q + " -") and not quote.rstrip().endswith(raw[-1]):
        return f"{quote.rstrip()} {raw[-1]}"
    return quote


def _clip(text: str, limit: int = MAX_EVIDENCE_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


class Pipeline:
    def __init__(self, llm: JsonLLM, settings: Settings, log: Callable[[str], None] | None = None):
        self.llm = llm
        self.s = settings
        self.log = log or (lambda _msg: None)
        self.failed_steps: list[str] = []
        self.unreviewed: list[str] = []
        self.n_requirements = 0
        self.grounding = GroundingStats()
        self.quality = QualityStats()
        self.skipped: list[SkippedSpan] = []
        # Куски документа, по которым нарезка получила ответ модели: только в них код добирает пропущенные идентификаторы.
        self._seg_answered: list[tuple[int, int]] = []
        # Строки с заглушками (TODO, TBD) и сами маркеры: ищет шаг 5, засчитывает _result.
        self._placeholder_marks: dict[int, list[str]] = {}
        self.checks: dict[str, list[CriterionCheck]] = {}
        self.set_analyses: list[SetAnalysis] = []
        self._req_by_number: dict[int, str] = {}
        self.steps: list[StepStat] = []
        self.critic = CriticStats()
        # Сколько замечаний по набору дал каждый проход шага 5 (consistency, completeness, edge).
        self.set_pass_counts: dict[str, int] = {}
        # Фатальная ошибка модели (К-10): после неё шаги с моделью пропускаются, отчёт пишется частичным.
        self.fatal: str | None = None

    # ---------- фатальные ошибки ----------

    def _on_fatal(self, exc: LLMFatal, step: str) -> None:
        """Фатальная ошибка ловится на шаге, а не на прогоне (К-10).

        Исключение одно: модель ещё ни разу не ответила (ключ, модель, квота, лимит, сеть на первой
        же нарезке). Отчёта по документу тогда нет, а прежний отчёт затирать нельзя: ошибка уходит
        в командную строку (код 1), файлы отчёта не пишутся.
        """
        if not self._seg_answered:
            raise exc
        if self.fatal is None:
            self.fatal = str(exc)
            self.log(f"  {step}: фатальная ошибка модели, оставшиеся шаги с моделью пропускаю")
        self.failed_steps.append(f"{step}: не выполнено после фатальной ошибки модели")

    def _blocked(self, step: str) -> bool:
        """Шаг с моделью пропускается, если раньше была фатальная ошибка."""
        if self.fatal is None:
            return False
        self.failed_steps.append(f"{step}: пропущено после фатальной ошибки модели")
        return True

    # ---------- шаг 3: нарезка ----------

    def _chunks(self, doc: Document) -> list[tuple[int, int]]:
        if doc.n <= SEG_CHUNK_LINES:
            return [(1, doc.n)]
        bounds, start = [], 1
        while start <= doc.n:
            end = min(start + SEG_CHUNK_LINES - 1, doc.n)
            if end < doc.n:
                # Режем перед заголовком, чтобы не разорвать раздел.
                for candidate in range(end, start + SEG_CHUNK_LINES // 2, -1):
                    if doc.is_heading(candidate + 1):
                        end = candidate
                        break
            bounds.append((start, end))
            start = end + 1
        return bounds

    def _segment_part(self, doc: Document, start: int, end: int, step: str, whole: bool, depth: int = 0) -> list[SegItem]:
        """Нарезка одного куска. Обрезанный ответ: кусок делится пополам (М-07)."""
        if self._blocked(step):
            return []
        part = None if whole and depth == 0 else (start, end)
        user = prompts.segmentation_prompt(doc.numbered(start, end), doc.outline(), part)
        try:
            out = self.llm.complete_json(step, prompts.SYSTEM, user, SegmentationOut, kind="segment")
        except LLMFatal as exc:
            self._on_fatal(exc, step)
            return []
        except LLMTruncated as exc:
            if depth < 2 and end - start >= 20:
                mid = (start + end) // 2
                self.log(f"  {step}: ответ обрезан, делю строки {start}-{end} пополам")
                return (self._segment_part(doc, start, mid, step + "a", whole, depth + 1)
                        + self._segment_part(doc, mid + 1, end, step + "b", whole, depth + 1))
            self.failed_steps.append(f"{step}: {exc}")
            self.log(f"  {step}: сбой, строки {start}-{end} не нарезаны ({error_reason(exc)})")
            return []
        except LLMError as exc:
            self.failed_steps.append(f"{step}: {exc}")
            self.log(f"  {step}: сбой, строки {start}-{end} не нарезаны ({error_reason(exc)})")
            return []
        self._seg_answered.append((start, end))
        for span in out.skipped:
            a, b = sorted((span.line_start, span.line_end))
            a, b = max(start, a), min(end, b)
            if a <= b:
                self.skipped.append(SkippedSpan(line_start=a, line_end=b, reason=span.reason))
        return list(out.requirements)

    def segment(self, doc: Document) -> list[Requirement]:
        chunks = self._chunks(doc)
        items: list[SegItem] = []
        for index, (start, end) in enumerate(chunks, start=1):
            items.extend(self._segment_part(doc, start, end, f"нарезка {index}/{len(chunks)}", len(chunks) == 1))
        requirements = self._build_requirements(doc, items)
        self._check_ids(doc, requirements)
        added = self._recover_ids(doc, requirements)
        if added:
            requirements = self._build_requirements(doc, items + added)
            self._check_ids(doc, requirements)
        return requirements

    def _recover_ids(self, doc: Document, requirements: list[Requirement]) -> list[SegItem]:
        """Требование со своим идентификатором, которое нарезка пропустила, добавляет код (К-03).

        Добирается только идентификатор с префиксом, который уже есть у принятых требований.
        Берётся первая строка с этим идентификатором, если она не заголовок, не входит в другое
        требование и лежит в куске, по которому модель ответила (сбой нарезки так не маскируется). Конец: строка перед следующей строкой с идентификатором, заголовком, пустой
        строкой, разметкой или уже выделенным требованием.
        """
        # Добираем только идентификаторы с префиксом, который модель уже приняла у других требований:
        # «UTF-8», «ISO-8601», «SHA-256» в начале строки похожи на идентификатор, но требованием не являются.
        prefixes = {_id_prefix(r.source_id) for r in requirements if r.source_id}
        missing = {i for i in self.quality.ids_missing if _id_prefix(i) in prefixes}
        if not missing:
            return []
        taken: set[int] = set()
        for r in requirements:
            taken.update(range(r.line_start, r.line_end + 1))
        id_lines: set[int] = set()
        starts: dict[str, tuple[int, str]] = {}
        for line in doc.lines:
            match = _DOC_ID_RE.match(line.text)
            if not match:
                continue
            id_lines.add(line.no)
            ident = _norm_doc_id(match.group(1))
            answered = any(a <= line.no <= b for a, b in self._seg_answered)
            if ident in missing and ident not in starts and answered and line.no not in taken \
                    and not doc.is_heading(line.no):
                starts[ident] = (line.no, match.group(1).strip("*`.:) "))
        items: list[SegItem] = []
        for ident, (start, raw) in starts.items():
            end = start
            while end < doc.n and doc.is_content(end + 1) and end + 1 not in taken and end + 1 not in id_lines:
                end += 1
            summary = re.sub(r"[*`_|#>]+", " ", doc.text(start, end))
            items.append(SegItem(line_start=start, line_end=end, source_id=raw, section=doc.section_path(start),
                                 kind="other", summary=_clip(summary, 150)))
            self.quality.ids_added.append(raw)
            self._unskip(start, end)
        if items:
            self.log(f"  нарезка: модель пропустила требования с идентификаторами, добавлены кодом: "
                     f"{', '.join(self.quality.ids_added)}")
        return items

    def _unskip(self, start: int, end: int) -> None:
        """Строки, ставшие требованием, убираются из списка пропущенных моделью."""
        kept: list[SkippedSpan] = []
        for span in self.skipped:
            if span.line_end < start or span.line_start > end:
                kept.append(span)
                continue
            if span.line_start < start:
                kept.append(SkippedSpan(line_start=span.line_start, line_end=start - 1, reason=span.reason))
            if span.line_end > end:
                kept.append(SkippedSpan(line_start=end + 1, line_end=span.line_end, reason=span.reason))
        self.skipped = kept

    def _check_ids(self, doc: Document, requirements: list[Requirement]) -> None:
        """Сверка нарезки с идентификаторами, найденными в документе кодом (К-03)."""
        in_doc: list[str] = []
        for line in doc.lines:
            match = _DOC_ID_RE.match(line.text)
            if match:
                ident = _norm_doc_id(match.group(1))
                if ident not in in_doc:
                    in_doc.append(ident)
        known = {_norm_doc_id(r.source_id) for r in requirements if r.source_id}
        # «UTF-8» или «SHA-256» в начале строки не идентификатор требования: если модель приняла
        # идентификаторы, считаем только с их префиксами. Не приняла ни одного: считаем все, это тоже сигнал.
        prefixes = {_id_prefix(i) for i in known}
        if prefixes:
            in_doc = [i for i in in_doc if _id_prefix(i) in prefixes]
        self.quality.ids_in_document = len(in_doc)
        self.quality.ids_missing = [i for i in in_doc if i not in known]

    def _build_requirements(self, doc: Document, items: list[SegItem]) -> list[Requirement]:
        spans: list[tuple[int, int, SegItem]] = []
        for item in items:
            start, end = sorted((item.line_start, item.line_end))
            start, end = max(1, start), min(doc.n, end)
            # Обрезаем пустые строки и разметку по краям диапазона.
            while start <= end and not doc.is_content(start):
                start += 1
            while end >= start and not doc.is_content(end):
                end -= 1
            if start <= end:
                spans.append((start, end, item))
        spans.sort(key=lambda s: (s[0], s[1]))

        kept: list[tuple[int, int, SegItem]] = []
        last_end = 0
        for start, end, item in spans:
            if start <= last_end:  # пересечение с предыдущим требованием
                start = last_end + 1
                while start <= end and not doc.is_content(start):
                    start += 1
                if start > end:
                    continue
            last_end = end
            kept.append((start, end, item))

        requirements: list[Requirement] = []
        for number, (start, end, item) in enumerate(kept, start=1):
            quote = doc.text(start, end).strip("\n")
            source_id = (item.source_id or "").strip().strip("*`.:").strip()
            requirements.append(
                Requirement(
                    id=make_id("REQ", number, len(kept)),
                    source_id=None if source_id.lower() in _NO_ID else source_id,
                    section=doc.section_path(start) or item.section.strip(),
                    line_start=start,
                    line_end=end,
                    page=doc.line(start).page,
                    kind=item.kind,
                    summary=" ".join(item.summary.split()),
                    quote=quote,
                    lint_hints=lint(quote),
                )
            )
            self._req_by_number[number] = requirements[-1].id
        return requirements

    def uncovered(self, doc: Document, requirements: list[Requirement]) -> list[tuple[int, int]]:
        """Содержательные строки, которые не вошли ни в одно требование и не отмечены моделью как не требования."""
        in_reqs, skipped = set(), set()
        for r in requirements:
            in_reqs.update(range(r.line_start, r.line_end + 1))
        for span in self.skipped:
            skipped.update(range(span.line_start, span.line_end + 1))
        content = [no for no in range(1, doc.n + 1) if doc.is_content(no)]
        self.quality.content_lines = len(content)
        self.quality.in_requirements = sum(1 for no in content if no in in_reqs)
        self.quality.skipped_by_model = sum(1 for no in content if no in skipped and no not in in_reqs)
        covered = in_reqs | skipped
        ranges: list[tuple[int, int]] = []
        for no in range(1, doc.n + 1):
            if no in covered or not doc.is_content(no):
                continue
            if ranges and all(not doc.is_content(k) for k in range(ranges[-1][1] + 1, no)):
                ranges[-1] = (ranges[-1][0], no)
            else:
                ranges.append((no, no))
        return ranges

    # ---------- шаг 4: проверка каждого требования ----------

    def _context(self, doc: Document, batch: list[Requirement]) -> tuple[str, bool]:
        full = doc.numbered()
        if len(full) <= FULL_CONTEXT_CHARS:
            return full, True
        start = max(1, min(r.line_start for r in batch) - CONTEXT_MARGIN_LINES)
        end = min(doc.n, max(r.line_end for r in batch) + CONTEXT_MARGIN_LINES)
        return doc.numbered(start, end), False

    def _review_batch(self, doc: Document, batch: list[Requirement], label: str, depth: int = 0) -> dict[str, ReqReviewOut]:
        if self.fatal is not None:
            return {}
        context, is_full = self._context(doc, batch)
        user = prompts.review_prompt(batch, context, is_full)
        try:
            out = self.llm.complete_json(f"проверка {label}", prompts.SYSTEM, user, BatchReviewOut, kind="review")
        except LLMFatal as exc:
            self._on_fatal(exc, f"проверка {label}")
            return {}
        except (LLMTruncated, LLMSchemaError) as exc:
            if len(batch) > 1:
                # Ответ обрезан или не прошёл схему: меньшая порция может пройти, делим пополам.
                self.log(f"  проверка {label}: сбой, делю порцию пополам ({error_reason(exc)})")
                mid = len(batch) // 2
                result = self._review_batch(doc, batch[:mid], label + "a", depth + 1)
                result.update(self._review_batch(doc, batch[mid:], label + "b", depth + 1))
                return result
            self.failed_steps.append(f"проверка {batch[0].id}: {exc}")
            self.log(f"  проверка {label}: сбой, {batch[0].id} не проверено ({error_reason(exc)})")
            return {}
        except LLMError as exc:
            # Сеть, сервер, отказ провайдера: деление порции тут не поможет, а каждая половина ждала бы
            # свои повторы. Порция остаётся без проверки, остальные идут дальше.
            ids = ", ".join(r.id for r in batch)
            self.failed_steps.append(f"проверка {label} ({ids}): {exc}")
            self.log(f"  проверка {label}: сбой, не проверено {ids} ({error_reason(exc)})")
            return {}

        wanted = {r.id: r for r in batch}
        result: dict[str, ReqReviewOut] = {}
        for review in out.reviews:
            req_id = self._norm_req_id(review.req_id)
            if req_id in wanted and req_id not in result:
                result[req_id] = review
        missing = [r for r in batch if r.id not in result]
        if missing and depth < 2 and len(missing) < len(batch):
            # Модель пропустила часть требований: спрашиваем по ним отдельно.
            result.update(self._review_batch(doc, missing, label + "+", depth + 1))
        elif missing and depth < 2 and len(batch) > 1:
            mid = len(batch) // 2
            result.update(self._review_batch(doc, batch[:mid], label + "a", depth + 1))
            result.update(self._review_batch(doc, batch[mid:], label + "b", depth + 1))
        return result

    def review_requirements(self, doc: Document, requirements: list[Requirement], index: TextIndex) -> tuple[list[Finding], dict[str, str]]:
        size = self.s.batch_size
        batches = [requirements[i : i + size] for i in range(0, len(requirements), size)]
        total = len(batches)

        def work(job: tuple[int, list[Requirement]]) -> dict[str, ReqReviewOut]:
            number, batch = job
            if self.fatal is not None:
                return {}
            self.log(f"  порция {number}/{total}: {batch[0].id}..{batch[-1].id}")
            return self._review_batch(doc, batch, f"{number}/{total}")

        jobs = list(enumerate(batches, start=1))
        if self.s.concurrency > 1 and total > 1:
            with ThreadPoolExecutor(max_workers=self.s.concurrency) as pool:
                results = list(pool.map(work, jobs))
        else:
            results = [work(job) for job in jobs]

        reviews: dict[str, ReqReviewOut] = {}
        for result in results:
            reviews.update(result)

        findings: list[Finding] = []
        rewritten: dict[str, str] = {}
        for req in requirements:
            review = reviews.get(req.id)
            if review is None:
                self.unreviewed.append(req.id)
                continue
            req_findings: list[Finding] = []
            for defect in review.defects:
                if defect.criterion not in REQ_CODES or defect.severity not in SEVERITY_SET:
                    # Неверный код критерия или уровня: отбрасываем один дефект, не всю порцию (К-04).
                    self.quality.dropped_defects += 1
                    continue
                question = (defect.question or "").strip() or None
                if question is None and defect.severity != "MINOR":
                    self.quality.defects_without_question += 1
                req_findings.append(
                    Finding(
                        scope="requirement",
                        criterion=defect.criterion,
                        severity=defect.severity,
                        req_ids=[req.id],
                        evidence=[self._ground(defect.evidence, defect.line, [req], index, doc)],
                        problem=defect.problem.strip(),
                        impact=defect.impact.strip(),
                        recommendation=defect.recommendation.strip(),
                        question=question,
                        addressee=(defect.addressee or _ADDRESSEE_DEFAULT) if question else None,
                    )
                )
            for f in req_findings:
                if all(e.status == "missing" for e in f.evidence):
                    # Ни одна цитата не найдена в документе: в сводку и вердикт не входит (К-06).
                    f.status = "quarantine"
                    self.grounding.quarantine += 1
            self.checks[req.id] = self._reconcile_checks(review, req_findings)
            req.lint_confirmed = self._confirm_lint(req, review)
            findings.extend(req_findings)
            if review.rewritten and review.rewritten.strip() and req_findings:
                rewritten[req.id] = review.rewritten.strip()
        return findings, rewritten

    def _reconcile_checks(self, review: ReqReviewOut, findings: list[Finding]) -> list[CriterionCheck]:
        """Оценки по всем девяти критериям от модели, сверенные с дефектами кодом (К-04).

        Дефект важнее оценки: есть дефект, значит fail. fail без дефекта становится unknown.
        Критерий без оценки считается pass, пропуски идут в паспорт.
        """
        failed = {f.criterion for f in findings}
        notes: dict[str, CriterionCheck] = {}
        for check in review.checks:
            if check.criterion not in REQ_CODES or check.status not in ("pass", "fail", "na", "unknown"):
                self.quality.dropped_checks += 1
                continue
            if check.criterion not in notes:
                notes[check.criterion] = CriterionCheck(
                    criterion=check.criterion, status=check.status, note=" ".join(check.note.split())
                )
        result: list[CriterionCheck] = []
        for code in REQ_CODES:
            check = notes.get(code)
            if check is None:
                self.quality.checks_missing += 1
            if code in failed:
                if check is not None and check.status == "pass":
                    self.quality.checks_pass_overridden += 1
                note = check.note if check and check.status != "pass" else ""
                result.append(CriterionCheck(criterion=code, status="fail", note=note))
            elif check is not None and check.status == "pass":
                result.append(CriterionCheck(criterion=code, status="pass"))
            elif check is not None:
                # fail без дефекта: модель сочла критерий нарушенным, но дефект не описала.
                status = "unknown" if check.status == "fail" else check.status
                result.append(CriterionCheck(criterion=code, status=status, note=check.note))
            else:
                result.append(CriterionCheck(criterion=code, status="pass"))
        return result

    @staticmethod
    def _confirm_lint(req: Requirement, review: ReqReviewOut) -> list[str]:
        quotes = " ".join(d.evidence for d in review.defects).casefold()
        confirmed = []
        for hint in req.lint_hints:
            word = hint.split("»", 1)[0].lstrip("«").casefold()
            if word and word in quotes:
                confirmed.append(hint)
        return confirmed

    # ---------- шаг 5: проверка набора ----------

    def review_set(self, doc: Document, requirements: list[Requirement], index: TextIndex) -> list[Finding]:
        numbered = doc.numbered()
        # Заглушки ищем по всему документу: во вводной части и пустых разделах нарезка их не видит.
        marks = placeholders(doc.lines)
        self._placeholder_marks = dict(marks)
        self.quality.placeholder_lines = [no for no, _ in marks]
        Pass = tuple[str, str, Callable[[list[Finding]], str], tuple[str, ...], type[BaseModel]]
        passes: list[Pass] = [
            ("набор: согласованность", "consistency", lambda _found: prompts.consistency_prompt(requirements, numbered),
             ("SET_CONSISTENT", "SET_COMPREHENSIBLE"), SetReviewOut),
            # Второй проход видит, что нашёл первый, и не повторяет это (К-05).
            ("набор: полнота и остальные критерии", "completeness",
             lambda found: prompts.completeness_prompt(requirements, numbered, found, marks),
             tuple(c for c in SET_CODES if c not in ("SET_CONSISTENT", "SET_COMPREHENSIBLE")), SetReviewOut),
        ]
        if self.s.edge:
            # Третий проход: неописанные граничные случаи по классам, без повторов первых двух.
            passes.append((EDGE_STEP, "edge", lambda found: prompts.edge_prompt(requirements, numbered, found),
                           (), EdgeReviewOut))
        known = {r.id: r for r in requirements}
        findings: list[Finding] = []
        for step, origin, build, own, schema in passes:
            if self._blocked(step):
                continue
            user = build(findings)
            self.log(f"  {step}")
            out = self._set_call(step, user, schema)
            if out is None:
                continue
            before = len(findings)
            seen_analyses = {a.criterion for a in self.set_analyses}
            for analysis in getattr(out, "analyses", []):
                if analysis.criterion in own and analysis.criterion not in seen_analyses \
                        and analysis.status in ("ok", "partial", "fail", "unknown"):
                    seen_analyses.add(analysis.criterion)
                    self.set_analyses.append(SetAnalysis(
                        criterion=analysis.criterion, status=analysis.status,
                        analysis=" ".join(analysis.analysis.split()),
                    ))
            for item in out.findings:
                if item.criterion not in SET_CODES or item.severity not in SEVERITY_SET:
                    self.quality.dropped_defects += 1
                    continue
                kind = item.kind if item.kind in ("contradiction", "gap", "other") else "other"
                req_ids = []
                for raw in item.req_ids:
                    req_id = self._norm_req_id(raw)
                    if req_id in known and req_id not in req_ids:
                        req_ids.append(req_id)
                quotes = [(q.quote, q.line) for q in item.evidence]
                evidence = self._ground_all(quotes, [known[i] for i in req_ids], index, doc)
                found = [e for e in evidence if e.status != "missing"]
                question = (item.question or "").strip() or None
                section = (item.section or "").strip() or None
                # Пробелу цитата не обязательна, но нужны вопрос и место, где сведений нет (К-05).
                anchored = bool(found or req_ids) or (kind == "gap" and question and section)
                if not anchored:
                    # Ни подтверждённой цитаты, ни ссылки на требование или раздел: замечание без опоры на текст.
                    self.grounding.dropped_findings += 1
                    continue
                if question is None and item.severity != "MINOR":
                    self.quality.defects_without_question += 1
                divergence = item.divergence if item.divergence in DIVERGENCES else "none"
                severity, raised_from = item.severity, None
                if divergence in DIVERGENCE_RAISE and severity != "CRITICAL" \
                        and len({e.line for e in found}) >= 2:
                    # Два места документа задают разное поведение, расчёт или единицы: реализовать оба нельзя.
                    severity, raised_from = "CRITICAL", item.severity
                    self.quality.severity_raised += 1
                findings.append(
                    Finding(
                        scope="set",
                        kind=kind,
                        criterion=item.criterion,
                        severity=severity,
                        divergence=divergence,
                        severity_raised_from=raised_from,
                        title=item.title.strip(),
                        req_ids=req_ids,
                        section=section,
                        evidence=evidence,
                        problem=item.problem.strip(),
                        impact=item.impact.strip(),
                        recommendation=item.recommendation.strip(),
                        question=question,
                        addressee=(item.addressee or _ADDRESSEE_DEFAULT) if question else None,
                        origin=origin,
                    )
                )
                if kind == "contradiction" and len({e.line for e in found}) < 2:
                    # Противоречие без двух подтверждённых цитат из разных строк: только вопрос (К-06).
                    findings[-1].status = "question_only"
                    self.grounding.question_only += 1
            self.set_pass_counts[origin] = len(findings) - before
            if origin == "edge":
                self.log(f"  {step}: замечаний {len(findings) - before}")
        return findings

    def _set_call(self, step: str, user: str, schema: type[BaseModel] = SetReviewOut) -> BaseModel | None:
        """Один проход по набору. Обрезанный ответ: один повтор с reasoning_effort=low (М-07)."""
        effort = None
        for attempt in (1, 2):
            try:
                return self.llm.complete_json(step, prompts.SYSTEM, user, schema, kind="set",
                                              **({"effort": effort} if effort else {}))
            except LLMFatal as exc:
                self._on_fatal(exc, step)
                return None
            except LLMTruncated as exc:
                if attempt == 1:
                    effort = "low"
                    self.log(f"  {step}: ответ обрезан, повторяю с reasoning_effort=low")
                    continue
                self.failed_steps.append(f"{step}: {exc}")
                self.log(f"  {step}: сбой ({error_reason(exc)})")
            except LLMError as exc:
                self.failed_steps.append(f"{step}: {exc}")
                self.log(f"  {step}: сбой ({error_reason(exc)})")
                return None
        return None

    # ---------- сверка цитат (вызывается из шагов 4 и 5) ----------

    def _norm_req_id(self, raw: str) -> str:
        """REQ-1, REQ-001, req01 приводятся к идентификатору из нарезки."""
        match = _REQ_REF_RE.search(raw or "")
        if match:
            return self._req_by_number.get(int(match.group(1)), (raw or "").strip())
        return (raw or "").strip()

    def _ground(self, quote: str, line: int | None, reqs: list[Requirement], index: TextIndex, doc: Document) -> Evidence:
        """Сверка одной цитаты модели с документом (К-06).

        Порядок: короткая цитата по номеру строки с допуском; точное вхождение в тексте требований,
        затем во всём документе (поиск идёт по склейке строк, так находится и цитата через перенос);
        нечёткое совпадение с порогом FUZZY_SHARE. Не нашлось: статус missing, цитата модели как есть.
        """
        quote = clean_quote(quote or "")
        if index.is_short(quote):
            found = index.find_short(quote, line)
            if found is not None:
                self.grounding.exact += 1
                return Evidence(quote=quote, line=found, status="exact")
        else:
            for start, end in [(r.line_start, r.line_end) for r in reqs] + [(None, None)]:
                found = index.find(quote, start, end)
                if found is not None:
                    self.grounding.exact += 1
                    return Evidence(quote=_clip(_with_trailing_dash(quote, doc.line(found).text)), line=found,
                                    status="exact")
            for start, end in [(r.line_start, r.line_end) for r in reqs] + [(None, None)]:
                found = index.fuzzy(quote, start, end)
                if found is not None:
                    self.grounding.fuzzy += 1
                    return Evidence(quote=_clip(doc.line(found).text), line=found, status="fuzzy")
        self.grounding.missing += 1
        return Evidence(quote=_clip(quote), line=line, status="missing")

    def _ground_all(self, quotes: list[tuple[str, int | None]], reqs: list[Requirement], index: TextIndex, doc: Document) -> list[Evidence]:
        evidence: list[Evidence] = []
        seen: set[tuple[int, str]] = set()
        for quote, line in quotes:
            if not quote or not quote.strip():
                continue
            item = self._ground(quote, line, reqs, index, doc)
            key = (item.line or 0, item.quote)
            if key not in seen:
                seen.add(key)
                evidence.append(item)
        return evidence

    # ---------- шаг 6: свёртка одинаковых замечаний ----------

    @staticmethod
    def _fold_key(f: Finding) -> tuple[str, str]:
        text = re.sub(r"[^\w ]+", " ", f.problem.casefold())
        return f.criterion, " ".join(text.split())

    def fold(self, findings: list[Finding], requirements: list[Requirement]) -> list[tuple[Finding, list[Finding]]]:
        """Один критерий с одинаковым текстом проблемы в трёх и более требованиях даёт одно
        системное замечание со списком мест (К-07, Р-11). Исходные получают статус merged."""
        by_req = {r.id: r for r in requirements}
        groups: dict[tuple[str, str], list[Finding]] = {}
        for f in findings:
            if f.scope == "requirement" and f.status not in INACTIVE_STATUSES:
                groups.setdefault(self._fold_key(f), []).append(f)
        system: list[Finding] = []
        members: list[list[Finding]] = []
        for items in groups.values():
            if len({f.req_ids[0] for f in items}) < FOLD_MIN_PLACES:
                continue
            head = min(items, key=lambda f: SEVERITY_ORDER[f.severity])
            req_ids: list[str] = []
            places: list[str] = []
            evidence: list[Evidence] = []
            for f in items:
                rid = f.req_ids[0]
                if rid not in req_ids:
                    req_ids.append(rid)
                line = next((e.line for e in f.evidence if e.status != "missing"), by_req[rid].line_start)
                places.append(f"{rid}, строка {line}")
                evidence.extend(e for e in f.evidence if e.status != "missing")
            fid_question = next((f for f in items if f.question), None)
            system.append(Finding(
                scope="set", kind="other", criterion=head.criterion, severity=head.severity,
                title=f"Повторяется в {len(req_ids)} требованиях: {head.problem}",
                req_ids=req_ids, evidence=evidence[:5], problem=head.problem, impact=head.impact,
                recommendation=head.recommendation,
                question=fid_question.question if fid_question else None,
                addressee=fid_question.addressee if fid_question else None,
                places=places, status="unreviewed",
            ))
            for f in items:
                f.status = "merged"
            self.grounding.folded += len(items)
            members.append(items)
        return list(zip(system, members))

    # ---------- шаг 7: критик ----------

    def _critic_context(self, doc: Document, findings: list[Finding]) -> tuple[str, bool]:
        full = doc.numbered()
        if len(full) <= FULL_CONTEXT_CHARS:
            return full, True
        spans: list[list[int]] = []
        lines = sorted({e.line for f in findings for e in f.evidence if e.line})
        for line in lines:
            start, end = max(1, line - CRITIC_MARGIN_LINES), min(doc.n, line + CRITIC_MARGIN_LINES)
            if spans and start <= spans[-1][1] + 1:
                spans[-1][1] = max(spans[-1][1], end)
            else:
                spans.append([start, end])
        parts = [doc.numbered(a, b) for a, b in spans]
        text = "\n...\n".join(parts)
        # Строки с номерами должны остаться строками: _clip склеил бы их в одну.
        return text[:FULL_CONTEXT_CHARS], False

    def critique(self, doc: Document, findings: list[Finding]) -> None:
        """Шаг 7 (К-07): второй ревьюер решает по каждому CRITICAL и MAJOR: keep, downgrade, drop, merge.

        Ограничения держит код: нет решения, значит замечание остаётся; уровень не повышается;
        новых замечаний нет; снять или понизить можно только с причиной; merge только в известное
        замечание без циклов, цель получает цитаты, требования и старший из двух уровней.
        """
        st = self.critic
        pool = [f for f in findings if f.status not in INACTIVE_STATUSES and f.severity in ("CRITICAL", "MAJOR")]
        st.reviewed = len(pool)
        if not pool:
            st.done = True
            return
        if self._blocked("критик"):
            return
        context, is_full = self._critic_context(doc, pool)
        candidates = self._merge_candidates(pool)
        st.candidate_groups = len(candidates)
        by_id = {f.id: f for f in pool}
        decisions: dict = {}
        out = self._critic_call(prompts.critic_prompt(pool, context, is_full, candidates))
        if out is None:
            return
        self._collect_decisions(out, by_id, set(by_id), decisions)
        missing = [f for f in pool if f.id not in decisions]
        if missing and not self._blocked("критик"):
            # Один повтор только по замечаниям без решения, остальные даны как возможные цели слияния.
            ids = {f.id for f in missing}
            st.retry_calls = 1
            groups = [(line, g) for line, g in candidates if ids & set(g)]
            targets = [f for f in pool if f.id not in ids]
            self.log(f"  критик: без решения {len(missing)}, повторный запрос только по ним")
            retry = self._critic_call(prompts.critic_prompt(missing, context, is_full, groups, targets=targets))
            if retry is not None:
                before = len(decisions)
                self._collect_decisions(retry, by_id, ids, decisions)
                st.retry_resolved = len(decisions) - before
        if not decisions:
            # Пустой ответ не считается перепроверкой: в отчёте остаётся пометка «не перепроверены».
            st.no_decision = len(pool)
            self.failed_steps.append("критик: модель не вернула ни одного решения")
            return
        st.no_decision = len(pool) - len(decisions)

        merges: dict[str, tuple[str, str]] = {}
        for fid, d in decisions.items():
            f = by_id[fid]
            reason = _plain_lines(" ".join(d.reason.split()))
            if d.action == "keep":
                f.status = "confirmed"
                st.keep += 1
            elif d.action == "downgrade" and reason and d.severity in SEVERITY_SET \
                    and SEVERITY_ORDER[d.severity] > SEVERITY_ORDER[f.severity]:
                f.severity_before, f.severity = f.severity, d.severity
                f.status, f.critic_reason = "downgraded", reason
                st.downgraded += 1
            elif d.action == "drop" and reason:
                f.status, f.critic_reason = "dropped", reason
                st.dropped += 1
            elif d.action == "merge" and reason and d.into:
                merges[fid] = (d.into.strip().upper(), reason)
            else:
                # Повышение уровня, решение без причины, неизвестное действие: замечание остаётся как было.
                st.rejected += 1

        def final_target(fid: str) -> str | None:
            seen = {fid}
            target = merges[fid][0]
            while target in merges:
                if target in seen:
                    return None  # цикл слияний
                seen.add(target)
                target = merges[target][0]
            return target

        for fid, (_, reason) in merges.items():
            src = by_id[fid]
            target_id = final_target(fid)
            target = by_id.get(target_id or "")
            if target is None or target is src or target.status == "dropped":
                st.rejected += 1
                continue
            self._merge_into(src, target)
            src.status, src.merged_into, src.critic_reason = "merged", target.id, reason
            st.merged += 1
        st.done = True

    def _critic_call(self, user: str) -> CriticOut | None:
        """Обрезанный ответ: один повтор с reasoning_effort=low, как у прохода по набору (М-07)."""
        effort = None
        for attempt in (1, 2):
            try:
                return self.llm.complete_json("критик", prompts.SYSTEM, user, CriticOut, kind="critic",
                                              **({"effort": effort} if effort else {}))
            except LLMFatal as exc:
                self._on_fatal(exc, "критик")
                return None
            except LLMTruncated as exc:
                if attempt == 1:
                    effort = "low"
                    self.log("  критик: ответ обрезан, повторяю с reasoning_effort=low")
                    continue
                self.failed_steps.append(f"критик: {exc}")
            except LLMError as exc:
                self.failed_steps.append(f"критик: {exc}")
                return None
        return None

    def _collect_decisions(self, out: CriticOut, by_id: dict, allowed: set[str], decisions: dict) -> None:
        """Первое решение по каждому замечанию из allowed; чужие и повторные идут в отклонённые."""
        for d in out.decisions:
            fid = d.finding_id.strip().upper()
            if fid not in by_id or fid not in allowed or fid in decisions:
                self.critic.rejected += 1
                continue
            decisions[fid] = d

    @staticmethod
    def _merge_candidates(pool: list[Finding]) -> list[tuple[int, list[str]]]:
        """Кандидаты на слияние: замечания, у которых подтверждённые цитаты стоят на одной строке документа.

        Одна группа на строку, одинаковые группы с разных строк не повторяются. Решает критик.
        """
        by_line: dict[int, list[str]] = {}
        for f in pool:
            for line in sorted({e.line for e in f.evidence if e.status != "missing" and e.line}):
                by_line.setdefault(line, []).append(f.id)
        groups, seen = [], set()
        for line in sorted(by_line):
            ids = by_line[line]
            if len(ids) > 1 and tuple(ids) not in seen:
                seen.add(tuple(ids))
                groups.append((line, ids))
        return groups

    @staticmethod
    def _merge_into(src: Finding, target: Finding) -> None:
        # Повтор цитаты, в том числе часть уже взятой строки, не добавляется; ненайденные цитаты цели остаются.
        missing = [e for e in target.evidence if e.status == "missing"]
        target.evidence = distinct_quotes(target.evidence + src.evidence) + missing
        for rid in src.req_ids:
            if rid not in target.req_ids:
                target.req_ids.append(rid)
        if SEVERITY_ORDER[src.severity] < SEVERITY_ORDER[target.severity]:
            target.severity_before = target.severity_before or target.severity
            target.severity = src.severity
        if not target.question and src.question:
            target.question, target.addressee = src.question, src.addressee

    # ---------- шаг 8: итог ----------

    @staticmethod
    def decide(findings: list[Finding]) -> tuple[str, str, str, list[str]]:
        """Решение по правилу К-09, готовность к разработке и тестированию, блокеры.

        Снятые критиком, слитые, ушедшие в карантин и пониженные до вопроса замечания не считаются.
        """
        active = [f for f in findings if f.status not in INACTIVE_STATUSES]
        critical = [f for f in active if f.severity == "CRITICAL"]
        major = [f for f in active if f.severity == "MAJOR"]
        if critical:
            decision, dev = DECISIONS[0], "Нет"
        elif major:
            decision, dev = DECISIONS[1], "Да, с оговорками"
        else:
            decision, dev = DECISIONS[2], "Да"
        if any(f.criterion in TESTING_BLOCKERS for f in critical):
            test = "Нет"
        elif critical or major:
            test = "Да, с оговорками"
        else:
            test = "Да"
        # Блокеры: сначала замечания по набору, потом по требованиям, внутри в исходном порядке.
        blockers = sorted(critical, key=lambda f: f.scope != "set")
        return decision, dev, test, [f.id for f in blockers]

    def _verdict(self, findings: list[Finding], **fields) -> Verdict:
        decision, dev, test, blockers = self.decide(findings)
        partial = self._incomplete()
        if partial:
            # По неполным данным положительного решения нет; найденный CRITICAL решение «Не рекомендуется» оставляет.
            if decision != DECISIONS[0]:
                decision, dev, test = NO_DECISION, NOT_DEFINED, NOT_DEFINED
            reason = self._incomplete_reason()
            fields["rationale"] = f"{reason} {fields.get('rationale', '')}".strip()
            fields["partial_reason"] = reason
        return Verdict(
            decision=decision, ready_for_development=dev, ready_for_testing=test, rule=DECISION_RULE,
            blockers=blockers, critic_done=self.critic.done, partial=partial, **fields,
        )

    def _incomplete_reason(self) -> str:
        """Сколько требований проверено из скольких и какие шаги не выполнены, для обоснования вердикта."""
        parts = []
        if self.n_requirements:
            checked = self.n_requirements - len(set(self.unreviewed))
            parts.append(f"Отчёт неполный: проверено требований {checked} из {self.n_requirements}.")
        else:
            parts.append("Отчёт неполный.")
        bad = [f"{st.number} «{st.name}» ({STEP_STATUS_WORD[st.status]})"
               for st in self.steps if st.status in STEP_STATUS_WORD]
        if bad:
            parts.append("Шаги: " + "; ".join(bad) + ".")
        if self.fatal:
            parts.append("Причина в начале отчёта.")
        return " ".join(parts)

    def _incomplete(self) -> bool:
        """Часть работы модели не выполнена: решение принято по неполным данным (К-10)."""
        return bool(self.fatal or self.unreviewed or any(
            s.startswith(("нарезка", "проверка", "набор")) for s in self.failed_steps))

    def conclude(self, doc: Document, requirements: list[Requirement], findings: list[Finding]) -> tuple[Verdict, list[Question]]:
        """Шаг 8: один вызов даёт обоснование, первоочередные действия и сводные вопросы (К-08)."""
        self.n_requirements = len(requirements)
        active = [f for f in findings if f.status not in INACTIVE_STATUSES]
        if not active:
            # Все замечания сняты критиком, слиты или без опоры на текст: модели не на что ссылаться (Н-3).
            if findings:
                rationale = "Подтверждённых нарушений нет: найденные замечания сняты критиком или не подтверждены цитатой."
            elif self._incomplete():
                rationale = "Агент не нашёл нарушений в той части, которую успел проверить."
            else:
                rationale = "Агент не нашёл нарушений критериев качества."
            verdict = self._verdict(findings, rationale=rationale, generated_by_model=False)
            # Противоречие с одной цитатой остаётся вопросом и здесь (К-06, О-09).
            questions = [self._fallback_question(f) for f in findings if f.status == "question_only" and f.question]
            return verdict, self._number_questions(questions, findings)
        ranked = sorted(active, key=lambda f: (SEVERITY_ORDER[f.severity], f.id))
        decision = self.decide(findings)[0]
        known = {f.id for f in ranked}
        out: FinalOut | None = None
        with_question = sum(1 for f in ranked if f.question and f.severity != "MINOR")
        limit = max(1, min(MAX_QUESTIONS, with_question))
        # Документ целиком нужен, чтобы модель не спрашивала то, на что он уже отвечает. Длинный не передаём.
        numbered = doc.numbered()
        numbered = numbered if len(numbered) <= FULL_CONTEXT_CHARS else None
        for attempt in (1, 2):
            if self._blocked("итог"):
                break
            user = prompts.final_prompt(doc.name, len(requirements), ranked, decision, limit, numbered)
            try:
                out = self.llm.complete_json("итог", prompts.SYSTEM, user, FinalOut, kind="verdict")
                break
            except LLMFatal as exc:
                self._on_fatal(exc, "итог")
                break
            except LLMTruncated as exc:
                if attempt == 1 and limit > 3:
                    # Ответ не влез в лимит длины: один повтор с вдвое меньшим числом вопросов.
                    limit = max(3, limit // 2)
                    self.log(f"  итог: ответ обрезан, повторяю с потолком {limit} вопросов")
                    continue
                self.failed_steps.append(f"итог: {exc}")
                break
            except LLMError as exc:
                self.failed_steps.append(f"итог: {exc}")
                break

        fixes: list[TopFix] = []
        if out is not None:
            for fix in out.top_fixes:
                ids = [i.strip() for i in fix.finding_ids if i.strip() in known]
                if ids and fix.action.strip():
                    fixes.append(TopFix(finding_ids=ids, action=fix.action.strip()))
            if not fixes:
                self.failed_steps.append("итог: модель не сослалась на существующие замечания")

        questions = self._questions(out, ranked) if out is not None else []
        questions_by_model = bool(questions)
        if out is not None and not questions and any(f.question for f in ranked):
            self.failed_steps.append("итог: сводные вопросы не прошли проверку")
        if not questions:
            questions = self._fallback_questions(ranked)
        else:
            questions = self._add_uncovered_critical(questions, ranked)
        # Противоречие с одной цитатой остаётся вопросом в группе «требует проверки» (К-06, О-09).
        questions += [self._fallback_question(f) for f in findings if f.status == "question_only" and f.question]
        questions = self._number_questions(questions, findings)
        # Итоговый счётчик: CRITICAL и MAJOR, у которых нет ни своего вопроса, ни сводного.
        self.quality.defects_without_question = sum(
            1 for f in active if f.severity != "MINOR" and not f.question and not f.question_id)

        if fixes:
            verdict = self._verdict(
                findings, rationale=out.rationale.strip(), top_fixes=fixes[:7], questions_by_model=questions_by_model,
            )
        else:
            # Запасной вариант без модели: самые тяжёлые замечания по порядку.
            verdict = self._verdict(
                findings,
                rationale="Обоснование от модели не получено, список составлен по критичности замечаний.",
                top_fixes=[TopFix(finding_ids=[f.id], action=f.recommendation) for f in ranked[:7]],
                generated_by_model=False, questions_by_model=questions_by_model,
            )
        return verdict, questions

    # ---------- сводные вопросы ----------

    @staticmethod
    def _priority(linked: list[Finding]) -> tuple[float, list[str]]:
        """Вес уровня связанных замечаний плюс 0,25 за каждое затронутое требование, не больше чем за два (К-08).

        Потолок нужен, чтобы таблица, порезанная на много требований, не поднимала свой вопрос выше
        бизнес-правила того же уровня. При равном весе остаётся порядок модели (сортировка устойчивая).
        """
        req_ids: list[str] = []
        for f in linked:
            for req_id in f.req_ids:
                if req_id not in req_ids:
                    req_ids.append(req_id)
        weight = sum(SEVERITY_WEIGHT[f.severity] for f in linked) + 0.25 * min(len(req_ids), REQ_BONUS_MAX)
        return round(weight, 2), req_ids

    @staticmethod
    def _quotes(linked: list[Finding], limit: int = 3) -> list[Evidence]:
        """Цитаты связанных замечаний без повторов: часть строки, уже взятой целиком, не повторяется."""
        return distinct_quotes([e for f in linked for e in f.evidence], limit)

    @staticmethod
    def _main_addressee(linked: list[Finding]) -> str:
        counts = Counter(f.addressee for f in linked if f.addressee)
        return counts.most_common(1)[0][0] if counts else _ADDRESSEE_DEFAULT

    def _questions(self, out: FinalOut, ranked: list[Finding]) -> list[Question]:
        """Проверки сводных вопросов кодом: ссылки, число вариантов, дубли (К-08)."""
        by_id = {f.id: f for f in ranked}
        questions: list[Question] = []
        by_key: dict[frozenset[str], Question] = {}
        for item in out.questions:
            ids: list[str] = []
            for raw in item.finding_ids:
                fid = raw.strip().upper()
                if fid in by_id and fid not in ids:
                    ids.append(fid)
            options = [
                Option(answer=" ".join(o.answer.split()), consequence=" ".join(o.consequence.split()))
                for o in item.options if o.answer.strip()
            ][:4]
            text = " ".join(item.text.split())
            if not ids or not text or len(options) < 2 or _DOUBLE_QUESTION.search(text):
                self.quality.questions_dropped += 1
                continue
            key = frozenset(ids)
            if key in by_key:
                # Тот же набор замечаний: второй вопрос сливается с первым.
                self.quality.questions_merged += 1
                continue
            linked = [by_id[i] for i in ids]
            priority, req_ids = self._priority(linked)
            recommended = item.recommended if isinstance(item.recommended, int) and 1 <= item.recommended <= len(options) else None
            why = " ".join((item.why_recommended or "").split()) or None
            question = Question(
                id="", text=text, addressee=item.addressee or self._main_addressee(linked), options=options,
                recommended=recommended, why_recommended=why if recommended else None,
                blocks=" ".join(item.blocks.split()), doc_says=" ".join((item.doc_says or "").split()) or None,
                finding_ids=ids, priority=priority, req_ids=req_ids, quotes=self._quotes(linked), source="model",
            )
            by_key[key] = question
            questions.append(question)
        return questions

    def _fallback_question(self, f: Finding) -> Question:
        priority, req_ids = self._priority([f])
        return Question(
            id="", text=" ".join((f.question or "").split()), addressee=f.addressee or _ADDRESSEE_DEFAULT,
            blocks=f.impact, finding_ids=[f.id], priority=priority, req_ids=req_ids,
            quotes=self._quotes([f]), source="fallback",
        )

    def _fallback_questions(self, ranked: list[Finding]) -> list[Question]:
        """Запасной путь: вопросы из полей question замечаний по убыванию уровня, без вариантов (К-08)."""
        questions: list[Question] = []
        by_text: dict[str, Question] = {}
        for f in ranked:
            if not f.question:
                continue
            key = " ".join(f.question.split()).casefold()
            if key in by_text:
                # Одинаковый вопрос у нескольких замечаний: один вопрос, закрывает все.
                q = by_text[key]
                q.finding_ids.append(f.id)
                linked = [x for x in ranked if x.id in q.finding_ids]
                q.priority, q.req_ids = self._priority(linked)
                q.quotes = self._quotes(linked)
                continue
            q = self._fallback_question(f)
            by_text[key] = q
            questions.append(q)
        return questions

    def _add_uncovered_critical(self, questions: list[Question], ranked: list[Finding]) -> list[Question]:
        """CRITICAL с вопросом, который модель не взяла ни в один сводный вопрос, не теряется."""
        covered = {fid for q in questions for fid in q.finding_ids}
        for f in ranked:
            if f.severity == "CRITICAL" and f.question and f.id not in covered:
                questions.append(self._fallback_question(f))
                self.quality.questions_added += 1
        return questions

    @staticmethod
    def _number_questions(questions: list[Question], ranked: list[Finding]) -> list[Question]:
        by_id = {f.id: f for f in ranked}

        def order(q: Question) -> tuple:
            linked = [by_id[fid] for fid in q.finding_ids if fid in by_id]
            active = [f for f in linked if f.status not in INACTIVE_STATUSES]
            critical = [f for f in active if f.severity == "CRITICAL"]
            # Первыми вопросы по противоречию мест документа уровня CRITICAL: без ответа нельзя реализовать
            # ни одно из мест. Потом остальные с CRITICAL, потом по весу. При равном весе раньше вопрос по
            # замечанию набора (S): иначе решал бы порядок модели, а у неё D стоят выше S того же уровня.
            contradiction = any(f.scope == "set" and f.kind == "contradiction" for f in critical)
            return (not contradiction, not critical, -q.priority, not any(f.scope == "set" for f in linked))

        questions.sort(key=order)
        for number, q in enumerate(questions, start=1):
            q.id = make_id("Q", number, len(questions))
            for fid in q.finding_ids:
                # У замечания остаётся ссылка на самый важный вопрос, который его закрывает.
                if by_id[fid].question_id is None:
                    by_id[fid].question_id = q.id
        return questions

    # ---------- журнал шагов ----------

    def _begin(self, number: str, name: str) -> tuple[StepStat, float, LLMStats, int]:
        self.log(f"Шаг {number}. {name}")
        return StepStat(number=number, name=name), time.monotonic(), self.llm.stats.model_copy(), len(self.failed_steps)

    def _end(self, mark: tuple[StepStat, float, LLMStats, int], summary: str, failed: bool = False) -> StepStat:
        step, t0, before, failures = mark
        after = self.llm.stats
        step.calls = after.calls - before.calls
        step.cache_hits = after.cache_hits - before.cache_hits
        step.retries = after.retries - before.retries
        step.seconds = round(time.monotonic() - t0, 1)
        step.summary = summary
        new_failures = self.failed_steps[failures:]
        if failed:
            step.status = "failed"
        elif new_failures:
            step.status = "degraded"
        if new_failures:
            step.reason = "; ".join(new_failures)[:500]
        calls = f"вызовов {step.calls}" + (f", из кэша {step.cache_hits}" if step.cache_hits else "")
        mark_ru = {"ok": "", "degraded": " [частично]", "failed": " [не выполнен]"}[step.status]
        self.log(f"    итог шага{mark_ru}: {summary} ({step.seconds} с, {calls})")
        self.steps.append(step)
        return step

    def _step_name(self, number: str) -> str:
        if number == "5" and not self.s.edge:
            return "Набор требований целиком (два прохода, граничные случаи выключены: --no-edge или REQASK_EDGE=0)"
        return STEP_NAMES[number]

    def _skip(self, number: str, name: str, reason: str) -> None:
        """Шаг пропущен: выключен флагом или нечего проверять. Причина идёт в лог и журнал шагов."""
        self.log(f"Шаг {number}. {name}: {reason}")
        self.steps.append(StepStat(number=number, name=name, status="skipped", reason=reason))

    # ---------- весь прогон ----------

    def run(self, doc: Document, agent_version: str) -> RunResult:
        """Шаги 0-8 таблицы 3.1. Шаг 9 (запись отчёта) делает командная строка."""
        started = datetime.now().astimezone()
        t0 = time.monotonic()

        mark = self._begin("0", "Чтение документа")
        self._end(mark, f"строк {doc.n}, формат {doc.fmt}")

        mark = self._begin("3", f"Нарезка требований ({doc.n} строк)")
        requirements = self.segment(doc)
        if not requirements:
            if self.failed_steps:
                self._end(mark, "требований не выделено", failed=True)
                return self._partial_without_requirements(doc, agent_version, started, t0, model_failed=True)
            # Модель ответила, но требований в документе не нашла: это не сбой агента (С-4).
            self._end(mark, "требований не выделено, все строки с текстом отмечены как не требования")
            return self._partial_without_requirements(doc, agent_version, started, t0, model_failed=False)
        lost = f"; идентификаторы документа вне нарезки: {', '.join(self.quality.ids_missing)}" if self.quality.ids_missing else ""
        added = f"; добавлено кодом по идентификаторам: {', '.join(self.quality.ids_added)}" if self.quality.ids_added else ""
        self._end(mark, f"требований {len(requirements)}, пропущено фрагментов {len(self.skipped)}{added}{lost}")
        index = TextIndex(doc)

        mark = self._begin("4", STEP_NAMES["4"])
        req_findings, rewritten = self.review_requirements(doc, requirements, index)
        self._end(
            mark, f"дефектов {len(req_findings)}, без проверки {len(self.unreviewed)}",
            failed=len(self.unreviewed) == len(requirements),
        )

        mark = self._begin("5", self._step_name("5"))
        set_findings = self.review_set(doc, requirements, index)
        edge = f", из них граничных случаев {self.set_pass_counts.get('edge', 0)}" if self.s.edge else ""
        self._end(mark, f"замечаний {len(set_findings)}{edge}, анализов по критериям {len(self.set_analyses)}")

        mark = self._begin("6", STEP_NAMES["6"])
        order = {r.id: i for i, r in enumerate(requirements)}
        req_findings.sort(key=lambda f: (order[f.req_ids[0]], SEVERITY_ORDER[f.severity]))
        for number, finding in enumerate(req_findings, start=1):
            finding.id = make_id("D", number, len(req_findings))
        folded = self.fold(req_findings, requirements)
        set_findings.extend(system for system, _ in folded)
        set_findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.criterion))
        for number, finding in enumerate(set_findings, start=1):
            finding.id = make_id("S", number, len(set_findings))
        for system, items in folded:
            for f in items:
                f.merged_into = system.id
        findings = req_findings + set_findings
        g = self.grounding
        self._end(
            mark,
            f"замечаний {len(findings)}, свёрнуто в системные {g.folded}; сверка цитат на шагах 4 и 5: "
            f"точных {g.exact}, нечётких {g.fuzzy}, не найдено {g.missing}; в карантине {g.quarantine}, "
            f"противоречий только с вопросом {g.question_only}, отброшено без опоры {g.dropped_findings}",
        )
        if self.s.critic:
            mark = self._begin("7", STEP_NAMES["7"])
            self.critique(doc, findings)
            c = self.critic
            if not c.done and self.fatal is None:
                # Вердикт от критика не зависит, но CRITICAL и MAJOR остались без второго взгляда (Н-3).
                self.failed_steps.append("критик: замечания не перепроверены, вердикт посчитан без перепроверки критиком")
            self._end(
                mark,
                f"проверено {c.reviewed} (групп кандидатов на слияние {c.candidate_groups}): оставлено {c.keep}, понижено {c.downgraded}, снято {c.dropped}, "
                f"слито {c.merged}, без решения {c.no_decision}, отклонено кодом {c.rejected}",
                failed=not c.done,
            )
        else:
            self._skip("7", STEP_NAMES["7"], "выключен (--no-critic или REQASK_CRITIC=0)")

        mark = self._begin("8", STEP_NAMES["8"])
        verdict, questions = self.conclude(doc, requirements, findings)
        tail = "" if verdict.questions_by_model else " (запасной путь: из полей замечаний)"
        self._end(mark, f"решение: {verdict.decision}; вопросов {len(questions)}{tail}")

        return self._result(doc, agent_version, started, t0, requirements, findings, rewritten, questions, verdict)

    def _partial_without_requirements(self, doc: Document, agent_version: str, started: datetime, t0: float,
                                      model_failed: bool = True) -> RunResult:
        """Нарезка не дала требований: отчёт из паспорта и причины (К-03, К-10).

        Сбой модели на нарезке: шаги 4-8 не выполнены. Модель ответила, но требований нет:
        шаги 4-8 пропущены, причина в вердикте говорит про документ, а не про агента (С-4).
        """
        for number in ("4", "5", "6", "7", "8"):
            if number == "7" and not self.s.critic:
                self.steps.append(StepStat(number="7", name=STEP_NAMES["7"], status="skipped",
                                           reason="выключен (--no-critic или REQASK_CRITIC=0)"))
            elif model_failed:
                self.steps.append(StepStat(number=number, name=self._step_name(number), status="failed",
                                           reason="нет требований после нарезки"))
            else:
                self.steps.append(StepStat(number=number, name=self._step_name(number), status="skipped",
                                           reason="в документе не найдено требований"))
        if model_failed:
            verdict = self._verdict(
                [], rationale="Решение не принято: требования не выделены, проверка не проводилась.",
                generated_by_model=False, questions_by_model=False,
            )
        else:
            reason = NO_REQUIREMENTS
            if self.uncovered(doc, []):
                reason = "В документе не найдено требований: модель не выделила ни одного требования."
            verdict = Verdict(
                decision=NO_DECISION, ready_for_development=NOT_DEFINED, ready_for_testing=NOT_DEFINED,
                rule=DECISION_RULE, rationale=f"{reason} Проверьте, что передан документ с требованиями.",
                partial_reason=reason, generated_by_model=False, questions_by_model=False,
            )
        verdict.decision, verdict.ready_for_development, verdict.ready_for_testing = NO_DECISION, NOT_DEFINED, NOT_DEFINED
        verdict.partial = True
        return self._result(doc, agent_version, started, t0, [], [], {}, [], verdict)

    def _answered_model(self) -> str:
        """Модель, которая отвечала на деле (В-5). После перехода на запасную видна и основная."""
        answered = getattr(self.llm, "model", None) or self.s.model
        if answered == self.s.model:
            return answered
        return f"{answered} (запасная: основная {self.s.model} не ответила)"

    def _result(self, doc: Document, agent_version: str, started: datetime, t0: float, requirements: list[Requirement],
                findings: list[Finding], rewritten: dict[str, str], questions: list[Question], verdict: Verdict) -> RunResult:
        # Строка с заглушкой засчитывается, только если цитата замечания содержит сам маркер:
        # замечание про другое место той же строки заглушку не закрывает.
        marks = self._placeholder_marks
        cited = {
            e.line for f in findings if f.status not in INACTIVE_STATUSES for e in f.evidence
            if e.status != "missing" and any(m.casefold() in e.quote.casefold() for m in marks.get(e.line, ()))
        }
        self.quality.placeholder_lines_cited = [no for no in self.quality.placeholder_lines if no in cited]
        result = RunResult(
            document_name=doc.name,
            document_format=doc.fmt,
            document_lines=doc.n,
            document_sha256=doc.sha256,
            started_at=started.strftime("%Y-%m-%d %H:%M:%S %z"),
            duration_sec=round(time.monotonic() - t0, 1),
            provider=self.s.provider,
            model=self._answered_model(),
            agent_version=agent_version,
            requirements=requirements,
            findings=findings,
            rewritten=rewritten,
            unreviewed=self.unreviewed,
            failed_steps=self.failed_steps,
            uncovered_lines=self.uncovered(doc, requirements),
            skipped_lines=self.skipped,
            checks=self.checks,
            set_analyses=self.set_analyses,
            questions=questions,
            steps=self.steps,
            json_mode=getattr(self.llm, "json_mode", ""),
            fatal=self.fatal,
            empty_pages=doc.empty_pages,
            removed_headers=doc.removed_headers,
            fallback_pages=doc.fallback_pages,
            verdict=verdict,
            grounding=self.grounding,
            quality=self.quality,
            critic=self.critic,
            llm=self.llm.stats,
        )
        _tidy_result(result)
        return result
