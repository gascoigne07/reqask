"""Сборка отчёта в Markdown из результата прогона. Модель здесь не участвует."""

from __future__ import annotations

from collections import Counter

from .criteria import ADDRESSEES, ALL_BY_CODE, REQ_CRITERIA, SET_CRITERIA, SEVERITIES, SEVERITY_RU
from .schemas import Evidence, Finding, Requirement, RunResult

OK, BAD, NA, UNKNOWN, SKIP = "✓", "✗", "·", "?", "нет"
MARKS = {"pass": OK, "fail": BAD, "na": NA, "unknown": UNKNOWN}
SKIP_REASONS_RU = {
    "heading": "заголовки", "service": "служебные сведения", "history": "история изменений",
    "checklist": "чек-листы", "template": "шаблоны, шапки таблиц и пустые поля",
    "intro": "вводный и поясняющий текст", "other": "прочее",
}
SET_STATUS_RU = {"ok": "выполнен", "partial": "частично", "fail": "нарушен", "unknown": "нельзя оценить"}


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _code(text: str) -> str:
    """Инлайн-код для дословной цитаты: разметка внутри не срабатывает."""
    text = " ".join(text.split())
    fence = "`"
    while fence in text:
        fence += "`"
    pad = " " if text.startswith("`") or text.endswith("`") or len(fence) > 1 else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _fenced(text: str) -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}text\n{text}\n{fence}"


def _lines(start: int, end: int) -> str:
    return f"строка {start}" if start == end else f"строки {start}-{end}"


def _where(req: Requirement) -> str:
    place = _lines(req.line_start, req.line_end)
    return f"{place}, страница {req.page}" if req.page else place


def _severity(code: str) -> str:
    return f"{code} ({SEVERITY_RU[code]})"


def _criterion(code: str) -> str:
    criterion = ALL_BY_CODE.get(code)
    return criterion.name if criterion else code


def _evidence(item: Evidence) -> str:
    line = f"строка {item.line}: " if item.line else ""
    note = {
        "exact": "",
        "fuzzy": " (цитата модели неточная, приведена строка документа)",
        "anchor": " (фрагмент не найден дословно, приведено требование)",
    }[item.status]
    return f"{line}{_code(item.quote)}{note}"


def _finding_details(f: Finding) -> list[str]:
    rows = [f"Дефект: {f.problem}"]
    if f.impact:
        rows.append(f"Последствие: {f.impact}")
    rows.append(f"Как исправить: {f.recommendation}")
    if f.question:
        rows.append(f"Вопрос {ADDRESSEES.get(f.addressee or '', 'автору')}: {f.question}")
    return rows


def _ranges(spans) -> str:
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def _req_label(req: Requirement) -> str:
    return f"{req.id} ({req.source_id})" if req.source_id else req.id


