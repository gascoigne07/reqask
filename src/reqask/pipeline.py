"""Конвейер проверки.

Шаги:
1. segment: модель размечает границы требований по номерам строк, цитаты вырезает код.
2. review: проверка каждого требования порциями, с линтер-подсказками и контекстом.
3. set review: два независимых прохода по набору (согласованность, полнота и остальное).
4. grounding: сверка всех цитат с документом, непривязанные замечания отбрасываются.
5. verdict: готовность считает правило, модель пишет обоснование и порядок исправлений.

Сбой одного шага не роняет прогон: порция делится пополам, непроверенное
перечисляется в отчёте. Останавливают прогон только ошибки без шанса на успех
(неверный ключ, нет модели, исчерпанная квота).
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel

from . import prompts
from .config import Settings
from .criteria import REQ_CODES, SET_CODES, SEVERITY_ORDER
from .grounding import TextIndex, clean_quote
from .lint import lint
from .llm import LLMError, LLMFatal
from .loader import Document
from .schemas import (
    SEVERITY_SET,
    BatchReviewOut,
    CriterionCheck,
    Evidence,
    Finding,
    GroundingStats,
    LLMStats,
    QualityStats,
    ReqReviewOut,
    Requirement,
    RunResult,
    SegItem,
    SegmentationOut,
    SetAnalysis,
    SetReviewOut,
    SkippedSpan,
    TopFix,
    Verdict,
    VerdictOut,
)

T = TypeVar("T", bound=BaseModel)

SEG_CHUNK_LINES = 350
FULL_CONTEXT_CHARS = 60_000
CONTEXT_MARGIN_LINES = 40
MAX_EVIDENCE_CHARS = 300
_NO_ID = {"", "-", "null", "none", "нет", "n/a", "отсутствует"}
_REQ_REF_RE = re.compile(r"REQ-?(\d+)", re.IGNORECASE)
# Идентификатор требования в начале строки: «FR-1.», «**Ф-2**», «| NFR-3.1 |». Буквы, дефис, номер.
_DOC_ID_RE = re.compile(r"^[\s>|#*_`-]*\**([A-ZА-ЯЁ][A-Za-zА-Яа-яЁё]{0,7}-\d+(?:\.\d+)*)\**[.:)]?(?=[\s*|`]|$)")
_ADDRESSEE_DEFAULT = "analyst"

# Критерии, без которых нельзя писать тесты: дефект CRITICAL по ним блокирует тестирование.
TESTING_BLOCKERS = {"VERIFIABLE", "UNAMBIGUOUS", "COMPLETE", "SET_CONSISTENT", "SET_COMPLETE", "SET_VALIDATABLE"}
READINESS_RULE = (
    "Разработка: «Нет», если есть хотя бы одно замечание CRITICAL; «Да, с оговорками», если есть MAJOR; иначе «Да». "
    "Тестирование: «Нет», если есть CRITICAL по проверяемости, однозначности, полноте, согласованности "
    "или валидируемости; «Да, с оговорками», если есть другие CRITICAL или MAJOR; иначе «Да»."
)


class JsonLLM(Protocol):
    stats: LLMStats

    def complete_json(self, step: str, system: str, user: str, schema: type[T], kind: str = "") -> T: ...


def make_id(prefix: str, number: int, total: int) -> str:
    """REQ-01, D-01: две цифры, три при числе больше 99 (К-03, О-03)."""
    return f"{prefix}-{number:0{3 if total > 99 else 2}d}"


def _norm_doc_id(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").strip().strip("*`.:)")).upper()


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
        self.grounding = GroundingStats()
        self.quality = QualityStats()
        self.skipped: list[SkippedSpan] = []
        self.checks: dict[str, list[CriterionCheck]] = {}
        self.set_analyses: list[SetAnalysis] = []
        self._req_by_number: dict[int, str] = {}

    # ---------- шаг 1: нарезка ----------

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

    def segment(self, doc: Document) -> list[Requirement]:
        chunks = self._chunks(doc)
        items: list[SegItem] = []
        for index, (start, end) in enumerate(chunks, start=1):
            part = (start, end) if len(chunks) > 1 else None
            user = prompts.segmentation_prompt(doc.numbered(start, end), doc.outline(), part)
            step = f"нарезка {index}/{len(chunks)}"
            try:
                out = self.llm.complete_json(step, prompts.SYSTEM, user, SegmentationOut, kind="segment")
            except LLMFatal:
                raise
            except LLMError as exc:
                self.failed_steps.append(f"{step}: {exc}")
                self.log(f"  {step}: сбой, строки {start}-{end} не нарезаны")
                continue
            items.extend(out.requirements)
            for span in out.skipped:
                a, b = sorted((span.line_start, span.line_end))
                a, b = max(start, a), min(end, b)
                if a <= b:
                    self.skipped.append(SkippedSpan(line_start=a, line_end=b, reason=span.reason))
        requirements = self._build_requirements(doc, items)
        self._check_ids(doc, requirements)
        return requirements

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

    # ---------- шаг 2: проверка каждого требования ----------

    def _context(self, doc: Document, batch: list[Requirement]) -> tuple[str, bool]:
        full = doc.numbered()
        if len(full) <= FULL_CONTEXT_CHARS:
            return full, True
        start = max(1, min(r.line_start for r in batch) - CONTEXT_MARGIN_LINES)
        end = min(doc.n, max(r.line_end for r in batch) + CONTEXT_MARGIN_LINES)
        return doc.numbered(start, end), False

    def _review_batch(self, doc: Document, batch: list[Requirement], label: str, depth: int = 0) -> dict[str, ReqReviewOut]:
        context, is_full = self._context(doc, batch)
        user = prompts.review_prompt(batch, context, is_full)
        try:
            out = self.llm.complete_json(f"проверка {label}", prompts.SYSTEM, user, BatchReviewOut, kind="review")
        except LLMFatal:
            raise
        except LLMError as exc:
            if len(batch) > 1:
                # Порция не прошла (обрезан ответ, битый JSON): делим пополам и пробуем снова.
                self.log(f"  проверка {label}: сбой, делю порцию пополам")
                mid = len(batch) // 2
                result = self._review_batch(doc, batch[:mid], label + "a", depth + 1)
                result.update(self._review_batch(doc, batch[mid:], label + "b", depth + 1))
                return result
            self.failed_steps.append(f"проверка {batch[0].id}: {exc}")
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
                        evidence=[self._ground_in_requirement(defect.evidence, req, index, doc)],
                        problem=defect.problem.strip(),
                        impact=defect.impact.strip(),
                        recommendation=defect.recommendation.strip(),
                        question=question,
                        addressee=(defect.addressee or _ADDRESSEE_DEFAULT) if question else None,
                    )
                )
            self.checks[req.id] = self._reconcile_checks(review, req_findings)
            req.lint_confirmed = self._confirm_lint(req, review)
            findings.extend(req_findings)
            if review.rewritten and review.rewritten.strip() and req_findings:
                rewritten[req.id] = review.rewritten.strip()
        return findings, rewritten

    def _reconcile_checks(self, review: ReqReviewOut, findings: list[Finding]) -> list[CriterionCheck]:
        """Оценки по всем критериям: pass ставит код, fail только при дефекте (К-04)."""
        failed = {f.criterion for f in findings}
        notes: dict[str, CriterionCheck] = {}
        for check in review.checks:
            if check.criterion not in REQ_CODES or check.status not in ("fail", "na", "unknown"):
                self.quality.dropped_checks += 1
                continue
            if check.criterion not in notes:
                notes[check.criterion] = CriterionCheck(
                    criterion=check.criterion, status=check.status, note=" ".join(check.note.split())
                )
        result: list[CriterionCheck] = []
        for code in REQ_CODES:
            check = notes.get(code)
            if code in failed:
                result.append(CriterionCheck(criterion=code, status="fail", note=check.note if check else ""))
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

    # ---------- шаг 3: проверка набора ----------

    def review_set(self, doc: Document, requirements: list[Requirement], index: TextIndex) -> list[Finding]:
        numbered = doc.numbered()
        passes: list[tuple[str, Callable[[list[Finding]], str], tuple[str, ...]]] = [
            ("набор: согласованность", lambda _found: prompts.consistency_prompt(requirements, numbered),
             ("SET_CONSISTENT", "SET_COMPREHENSIBLE")),
            # Второй проход видит, что нашёл первый, и не повторяет это (К-05).
            ("набор: полнота и остальные критерии",
             lambda found: prompts.completeness_prompt(requirements, numbered, found),
             tuple(c for c in SET_CODES if c not in ("SET_CONSISTENT", "SET_COMPREHENSIBLE"))),
        ]
        known = {r.id: r for r in requirements}
        findings: list[Finding] = []
        for step, build, own in passes:
            user = build(findings)
            self.log(f"  {step}")
            try:
                out = self.llm.complete_json(step, prompts.SYSTEM, user, SetReviewOut, kind="set")
            except LLMFatal:
                raise
            except LLMError as exc:
                self.failed_steps.append(f"{step}: {exc}")
                continue
            seen_analyses = {a.criterion for a in self.set_analyses}
            for analysis in out.analyses:
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
                quotes = [q.quote for q in item.evidence]
                evidence = self._ground_in_document(quotes, [known[i] for i in req_ids], index, doc)
                question = (item.question or "").strip() or None
                section = (item.section or "").strip() or None
                # Пробелу цитата не обязательна, но нужны вопрос и место, где сведений нет (К-05).
                anchored = bool(evidence or req_ids) or (kind == "gap" and question and section)
                if not anchored:
                    # Ни подтверждённой цитаты, ни ссылки на требование или раздел: замечание без опоры на текст.
                    self.grounding.dropped_findings += 1
                    continue
                if question is None and (kind == "gap" or item.severity != "MINOR"):
                    self.quality.defects_without_question += 1
                findings.append(
                    Finding(
                        scope="set",
                        kind=kind,
                        criterion=item.criterion,
                        severity=item.severity,
                        title=item.title.strip(),
                        req_ids=req_ids,
                        section=section,
                        evidence=evidence,
                        problem=item.problem.strip(),
                        impact=item.impact.strip(),
                        recommendation=item.recommendation.strip(),
                        question=question,
                        addressee=(item.addressee or _ADDRESSEE_DEFAULT) if question else None,
                    )
                )
        return findings

    # ---------- шаг 4: сверка цитат ----------

    def _norm_req_id(self, raw: str) -> str:
        """REQ-1, REQ-001, req01 приводятся к идентификатору из нарезки."""
        match = _REQ_REF_RE.search(raw or "")
        if match:
            return self._req_by_number.get(int(match.group(1)), (raw or "").strip())
        return (raw or "").strip()

    def _ground_in_requirement(self, quote: str, req: Requirement, index: TextIndex, doc: Document) -> Evidence:
        line = index.find(quote, req.line_start, req.line_end)
        if line is None:
            line = index.find(quote)  # цитата из контекста за пределами требования
        if line is not None:
            self.grounding.exact += 1
            return Evidence(quote=_clip(clean_quote(quote)), line=line, status="exact")
        line = index.fuzzy(quote, req.line_start, req.line_end)
        if line is not None:
            self.grounding.fuzzy += 1
            return Evidence(quote=_clip(doc.line(line).text), line=line, status="fuzzy")
        # Фрагмент не найден. Замечание остаётся привязанным к требованию, цитата берётся из него.
        self.grounding.anchor += 1
        return Evidence(quote=_clip(req.quote), line=req.line_start, status="anchor")

    def _ground_in_document(self, quotes: list[str], reqs: list[Requirement], index: TextIndex, doc: Document) -> list[Evidence]:
        evidence: list[Evidence] = []
        seen: set[tuple[int, str]] = set()
        for quote in quotes:
            if not quote or not quote.strip():
                continue
            found: Evidence | None = None
            line = index.find(quote)
            if line is not None:
                found = Evidence(quote=_clip(clean_quote(quote)), line=line, status="exact")
                self.grounding.exact += 1
            else:
                for req in reqs:
                    line = index.fuzzy(quote, req.line_start, req.line_end)
                    if line is not None:
                        break
                if line is None:
                    line = index.fuzzy(quote)
                if line is not None:
                    found = Evidence(quote=_clip(doc.line(line).text), line=line, status="fuzzy")
                    self.grounding.fuzzy += 1
            if found is None:
                self.grounding.dropped_quotes += 1
                continue
            key = (found.line or 0, found.quote)
            if key not in seen:
                seen.add(key)
                evidence.append(found)
        return evidence

    # ---------- шаг 5: итог ----------

    @staticmethod
    def readiness(findings: list[Finding]) -> tuple[str, str]:
        critical = [f for f in findings if f.severity == "CRITICAL"]
        major = [f for f in findings if f.severity == "MAJOR"]
        dev = "Нет" if critical else ("Да, с оговорками" if major else "Да")
        if any(f.criterion in TESTING_BLOCKERS for f in critical):
            test = "Нет"
        elif critical or major:
            test = "Да, с оговорками"
        else:
            test = "Да"
        return dev, test

    def conclude(self, doc: Document, requirements: list[Requirement], findings: list[Finding]) -> Verdict:
        dev, test = self.readiness(findings)
        if not findings:
            return Verdict(
                ready_for_development=dev, ready_for_testing=test, rule=READINESS_RULE,
                rationale="Агент не нашёл нарушений критериев качества.", generated_by_model=False,
            )
        ranked = sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.id))
        user = prompts.verdict_prompt(doc.name, len(requirements), ranked, f"разработка: {dev}; тестирование: {test}")
        known = {f.id for f in findings}
        try:
            out = self.llm.complete_json("итог", prompts.SYSTEM, user, VerdictOut, kind="verdict")
            fixes = []
            for fix in out.top_fixes:
                ids = [i.strip() for i in fix.finding_ids if i.strip() in known]
                if ids and fix.action.strip():
                    fixes.append(TopFix(finding_ids=ids, action=fix.action.strip()))
            if fixes:
                return Verdict(
                    ready_for_development=dev, ready_for_testing=test, rule=READINESS_RULE,
                    rationale=out.rationale.strip(), top_fixes=fixes[:7],
                )
            self.failed_steps.append("итог: модель не сослалась на существующие замечания")
        except LLMFatal:
            raise
        except LLMError as exc:
            self.failed_steps.append(f"итог: {exc}")
        # Запасной вариант без модели: самые тяжёлые замечания по порядку.
        fixes = [TopFix(finding_ids=[f.id], action=f.recommendation) for f in ranked[:7]]
        return Verdict(
            ready_for_development=dev, ready_for_testing=test, rule=READINESS_RULE,
            rationale="Обоснование от модели не получено, список составлен по критичности замечаний.",
            top_fixes=fixes, generated_by_model=False,
        )

    # ---------- весь прогон ----------

    def run(self, doc: Document, agent_version: str) -> RunResult:
        started = datetime.now().astimezone()
        t0 = time.monotonic()

        self.log(f"1/5 Нарезка требований ({doc.n} строк)")
        requirements = self.segment(doc)
        if not requirements:
            raise LLMError(
                "Агент не выделил ни одного требования. Проверьте, что документ содержит требования, "
                "и посмотрите сообщения об ошибках выше."
            )
        self.log(f"    выделено требований: {len(requirements)}")
        if self.quality.ids_missing:
            self.log(f"    идентификаторы документа вне нарезки: {', '.join(self.quality.ids_missing)}")
        index = TextIndex(doc)

        self.log("2/5 Проверка каждого требования")
        req_findings, rewritten = self.review_requirements(doc, requirements, index)

        self.log("3/5 Проверка набора требований")
        set_findings = self.review_set(doc, requirements, index)

        self.log("4/5 Сверка цитат с документом")
        order = {r.id: i for i, r in enumerate(requirements)}
        req_findings.sort(key=lambda f: (order[f.req_ids[0]], SEVERITY_ORDER[f.severity]))
        for number, finding in enumerate(req_findings, start=1):
            finding.id = make_id("D", number, len(req_findings))
        set_findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.criterion))
        for number, finding in enumerate(set_findings, start=1):
            finding.id = make_id("S", number, len(set_findings))
        findings = req_findings + set_findings
        g = self.grounding
        self.log(
            f"    цитат точных: {g.exact}, восстановлено: {g.fuzzy}, привязано к требованию: {g.anchor}, "
            f"отброшено цитат: {g.dropped_quotes}, отброшено замечаний: {g.dropped_findings}"
        )

        self.log("5/5 Итог")
        verdict = self.conclude(doc, requirements, findings)

        return RunResult(
            document_name=doc.name,
            document_format=doc.fmt,
            document_lines=doc.n,
            document_sha256=doc.sha256,
            started_at=started.strftime("%Y-%m-%d %H:%M:%S %z"),
            duration_sec=round(time.monotonic() - t0, 1),
            provider=self.s.provider,
            model=self.s.model,
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
            verdict=verdict,
            grounding=self.grounding,
            quality=self.quality,
            llm=self.llm.stats,
        )
