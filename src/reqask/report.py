"""Сборка отчёта в Markdown из результата прогона. Модель здесь не участвует.

Порядок разделов (ТЗ, раздел 9): первый экран с вердиктом и главными вопросами,
1 паспорт, 2 нарезка, 3 каждое требование, 4 набор целиком, 5 сводка, 6 вердикт,
7 вопросы, приложения А (критерии) и Б (снятые и неподтверждённые замечания).
Рядом пишется report.questions.md: только вопросы, в виде для письма автору ТЗ.
"""

from __future__ import annotations

from collections import Counter

from .criteria import (
    ADDRESSEES,
    ALL_BY_CODE,
    PASS_NOTE,
    REQ_CRITERIA,
    SET_CRITERIA,
    SET_SECTIONS,
    SEVERITIES,
    SEVERITY_RU,
    SEVERITY_RULES,
)
from .schemas import INACTIVE_STATUSES, Evidence, Finding, Question, Requirement, RunResult

ICONS = {"pass": "✅", "fail": "❌", "na": "➖", "unknown": "❔"}
STATUS_RU = {"pass": PASS_NOTE, "fail": "нарушен", "na": "не применим", "unknown": "нельзя оценить по тексту"}
SKIP_REASONS_RU = {
    "heading": "заголовки", "service": "служебные сведения", "history": "история изменений",
    "checklist": "чек-листы", "template": "шаблоны, шапки таблиц и пустые поля",
    "intro": "вводный и поясняющий текст", "other": "прочее",
}
SET_STATUS_RU = {"ok": "выполнен", "partial": "частично", "fail": "нарушен", "unknown": "нельзя оценить"}
KIND_RU = {"contradiction": "противоречие", "gap": "пробел", "other": "прочее", "defect": "дефект"}
FINDING_STATUS_RU = {
    "dropped": "снято критиком", "merged": "слито с другим замечанием", "downgraded": "уровень понижен критиком", "quarantine": "цитата не найдена в документе",
    "question_only": "противоречие подтверждено одной цитатой, оставлен вопрос",
}
STEP_STATUS_RU = {"ok": "выполнен", "degraded": "частично", "failed": "не выполнен", "skipped": "не включён"}
# Подраздел отчёта для блокеров по виду (раздел 5), как критичные дефекты описывает README оргов.
BLOCKER_GROUPS = (
    ("Противоречия", lambda f: f.kind == "contradiction" or f.criterion in ("CONSISTENT", "SET_CONSISTENT")),
    ("Непроверяемые и неоднозначные формулировки", lambda f: f.criterion in ("VERIFIABLE", "UNAMBIGUOUS")),
    ("Неполные формулировки и пробелы", lambda f: f.kind == "gap" or f.criterion in ("COMPLETE", "SET_COMPLETE")),
    ("Прочие", lambda f: True),
)
# Подраздел раздела 4 для системного замечания, свёрнутого из критерия отдельного требования.
SYSTEM_GROUP = {"CONSISTENT": "consistency", "FEASIBLE": "feasibility", "CORRECT": "feasibility", "APPROPRIATE": "feasibility"}
FIRST_SCREEN_BLOCKERS = 5
FIRST_SCREEN_QUESTIONS = 5
REQ_TABLE_QUOTE = 80


# ---------- мелкие помощники ----------


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _one_line(text: str, limit: int | None = None) -> str:
    text = " ".join(text.split())
    if limit and len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def _no_dot(text: str) -> str:
    """Убирает точку в конце, чтобы после склейки фраз не было двух точек подряд."""
    text = text.rstrip()
    return text if text.endswith("...") else text.rstrip(".")


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


def _anchor(ident: str) -> str:
    return ident.lower()


def _link(ident: str) -> str:
    return f"[{ident}](#{_anchor(ident)})"


def _links(ids: list[str]) -> str:
    return ", ".join(_link(i) for i in ids)


def _target(ident: str) -> str:
    return f'<a id="{_anchor(ident)}"></a>'


def _criterion(code: str) -> str:
    criterion = ALL_BY_CODE.get(code)
    return criterion.name if criterion else code