def render(result: RunResult) -> str:
    reqs = result.requirements
    by_id = {r.id: r for r in reqs}
    req_findings = [f for f in result.findings if f.scope == "requirement"]
    set_findings = [f for f in result.findings if f.scope == "set"]
    by_req: dict[str, list[Finding]] = {}
    for finding in req_findings:
        by_req.setdefault(finding.req_ids[0], []).append(finding)
    severity_count = Counter(f.severity for f in result.findings)
    out: list[str] = []
    add = out.append

    add(f"# Отчёт о проверке требований: {result.document_name}\n")
    add("Отчёт сформирован агентом reqask автоматически. Все цитаты сверены с текстом документа.\n")

    # ---------- 1. паспорт ----------
    llm, g = result.llm, result.grounding
    add("## 1. Паспорт прогона\n")
    add("| Параметр | Значение |")
    add("| :--- | :--- |")
    add(f"| Документ | {_cell(result.document_name)} ({result.document_format}, строк: {result.document_lines}) |")
    add(f"| Контрольная сумма документа | sha256 `{result.document_sha256[:16]}` |")
    add(f"| Дата и время прогона | {result.started_at} |")
    add(f"| Длительность | {result.duration_sec} с |")
    add(f"| Модель | {_cell(result.model)} (провайдер: {result.provider}) |")
    add(f"| Версия агента | {_cell(result.agent_version)} |")
    add("| Критерии | ISO/IEC/IEEE 29148:2018 п. 5.2.5 и 5.2.6; IEEE Std 830-1998 п. 4.3 |")
    add(
        f"| Обращения к модели | {llm.calls} (из кэша: {llm.cache_hits}, повторов при сбоях: {llm.retries}, "
        f"исправлений JSON: {llm.repairs}) |"
    )
    add(f"| Токены | вход: {llm.prompt_tokens}, выход: {llm.completion_tokens} |")
    add(
        f"| Сверка цитат | точных: {g.exact}, восстановлено по близкому совпадению: {g.fuzzy}, "
        f"привязано к требованию целиком: {g.anchor}, отброшено цитат: {g.dropped_quotes}, "
        f"отброшено замечаний без опоры на текст: {g.dropped_findings} |"
    )
    add("")
    if result.failed_steps or result.unreviewed:
        add("**Неполнота прогона.** Часть шагов не выполнена, отчёт по ним неполон:\n")
        for step in result.failed_steps:
            add(f"- {step}")
        if result.unreviewed:
            add(f"- требования без проверки: {', '.join(result.unreviewed)}")
        add("")

    # ---------- 2. нарезка ----------
    add("## 2. Как агент нарезал требования\n")
    with_id = sum(1 for r in reqs if r.source_id)
    add(
        f"Выделено требований: **{len(reqs)}**. Идентификатор в документе есть у {with_id} из них, "
        f"остальным идентификатор присвоил агент. Границы требований заданы номерами строк документа, "
        f"цитаты в разделе 3 вырезаны из документа по этим границам без участия модели.\n"
    )
    add("| ID в отчёте | ID в документе | Раздел | Где | Краткая формулировка |")
    add("| :--- | :--- | :--- | :--- | :--- |")
    for r in reqs:
        add(f"| {r.id} | {_cell(r.source_id or 'нет')} | {_cell(r.section or 'не указан')} | {_where(r)} | {_cell(r.summary)} |")
    add("")
    q = result.quality
    if q.content_lines:
        add(
            f"Строк с текстом: {q.content_lines}. Вошли в требования: {q.in_requirements}. "
            f"Отмечены как не требования: {q.skipped_by_model}.\n"
        )
    if result.skipped_lines:
        by_reason: dict[str, list[tuple[int, int]]] = {}
        for span in result.skipped_lines:
            by_reason.setdefault(span.reason, []).append((span.line_start, span.line_end))
        add("Что агент не отнёс к требованиям (учтено при проверке набора в разделе 4):\n")
        for reason, spans in by_reason.items():
            add(f"- {SKIP_REASONS_RU.get(reason, reason)}: строки {_ranges(sorted(spans))}")
        add("")
    if result.uncovered_lines:
        add(
            f"Строки с текстом, которые не попали ни в требования, ни в список выше: "
            f"{_ranges(result.uncovered_lines)}. Их стоит проверить глазами.\n"
        )
    if q.ids_in_document:
        if q.ids_missing:
            add(
                f"Идентификаторов требований в документе: {q.ids_in_document}. Не найдены в нарезке: "
                f"{', '.join(q.ids_missing)}.\n"
            )
        else:
            add(f"Все {q.ids_in_document} идентификаторов требований из документа есть в нарезке.\n")

    # ---------- 3. каждое требование ----------
    add("## 3. Проверка каждого требования\n")
    add("### 3.1. Матрица соответствия критериям\n")
    add(
        f"Обозначения: {OK} нарушений не найдено, {BAD} есть замечание, {NA} не применим, "
        f"{UNKNOWN} нельзя оценить по тексту, «{SKIP}» требование не проверено.\n"
    )
    add("| Требование | " + " | ".join(c.short for c in REQ_CRITERIA) + " | Замечаний |")
    add("| :--- | " + " | ".join(":---:" for _ in REQ_CRITERIA) + " | :---: |")
    for r in reqs:
        violated = {f.criterion for f in by_req.get(r.id, [])}
        status = {c.criterion: c.status for c in result.checks.get(r.id, [])}
        if r.id in result.unreviewed:
            marks = [SKIP] * len(REQ_CRITERIA)
        else:
            marks = [BAD if c.code in violated else MARKS[status.get(c.code, "pass")] for c in REQ_CRITERIA]
        add(f"| {_cell(_req_label(r))} | " + " | ".join(marks) + f" | {len(by_req.get(r.id, []))} |")
    add("")
    add("Расшифровка столбцов: " + "; ".join(f"{c.short} {c.name.lower()}" for c in REQ_CRITERIA) + ".\n")

    add("### 3.2. Разбор по требованиям\n")
    for r in reqs:
        add(f"#### {_req_label(r)}\n")
        add(f"Раздел: {r.section or 'не указан'}. Место: {_where(r)}. Суть: {r.summary}\n")
        add(_fenced(r.quote) + "\n")
        findings = by_req.get(r.id, [])
        if r.id in result.unreviewed:
            add("Требование не проверено: модель не вернула результат по нему.\n")
            continue
        open_checks = [c for c in result.checks.get(r.id, []) if c.status in ("na", "unknown") and c.note]
        for check in open_checks:
            mark = "не применим" if check.status == "na" else "нельзя оценить"
            add(f"- {_criterion(check.criterion)}: {mark}. {check.note}")
        if open_checks:
            add("")
        if not findings:
            add("Замечаний нет: нарушений критериев не найдено.\n")
            continue
        violated = [c.name for c in REQ_CRITERIA if c.code in {f.criterion for f in findings}]
        add(f"Нарушены критерии: {', '.join(violated)}.\n")
        for f in findings:
            add(f"- **{f.id} · {_severity(f.severity)} · {_criterion(f.criterion)}**")
            for item in f.evidence:
                add(f"  - Цитата, {_evidence(item)}")
            for row in _finding_details(f):
                add(f"  - {row}")
        add("")
        if r.id in result.rewritten:
            add("Предлагаемая формулировка:\n")
            add("> " + result.rewritten[r.id].replace("\n", "\n> ") + "\n")

    # ---------- 4. набор ----------
    add("## 4. Проверка набора требований\n")
    set_count = Counter(f.criterion for f in set_findings)
    analyses = {a.criterion: a for a in result.set_analyses}
    add("| Критерий | Источник | Итог | Замечаний | Что проверено |")
    add("| :--- | :--- | :---: | :---: | :--- |")
    for c in SET_CRITERIA:
        count = set_count.get(c.code, 0)
        a = analyses.get(c.code)
        verdict = SET_STATUS_RU[a.status] if a else (BAD if count else OK)
        add(f"| {c.name} | {c.source} | {verdict} | {count} | {_cell(a.analysis if a else 'анализ не получен')} |")
    add("")
    if not set_findings:
        add("Замечаний к набору нет.\n")
    for f in set_findings:
        add(f"#### {f.id}. {f.title}\n")
        add(f"- Критерий: {_criterion(f.criterion)}. Критичность: {_severity(f.severity)}.")
        if f.req_ids:
            labels = [f"{_req_label(by_id[i])} ({_lines(by_id[i].line_start, by_id[i].line_end)})" for i in f.req_ids]
            add(f"- Затронутые требования: {', '.join(labels)}.")
        if f.section:
            add(f"- Раздел: {f.section}.")
        for item in f.evidence:
            add(f"- Цитата, {_evidence(item)}")
        for row in _finding_details(f):
            add(f"- {row}")
        add("")

    # ---------- 5. сводка ----------
    add("## 5. Сводка\n")
    with_defects = sum(1 for r in reqs if by_req.get(r.id))
    add("| Показатель | Значение |")
    add("| :--- | :---: |")
    add(f"| Требований всего | {len(reqs)} |")
    add(f"| Требований с замечаниями | {with_defects} |")
    add(f"| Требований без замечаний | {len(reqs) - with_defects - len(result.unreviewed)} |")
    if result.unreviewed:
        add(f"| Требований без проверки | {len(result.unreviewed)} |")
    add(f"| Нарушений всего | {len(result.findings)} |")
    add(f"| из них в отдельных требованиях | {len(req_findings)} |")
    add(f"| из них в наборе в целом | {len(set_findings)} |")
    for severity in SEVERITIES:
        add(f"| {_severity(severity)} | {severity_count.get(severity, 0)} |")
    add("")

    criterion_count = Counter(f.criterion for f in result.findings)
    if criterion_count:
        add("Нарушения по критериям:\n")
        add("| Критерий | Всего | CRITICAL | MAJOR | MINOR |")
        add("| :--- | :---: | :---: | :---: | :---: |")
        for code, total in criterion_count.most_common():
            per = Counter(f.severity for f in result.findings if f.criterion == code)
            add(f"| {_criterion(code)} | {total} | {per.get('CRITICAL', 0)} | {per.get('MAJOR', 0)} | {per.get('MINOR', 0)} |")
        add("")

    critical = [f for f in result.findings if f.severity == "CRITICAL"]
    add("### Критичные дефекты\n")
    if not critical:
        add("Критичных дефектов не найдено.\n")
    else:
        add("| ID | Где | Критерий | Суть |")
        add("| :--- | :--- | :--- | :--- |")
        for f in critical:
            if f.req_ids:
                where = ", ".join(_req_label(by_id[i]) for i in f.req_ids)
            else:
                where = "набор в целом"
            lines = sorted({e.line for e in f.evidence if e.line})
            if lines:
                where += " (" + ("строка " if len(lines) == 1 else "строки ") + ", ".join(map(str, lines)) + ")"
            add(f"| {f.id} | {_cell(where)} | {_criterion(f.criterion)} | {_cell(f.title or f.problem)} |")
        add("")

    # ---------- 6. итог ----------
    v = result.verdict
    add("## 6. Итог\n")
    add(f"- Можно ли начинать разработку: **{v.ready_for_development}**")
    add(f"- Можно ли начинать тестирование: **{v.ready_for_testing}**\n")
    add(f"Правило расчёта готовности. {v.rule}\n")
    add(v.rationale + "\n")
    if v.top_fixes:
        add("### Что исправить в первую очередь\n")
        for number, fix in enumerate(v.top_fixes, start=1):
            add(f"{number}. {fix.action} (замечания: {', '.join(fix.finding_ids)})")
        add("")

    # ---------- приложение ----------
    add("## Приложение. Критерии проверки\n")
    add("Для отдельного требования:\n")
    for c in REQ_CRITERIA:
        add(f"- **{c.name}** ({c.source}). {c.question}")
    add("\nДля набора требований:\n")
    for c in SET_CRITERIA:
        add(f"- **{c.name}** ({c.source}). {c.question}")
    add("\nУровни критичности: CRITICAL блокирует разработку или тестирование, MAJOR несёт риск "
        "разного понимания и переделок, MINOR касается оформления.")
    add("")

    return "\n".join(out)