def _addressee(code: str | None) -> str:
    return ADDRESSEES.get(code or "", "автору")


def _evidence(item: Evidence) -> str:
    line = f" (строка {item.line})" if item.line else ""
    note = {
        "exact": "",
        "fuzzy": ", восстановлена по близкому совпадению",
        "missing": ", не найдена в документе",
    }.get(item.status, "")
    return f"{_code(item.quote)}{line}{note}"


def _active(f: Finding) -> bool:
    return f.status not in INACTIVE_STATUSES


def _ranges(spans) -> str:
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def _blocks_label(q: Question, by_id: dict[str, Finding]) -> str:
    severities = {by_id[i].severity for i in q.finding_ids if i in by_id}
    if "CRITICAL" in severities:
        return "блокирует разработку"
    if "MAJOR" in severities:
        return "нужен до начала спринта"
    return "не блокирует"


def _where_finding(f: Finding, reqs: dict[str, Requirement]) -> str:
    if f.req_ids:
        return ", ".join(_link(i) for i in f.req_ids if i in reqs)
    if f.section:
        return f"раздел «{f.section}»"
    return "набор в целом"


def _review_only_question(q: Question, by_id: dict[str, Finding]) -> bool:
    """Вопрос по противоречию, подтверждённому одной цитатой: печатается отдельной группой (О-09)."""
    linked = [by_id[i] for i in q.finding_ids if i in by_id]
    return bool(linked) and all(f.status == "question_only" for f in linked)


# ---------- отчёт ----------


PARTIAL_VERDICT = ("Решение принято по неполным данным: часть шагов с моделью не выполнена, "
                   "после полной проверки оно может стать строже.")

class _Report:
    def __init__(self, result: RunResult):
        self.r = result
        self.reqs = {r.id: r for r in result.requirements}
        self.by_id = {f.id: f for f in result.findings}
        self.active = [f for f in result.findings if _active(f)]
        self.inactive = [f for f in result.findings if not _active(f)]
        # Что критик слил в каждое замечание: цель показывает список, чтобы слияние можно было проверить.
        self.absorbed: dict[str, list[str]] = {}
        for f in result.findings:
            if f.status == "merged" and f.merged_into and f.critic_reason:
                self.absorbed.setdefault(f.merged_into, []).append(f.id)
        self.req_findings: dict[str, list[Finding]] = {}
        for f in result.findings:
            if f.scope == "requirement" and f.req_ids:
                self.req_findings.setdefault(f.req_ids[0], []).append(f)
        self.questions = {q.id: q for q in result.questions}
        self.out: list[str] = []

    def add(self, line: str = "") -> None:
        self.out.append(line)

    # ---------- первый экран ----------

    def first_screen(self) -> None:
        r, v = self.r, self.r.verdict
        self.add(f"# Отчёт о проверке требований: {r.document_name}\n")
        self.add(
            f"Отчёт сформирован агентом reqask автоматически по ISO/IEC/IEEE 29148:2018 и IEEE 830. "
            f"Модель: {r.model}. Дата: {r.started_at}.\n"
        )
        self.incomplete_block()
        self.add(f"**Вердикт: {v.decision}.**")
        if v.partial:
            self.add(PARTIAL_VERDICT)
        if v.blockers and not v.critic_done:
            self.add("Критичные замечания не перепроверены отдельным шагом.")
        self.add("")
        self.add(f"- Готовность к разработке: **{v.ready_for_development}**")
        self.add(f"- Готовность к тестированию: **{v.ready_for_testing}**")
        sev = Counter(f.severity for f in self.active)
        with_defects = sum(1 for rid in self.reqs if any(_active(f) for f in self.req_findings.get(rid, [])))
        self.add(
            f"- Требований: {len(self.reqs)}, с дефектами: {with_defects}. "
            f"Замечаний: CRITICAL {sev.get('CRITICAL', 0)}, MAJOR {sev.get('MAJOR', 0)}, MINOR {sev.get('MINOR', 0)}. "
            f"Вопросов автору: {len(r.questions)}."
        )
        lost = [f for f in self.inactive if f.severity == "CRITICAL" and f.status in ("quarantine", "question_only")]
        if lost:
            self.add(f"- {len(lost)} критичных замечаний не подтверждены цитатой, см. [приложение Б](#appendix-b).")
        self.add("")
        if v.blockers:
            self.add("**Блокеры:**\n")
            for fid in v.blockers[:FIRST_SCREEN_BLOCKERS]:
                f = self.by_id[fid]
                self.add(f"- {_link(fid)} · {_where_finding(f, self.reqs)} · {_one_line(f.title or f.problem, 140)}")
            rest = len(v.blockers) - FIRST_SCREEN_BLOCKERS
            if rest > 0:
                self.add(f"- и ещё {rest}, полный список в [разделе 5](#summary)")
            self.add("")
        if r.questions:
            self.add("**Главные вопросы автору ТЗ:**\n")
            for q in r.questions[:FIRST_SCREEN_QUESTIONS]:
                self.add(f"- {_link(q.id)} · {_addressee(q.addressee)}: {_one_line(q.text, 220)}")
            self.add(f"\nВсе вопросы в [разделе 7](#questions), для отправки автору: файл `report.questions.md`.\n")

    def incomplete_block(self) -> None:
        r = self.r
        failed = [s for s in r.steps if s.status in ("failed", "degraded")]
        if not (r.failed_steps or r.unreviewed or failed or r.fatal):
            return
        self.add("> **Отчёт неполный.** Часть работы не выполнена:")
        if r.fatal:
            self.add(f"> - причина: {_one_line(r.fatal, 400)}")
        for s in failed:
            self.add(f"> - шаг {s.number} «{s.name}»: {STEP_STATUS_RU[s.status]}")
        for item in r.failed_steps:
            self.add(f"> - {_one_line(item, 300)}")
        if r.unreviewed:
            self.add(f"> - требования без проверки: {', '.join(r.unreviewed)}")
        self.add("")

    # ---------- 1. паспорт ----------

    def passport(self) -> None:
        r, llm, g, q = self.r, self.r.llm, self.r.grounding, self.r.quality
        self.add("## 1. Паспорт прогона\n")
        self.add("| Прогон | Значение |")
        self.add("| :--- | :--- |")
        self.add(f"| Документ | {_cell(r.document_name)}, формат {r.document_format}, строк {r.document_lines} |")
        if r.document_format == "pdf":
            empty = ", ".join(map(str, r.empty_pages)) if r.empty_pages else "нет"
            self.add(f"| Чтение PDF | страницы без текста: {empty}; удалено строк колонтитулов: {r.removed_headers} |")
        self.add(f"| SHA-256 документа | `{r.document_sha256}` |")
        self.add(f"| Дата и время | {r.started_at} |")
        self.add(f"| Длительность | {r.duration_sec} с |")
        self.add(f"| Модель | {_cell(r.model)} (провайдер: {r.provider}) |")
        self.add(f"| Версия агента | {_cell(r.agent_version)} |")
        mode = "только из кэша" if llm.calls and llm.cache_hits == llm.calls else (
            "живой прогон" if not llm.cache_hits else "живой прогон, часть ответов из кэша")
        self.add(f"| Режим | {mode}; формат ответа JSON: {r.json_mode or 'не известен'} |")
        self.add("| Стандарты | ISO/IEC/IEEE 29148:2018 п. 5.2.5 и 5.2.6; IEEE Std 830-1998 п. 4.3 |")
        self.add(f"| Обращений к модели | {llm.calls}, из кэша {llm.cache_hits}, повторов при сбоях {llm.retries} |")
        self.add(f"| Токены | вход {llm.prompt_tokens}, выход {llm.completion_tokens}, всего {llm.total_tokens} |")
        if llm.notes:
            self.add(f"| Отказы провайдера | {_cell('; '.join(llm.notes))} |")
        self.add("")

        self.add("| Самопроверка прогона | Значение |")
        self.add("| :--- | :--- |")
        if q.content_lines:
            share = round(100 * q.in_requirements / q.content_lines)
            self.add(
                f"| Покрытие нарезкой | строк с текстом {q.content_lines}, в требованиях {q.in_requirements} ({share}%), "
                f"отмечены как не требования {q.skipped_by_model}, не разобраны {sum(b - a + 1 for a, b in r.uncovered_lines)} |"
            )
        if q.ids_in_document:
            lost = f", потеряны: {', '.join(q.ids_missing)}" if q.ids_missing else ", потерянных нет"
            self.add(f"| Идентификаторы | в документе {q.ids_in_document}, в нарезке {q.ids_in_document - len(q.ids_missing)}{lost} |")
        quarantine = sum(1 for f in self.inactive if f.status == "quarantine")
        self.add(
            f"| Цитаты | точных {g.exact}, нечётких {g.fuzzy}, не найдено {g.missing}; "
            f"замечаний в карантине {quarantine}, противоречий только с вопросом {g.question_only}, "
            f"свёрнуто в системные {g.folded}, отброшено без опоры на текст {g.dropped_findings} |"
        )
        c = r.critic
        if c.done:
            self.add(
                f"| Критик | проверено CRITICAL и MAJOR {c.reviewed}: оставлено {c.keep}, понижено {c.downgraded}, "
                f"снято {c.dropped}, слито {c.merged}, без решения {c.no_decision}, решений отклонено кодом {c.rejected} |"
            )
        else:
            step = next((x for x in r.steps if x.number == "7"), None)
            why = "не выполнен" if step and step.status == "failed" else "не включён"
            self.add(f"| Критик | {why} |")
        self.add(
            f"| Ответы модели | исправлений JSON {llm.repairs}, отброшено дефектов проверкой {q.dropped_defects}, "
            f"оценок {q.dropped_checks}; оценок не вернула модель {q.checks_missing}, "
            f"pass заменён на fail по дефекту {q.checks_pass_overridden}; "
            f"CRITICAL и MAJOR без вопроса {q.defects_without_question} |"
        )
        self.add(
            f"| Сводные вопросы | {'от модели' if r.verdict.questions_by_model else 'запасной путь из полей замечаний'}; "
            f"отброшено проверкой {q.questions_dropped}, слито дублей {q.questions_merged}, "
            f"добавлено кодом для CRITICAL {q.questions_added} |"
        )
        if r.steps:
            st = Counter(s.status for s in r.steps)
            self.add(
                f"| Шаги | выполнено {st.get('ok', 0)}, частично {st.get('degraded', 0)}, "
                f"не выполнено {st.get('failed', 0)}, не включено {st.get('skipped', 0)} |"
            )
        hints = sum(len(x.lint_hints) for x in r.requirements)
        confirmed = sum(len(x.lint_confirmed) for x in r.requirements)
        if hints:
            self.add(f"| Правила | подсказок словаря {hints}, подтверждено моделью {confirmed} ({round(100 * confirmed / hints)}%) |")
        self.add("")

        if r.steps:
            self.add("<details><summary>Журнал шагов</summary>\n")
            self.add("| Шаг | Что | Итог | Вызовов | Секунд | Результат |")
            self.add("| :-- | :--- | :--- | :-- | :-- | :--- |")
            for s in r.steps:
                result = s.summary or s.reason
                if s.reason and s.summary:
                    result += f". Сбои: {s.reason}"
                self.add(f"| {s.number} | {s.name} | {STEP_STATUS_RU[s.status]} | {s.calls} | {s.seconds} | {_cell(result)} |")
            self.add("\n</details>\n")

    # ---------- 2. нарезка ----------

    def segmentation(self) -> None:
        r = self.r
        self.add("## 2. Нарезка на требования\n")
        with_id = sum(1 for x in r.requirements if x.source_id)
        self.add(
            f"Выделено требований: **{len(r.requirements)}**, у {with_id} есть идентификатор в документе. "
            "Границы заданы номерами строк, текст требований вырезан из документа кодом.\n"
        )
        self.add("| ID | ID в документе | Раздел | Строки | Суть | Начало текста |")
        self.add("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for x in r.requirements:
            lines = f"{x.line_start}-{x.line_end}" if x.line_end != x.line_start else str(x.line_start)
            if x.page:
                lines += f", стр. {x.page}"
            self.add(
                f"| {_link(x.id)} | {_cell(x.source_id or 'без номера')} | {_cell(x.section or 'не указан')} | {lines} "
                f"| {_cell(x.summary)} | {_code(_one_line(x.quote, REQ_TABLE_QUOTE)).replace('|', chr(92) + '|')} |"
            )
        self.add("")
        if r.skipped_lines:
            by_reason: dict[str, list[tuple[int, int]]] = {}
            for span in r.skipped_lines:
                by_reason.setdefault(span.reason, []).append((span.line_start, span.line_end))
            self.add("Не вошли в требования (эти строки видит проверка набора в разделе 4):\n")
            for reason, spans in by_reason.items():
                self.add(f"- {SKIP_REASONS_RU.get(reason, reason)}: строки {_ranges(sorted(spans))}")
            self.add("")
        if r.uncovered_lines:
            self.add(
                f"Строки с текстом, которые не попали ни в требования, ни в список выше: "
                f"{_ranges(r.uncovered_lines)}. Их стоит проверить глазами.\n"
            )
        q = r.quality
        if q.ids_missing:
            self.add(f"Идентификаторы из документа, которых нет в нарезке: {', '.join(q.ids_missing)}.\n")

    # ---------- 3. каждое требование ----------

    def requirements(self) -> None:
        self.add("## 3. Проверка каждого требования\n")
        self.add(
            f"Значки: {ICONS['pass']} выполнен, {ICONS['fail']} нарушен, {ICONS['na']} не применим, "
            f"{ICONS['unknown']} нельзя оценить по тексту. Шесть основных критериев показаны всегда, "
            "уместность уровня, атомарность и корректность только при нарушении.\n"
        )
        for x in self.r.requirements:
            self.requirement_block(x)

    def requirement_block(self, x: Requirement) -> None:
        r = self.r
        head = f"{x.id} · ID в документе: {x.source_id or 'без номера'} · раздел {x.section or 'не указан'} · {_lines(x.line_start, x.line_end)}"
        if x.page:
            head += f" · страница {x.page}"
        self.add(_target(x.id))
        self.add(f"### {head}\n")
        if "\n" in x.quote.strip():
            self.add(_fenced(x.quote) + "\n")
        else:
            self.add(f"> {x.quote.strip()}\n")
        if x.id in r.unreviewed:
            self.add("Требование не проверено: модель не вернула по нему результат.\n")
            return
        findings = self.req_findings.get(x.id, [])
        shown = [f for f in findings if _active(f)]
        checks = {c.criterion: c for c in r.checks.get(x.id, [])}
        visible = [c for c in REQ_CRITERIA if c.group == "core" or checks.get(c.code) and checks[c.code].status == "fail"]
        if not shown and all(checks.get(c.code) is None or checks[c.code].status == "pass" for c in REQ_CRITERIA):
            marks = " ".join(f"{ICONS['pass']} {c.short}" for c in visible)
            self.add(f"Замечаний нет: {marks}\n")
            return
        self.add("| Критерий | Оценка | Пояснение |")
        self.add("| :--- | :---: | :--- |")
        for c in visible:
            check = checks.get(c.code)
            status = check.status if check else "pass"
            note = (check.note if check and check.note else STATUS_RU[status]) if status != "pass" else PASS_NOTE
            self.add(f"| {c.name} | {ICONS[status]} | {_cell(note)} |")
        self.add("")
        if not shown:
            self.add("Дефектов нет, открытые вопросы по критериям в таблице.\n")
        for f in shown:
            self.defect(f)
        for f in findings:
            if f.status == "merged" and f.merged_into and f.critic_reason:
                self.add(f"{_link(f.id)} [{f.severity}] {_criterion(f.criterion)}: тот же дефект, что {_link(f.merged_into)}, слито критиком.\n")
            elif f.status == "merged" and f.merged_into:
                self.add(f"{_link(f.id)} [{f.severity}] {_criterion(f.criterion)}: повторяется в нескольких требованиях, см. {_link(f.merged_into)}.\n")
            elif not _active(f):
                self.add(f"{_link(f.id)} снято: {FINDING_STATUS_RU.get(f.status, f.status)}, см. [приложение Б](#appendix-b).\n")
        if x.id in r.rewritten:
            self.add(f"**Готовая формулировка:** {_one_line(r.rewritten[x.id])}\n")

    def defect(self, f: Finding) -> None:
        quotes = "; ".join(_evidence(e) for e in f.evidence if e.status != "missing")
        quote = f" Цитата: {quotes}." if quotes else ""
        impact = f" Последствие: {f.impact}" if f.impact else ""
        self.add(_target(f.id))
        self.add(f"**{f.id} [{f.severity}] {_criterion(f.criterion)}.** {f.problem}{quote}{impact}")
        others = [i for i in f.req_ids[1:] if i in self.reqs]
        if others:
            self.add(f"- Тот же дефект: {_links(others)}.")
        self.critic_line(f)
        self.question_line(f)
        self.add(f"- Как исправить: {f.recommendation}\n")

    def critic_line(self, f: Finding) -> None:
        absorbed = self.absorbed.get(f.id)
        if absorbed:
            self.add(f"- Критик слил сюда: {_links(absorbed)}, их текст в [приложении Б](#appendix-b).")
        if f.status == "downgraded" and f.severity_before:
            self.add(f"- Критик понизил уровень с {f.severity_before}: {f.critic_reason}")
        elif f.severity_before:
            self.add(f"- Уровень поднят до {f.severity} при слиянии с более критичным повтором.")

    def question_line(self, f: Finding) -> None:
        if f.question:
            see = f" См. {_link(f.question_id)}." if f.question_id else ""
            self.add(f"- Вопрос {_addressee(f.addressee)}: {f.question}{see}")

    # ---------- 4. набор ----------

    def set_review(self) -> None:
        r = self.r
        self.add("## 4. Проверка набора требований целиком\n")
        analyses = {a.criterion: a for a in r.set_analyses}
        set_findings = [f for f in r.findings if f.scope == "set" and _active(f)]
        number = 0
        for group in ("completeness", "consistency", "feasibility"):
            number += 1
            criteria = [c for c in SET_CRITERIA if c.group == group]
            codes = {c.code for c in criteria}
            self.add(f"### 4.{number}. {SET_SECTIONS[group]}\n")
            self.add("**Анализ.**\n")
            for c in criteria:
                a = analyses.get(c.code)
                if a:
                    self.add(f"- {c.name} ({c.source}): **{SET_STATUS_RU[a.status]}**. {_one_line(a.analysis)}")
                else:
                    self.add(f"- {c.name} ({c.source}): анализ не получен.")
            self.add("")
            if group == "feasibility":
                correct = [f for f in r.findings if f.scope == "requirement" and f.criterion == "CORRECT" and _active(f)]
                if correct:
                    self.add(f"Дефекты корректности в отдельных требованиях: {_links([f.id for f in correct])}.\n")
            items = [f for f in set_findings if f.criterion in codes or (not f.criterion.startswith("SET_") and group == SYSTEM_GROUP.get(f.criterion, "completeness"))]
            if not items:
                self.add("Замечаний нет.\n")
            for f in items:
                self.set_finding(f)

    def set_finding(self, f: Finding) -> None:
        self.add(_target(f.id))
        self.add(f"#### {f.id} [{f.severity}] {f.title or _criterion(f.criterion)}\n")
        self.add(f"- Вид: {KIND_RU.get(f.kind, f.kind)}. Критерий: {_criterion(f.criterion)}.")
        if f.req_ids:
            self.add(f"- Требования: {_links([i for i in f.req_ids if i in self.reqs])}.")
        if f.section:
            self.add(f"- Раздел: {f.section}.")
        if f.places:
            self.add(f"- Места: {'; '.join(f.places)}.")
        found = [e for e in f.evidence if e.status != "missing"]
        for e in found:
            self.add(f"- Цитата: {_evidence(e)}")
        if not found:
            self.add("- Цитаты нет: в документе этих сведений нет.")
        self.add(f"- Что не так: {f.problem}")
        self.critic_line(f)
        if f.impact:
            self.add(f"- Последствие: {f.impact}")
        self.question_line(f)
        self.add(f"- Как исправить: {f.recommendation}\n")

    # ---------- 5. сводка ----------

    def summary(self) -> None:
        r = self.r
        self.add('<a id="summary"></a>')
        self.add("## 5. Сводка\n")
        reviewed = [x for x in r.requirements if x.id not in r.unreviewed]
        with_defects = [x for x in reviewed if any(_active(f) for f in self.req_findings.get(x.id, []))]
        sev = Counter(f.severity for f in self.active)
        self.add("| Показатель | Значение |")
        self.add("| :--- | :---: |")
        self.add(f"| Требований всего | {len(r.requirements)} |")
        self.add(f"| без дефектов | {len(reviewed) - len(with_defects)} |")
        self.add(f"| с дефектами | {len(with_defects)} |")
        if r.unreviewed:
            self.add(f"| не проверено | {len(r.unreviewed)} |")
        self.add(f"| Замечаний всего | {len(self.active)} |")
        self.add(f"| в отдельных требованиях | {sum(1 for f in self.active if f.scope == 'requirement')} |")
        self.add(f"| по набору | {sum(1 for f in self.active if f.scope == 'set')} |")
        for s in SEVERITIES:
            self.add(f"| {s} ({SEVERITY_RU[s]}) | {sev.get(s, 0)} |")
        self.add(f"| Вопросов автору | {len(r.questions)} |")
        self.add("")

        blockers = [self.by_id[i] for i in r.verdict.blockers if i in self.by_id]
        self.add("### Блокеры\n")
        if not blockers:
            self.add("Критичных замечаний нет.\n")
            return
        number, used = 0, set()
        for title, match in BLOCKER_GROUPS:
            group = [f for f in blockers if f.id not in used and match(f)]
            if not group:
                continue
            self.add(f"**{title}**\n")
            for f in group:
                used.add(f.id)
                number += 1
                self.add(f"{number}. {_link(f.id)} · {_where_finding(f, self.reqs)} · {_one_line(f.title or f.problem, 200)}")
            self.add("")

    # ---------- 6. вердикт ----------

    def verdict(self) -> None:
        v = self.r.verdict
        self.add("## 6. Вердикт\n")
        self.add(f"**{v.decision}.**\n")
        if v.partial:
            self.add(PARTIAL_VERDICT + "\n")
        if v.blockers and not v.critic_done:
            self.add("Критичные замечания не перепроверены отдельным шагом.\n")
        self.add(f"Правило. {v.rule}\n")
        self.add(v.rationale + "\n")
        if v.top_fixes:
            self.add("Что исправить в первую очередь:\n")
            for number, fix in enumerate(v.top_fixes, start=1):
                self.add(f"{number}. {fix.action} ({_links(fix.finding_ids)})")
            self.add("")

    # ---------- 7. вопросы ----------

    def questions_section(self) -> None:
        r = self.r
        self.add('<a id="questions"></a>')
        self.add("## 7. Вопросы к автору ТЗ\n")
        if not r.questions:
            self.add("Вопросов нет.\n")
            return
        if not r.verdict.questions_by_model:
            self.add("Сводные вопросы не сформированы, ниже вопросы из замечаний по убыванию критичности.\n")
        main = [q for q in r.questions if not _review_only_question(q, self.by_id)]
        review = [q for q in r.questions if _review_only_question(q, self.by_id)]
        order = list(ADDRESSEES)
        for addressee in sorted({q.addressee for q in main}, key=lambda a: order.index(a) if a in order else len(order)):
            group = sorted((q for q in main if q.addressee == addressee), key=lambda q: -q.priority)
            self.add(f"### Вопросы {_addressee(addressee)}\n")
            for q in group:
                self.question(q)
        if review:
            self.add("### Требует проверки\n")
            self.add("Противоречие подтверждено только одной цитатой. Стоит проверить, прежде чем задавать вопрос.\n")
            for q in review:
                self.question(q)

    def question(self, q: Question) -> None:
        self.add(_target(q.id))
        self.add(f"#### {q.id} · {_addressee(q.addressee)} · {_blocks_label(q, self.by_id)}\n")
        self.add(q.text + "\n")
        for line in _question_body(q):
            self.add(line)
        self.add(f"- Закрывает замечания: {_links(q.finding_ids)}.\n")

    # ---------- приложения ----------

    def appendix_criteria(self) -> None:
        self.add("## Приложение А. Критерии и уровни критичности\n")
        self.add("Для отдельного требования:\n")
        for c in REQ_CRITERIA:
            self.add(f"- **{c.name}** ({c.source}). {c.question}")
        self.add("\nДля набора требований:\n")
        for c in SET_CRITERIA:
            self.add(f"- **{c.name}** ({c.source}, подраздел «{SET_SECTIONS[c.group]}»). {c.question}")
        self.add("\nУровни критичности:\n")
        self.add(SEVERITY_RULES + "\n")

    def appendix_removed(self) -> None:
        self.add('<a id="appendix-b"></a>')
        self.add("## Приложение Б. Снятые, слитые и неподтверждённые замечания\n")
        if not self.inactive:
            self.add("Таких замечаний нет.\n")
            return
        for f in self.inactive:
            reason = FINDING_STATUS_RU.get(f.status, f.status)
            if f.merged_into:
                reason += f" {_link(f.merged_into)}"
            if f.critic_reason:
                reason += f": {_no_dot(f.critic_reason)}"
            self.add(_target(f.id))
            self.add(
                f"- **{f.id} [{f.severity}] {_criterion(f.criterion)}** · {_where_finding(f, self.reqs)} · "
                f"{_no_dot(_one_line(f.title or f.problem, 200))}. Причина: {reason}."
            )
            for e in f.evidence:
                self.add(f"  - Цитата модели: {_evidence(e)}")
        self.add("")

    def render(self) -> str:
        self.first_screen()
        self.passport()
        self.segmentation()
        self.requirements()
        self.set_review()
        self.summary()
        self.verdict()
        self.questions_section()
        self.appendix_criteria()
        self.appendix_removed()
        return "\n".join(self.out)


def _question_body(q: Question) -> list[str]:
    """Общая часть вопроса для отчёта и для report.questions.md."""
    rows: list[str] = []
    if q.quotes:
        rows.append("- Сейчас в документе: " + "; ".join(_evidence(e) for e in q.quotes) + ".")
        if q.doc_says:
            rows.append(f"- Коротко: {q.doc_says}")
    elif q.doc_says:
        rows.append(f"- Сейчас в документе: {q.doc_says}")
    else:
        rows.append("- Сейчас в документе: не описано.")
    if q.options:
        rows.append("- Варианты:")
        for number, option in enumerate(q.options, start=1):
            rows.append(f"  {number}. {option.answer.rstrip('.')}. Последствие: {option.consequence}")
    if q.recommended:
        why = f", потому что {q.why_recommended[0].lower()}{q.why_recommended[1:]}" if q.why_recommended else ""
        rows.append(f"- Рекомендуем: вариант {q.recommended}{why}")
    if q.blocks:
        rows.append(f"- Без ответа нельзя: {q.blocks}")
    return rows


def render(result: RunResult) -> str:
    return _Report(result).render()


def render_questions(result: RunResult) -> str:
    """report.questions.md: только вопросы, без служебных ссылок, для письма автору ТЗ (О-08)."""
    out = [f"# Вопросы по документу «{result.document_name}»\n"]
    if not result.questions:
        out.append("Вопросов нет.\n")
        return "\n".join(out)
    out.append(
        "Вопросы собраны агентом проверки требований. Под каждым вопросом: что сейчас написано в документе, "
        "варианты ответа и что изменится при каждом из них. Достаточно ответить номером варианта или своим текстом.\n"
    )
    order = list(ADDRESSEES)
    addressees = sorted({q.addressee for q in result.questions}, key=lambda a: order.index(a) if a in order else len(order))
    number = 0
    for addressee in addressees:
        out.append(f"## Вопросы {_addressee(addressee)}\n")
        for q in sorted((q for q in result.questions if q.addressee == addressee), key=lambda q: -q.priority):
            number += 1
            out.append(f"### {number}. {q.text}\n")
            out.extend(_question_body(q))
            out.append("")
    return "\n".join(out)
