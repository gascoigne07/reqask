"""HTML-вариант отчёта: тот же RunResult и те же расчёты, что в report.py, другая разметка.

Отбор блокеров, счётчики, группы требований, причины снятия и тексты подписей берутся из _Report
и помощников report.py, поэтому числа и формулировки совпадают с report.md. Таблицы паспорта
собираются из строк, которые печатает report.py, чтобы паспорт не расходился с Markdown.

Файл самодостаточный: стили и небольшой скрипт встроены, внешних адресов нет, ссылки только на якоря
внутри страницы. Весь текст из документа и от модели проходит через html.escape. Без скрипта всё
содержимое видно; скрипт добавляет фильтр замечаний по уровню и кнопку «развернуть всё».
"""

from __future__ import annotations

import html
import re
from collections import Counter

from . import report as md
from .criteria import REQ_CRITERIA, SET_CRITERIA, SET_SECTIONS, SEVERITIES, SEVERITY_RU, SEVERITY_RULES
from .grounding import distinct_quotes
from .report import (
    BLOCKER_GROUPS,
    FINDING_STATUS_RU,
    FIRST_SCREEN_BLOCKERS,
    FIRST_SCREEN_BLOCKERS_ALL,
    FIRST_SCREEN_QUESTIONS,
    KIND_RU,
    QUESTION_NUMBERS_NOTE,
    SET_STATUS_RU,
    SKIP_REASONS_RU,
    STATUS_RU,
    SYSTEM_GROUP,
    _active,
    _addressee,
    _blocks_label,
    _criterion,
    _gist,
    _lines,
    _no_dot,
    _one_line,
    _partial_verdict,
    _ranges,
    _repeats_quotes,
    _review_only_question,
    _sentence_case,
    _short_section,
)
from .schemas import Evidence, Finding, Question, Requirement, RunResult

# Отметки оценок вместо значков report.md: эмодзи в HTML не используем, смысл тот же.
MARKS = {"pass": "✓", "fail": "✗", "na": "○", "unknown": "?"}
DECISION_CLASS = {"Не рекомендуется начинать": "bad", "Условно допускается": "warn", "Допускается": "ok"}
SECTIONS = (
    ("first", "Итог"),
    ("passport", "1. Паспорт прогона"),
    ("segmentation", "2. Нарезка"),
    ("requirements", "3. Требования"),
    ("set-review", "4. Набор целиком"),
    ("summary", "5. Сводка"),
    ("verdict", "6. Вердикт"),
    ("questions", "7. Вопросы"),
    ("appendix-a", "Приложение А"),
    ("appendix-b", "Приложение Б"),
)


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def _hid(ident: str) -> str:
    """Якорь из идентификатора: как в report.md (строчные буквы), посторонние знаки заменены дефисом."""
    return re.sub(r"[^\w-]+", "-", str(ident).lower()).strip("-") or "id"


def _ready_class(value: str) -> str:
    if value == "Нет":
        return "bad"
    if value.startswith("Да,"):
        return "warn"
    return "ok" if value == "Да" else "none"


def _sev(f: Finding) -> str:
    return esc(f.severity.lower())


def _split_row(line: str) -> list[str]:
    """Строка таблицы Markdown из report.py: ячейки разделены |, а | внутри текста экранирован (_cell)."""
    cells = re.split(r"(?<!\\)\|", line.strip())[1:-1]
    return [c.strip().replace("\\|", "|") for c in cells]


def _md_tables(lines: list[str]) -> list[dict]:
    """Таблицы из вывода раздела report.py, с пометкой, лежит ли таблица внутри <details>."""
    tables: list[dict] = []
    summary = None
    current = None
    for line in lines:
        for part in line.split("\n"):
            m = re.match(r"<details><summary>(.*)</summary>", part)
            if m:
                summary = m.group(1)
                continue
            if part.startswith("</details>"):
                summary = None
                continue
            if part.startswith("|"):
                cells = _split_row(part)
                if all(re.fullmatch(r":?-+:?", c) for c in cells):
                    continue
                if current is None:
                    current = {"summary": summary, "head": cells, "rows": []}
                    tables.append(current)
                else:
                    current["rows"].append(cells)
            else:
                current = None
    return tables


def _cell_html(text: str) -> str:
    # В паспорте инлайн-кодом стоит только SHA-256; остальной текст выводится как есть.
    m = re.fullmatch(r"`([^`]*)`", text)
    return f"<code>{esc(m.group(1))}</code>" if m else esc(text)


class _Html(md._Report):
    def __init__(self, result: RunResult):
        super().__init__(result)
        self.ids: set[str] = set()

    # ---------- помощники разметки ----------

    def tid(self, ident: str) -> str:
        """Атрибут id для цели ссылки; повтор не ставится, чтобы идентификаторы на странице не дублировались."""
        hid = _hid(ident)
        if hid in self.ids:
            return ""
        self.ids.add(hid)
        return f' id="{esc(hid)}"'

    def link(self, ident: str, cls: str = "") -> str:
        attr = f' class="{cls}"' if cls else ""
        return f'<a href="#{esc(_hid(ident))}"{attr}>{esc(ident)}</a>'

    def links(self, ids: list[str]) -> str:
        return ", ".join(self.link(i) for i in ids)

    def evidence(self, item: Evidence) -> str:
        line = f' <span class="ln">(строка {item.line})</span>' if item.line else ""
        note = {
            "exact": "",
            "fuzzy": ", восстановлена по близкому совпадению",
            "missing": ", не найдена в документе",
        }.get(item.status, "")
        return f'<span class="quote">{esc(" ".join(item.quote.split()))}</span>{line}{esc(note)}'

    def where(self, f: Finding) -> str:
        if f.req_ids:
            return ", ".join(self.link(i) for i in f.req_ids if i in self.reqs)
        if f.section:
            return f"раздел «{esc(f.section)}»"
        return "набор в целом"

    def blocker_line(self, f: Finding, joined: list[str], limit: int = md.BLOCKER_TEXT) -> str:
        gist = esc(_no_dot(_gist(f, limit)))
        if joined:
            gist = f"{gist} (вместе с {self.links(joined)})"
        return (f'{self.link(f.id, "bid sev-" + _sev(f))} <span class="sep">·</span> '
                f'<span class="where">{self.where(f)}</span> <span class="sep">·</span> {gist}')

    def section(self, key: str, title: str) -> None:
        self.add(f'<section class="part"{self.tid(key)}>')
        self.add(f"<h2>{esc(title)}</h2>")

    def end(self) -> None:
        self.add("</section>")

    def table(self, head: list[str], rows: list[list[str]], cls: str = "") -> None:
        """Ячейки уже в HTML. Широкая таблица прокручивается внутри своей обёртки."""
        self.add(f'<div class="table-wrap"><table class="{cls}">')
        self.add("<thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>")
        for row in rows:
            self.add("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        self.add("</tbody></table></div>")

    # ---------- первый экран ----------

    def toc(self) -> None:
        items = "".join(f'<li><a href="#{key}">{esc(title)}</a></li>' for key, title in SECTIONS)
        self.add(f'<nav class="toc" aria-label="Оглавление"><ul>{items}</ul>')
        buttons = "".join(
            f'<button type="button" data-sev="{s.lower()}" aria-pressed="false">{s}</button>' for s in SEVERITIES
        )
        self.add(
            '<div class="tools" id="tools" hidden><span class="tools-label">Замечания:</span>'
            '<button type="button" data-sev="" aria-pressed="true">все</button>'
            f'{buttons}<button type="button" data-act="open">развернуть всё</button></div>'
        )
        self.add("</nav>")

    def first_screen(self) -> None:
        r, v = self.r, self.r.verdict
        self.add('<header class="doc-head">')
        self.add(f"<h1>Отчёт о проверке требований: {esc(r.document_name)}</h1>")
        self.add(
            '<p class="sub">Отчёт сформирован агентом reqask автоматически по ISO/IEC/IEEE 29148:2018 и IEEE 830. '
            f"Модель: {esc(r.model)}. Дата: {esc(r.started_at)}.</p>"
        )
        self.add("</header>")
        self.toc()
        self.add(f'<section class="first"{self.tid("first")}>')
        self.incomplete_block()
        cls = DECISION_CLASS.get(v.decision, "none")
        self.add(f'<div class="verdict v-{cls}">')
        self.add(f'<div class="verdict-main"><span class="label">Вердикт</span>'
                 f'<strong class="decision">{esc(v.decision)}</strong></div>')
        if v.partial:
            self.add(f'<p class="verdict-note">{esc(_partial_verdict(v))}</p>')
        if v.blockers and not v.critic_done:
            self.add('<p class="verdict-note">Критичные замечания не перепроверены отдельным шагом.</p>')
        self.add('<dl class="ready">')
        for label, value in (("Готовность к разработке", v.ready_for_development),
                             ("Готовность к тестированию", v.ready_for_testing)):
            self.add(f'<div><dt>{label}</dt><dd class="r-{_ready_class(value)}">{esc(value)}</dd></div>')
        self.add("</dl></div>")

        sev = Counter(f.severity for f in self.active)
        with_defects = sum(1 for rid in self.reqs if self._has_defect(rid))
        tiles = [
            ("reqs", "", len(self.reqs), "Требований"),
            ("with-defects", "", with_defects, "с дефектами"),
            *((s.lower(), f" sev-{s.lower()}", sev.get(s, 0), s) for s in SEVERITIES),
            ("questions", "", len(r.questions), "Вопросов автору"),
        ]
        self.add('<div class="tiles">')
        for key, extra, value, label in tiles:
            self.add(f'<div class="tile{extra}" data-k="{key}"><b>{value}</b><span>{esc(label)}</span></div>')
        self.add("</div>")
        lost = [f for f in self.inactive if f.severity == "CRITICAL" and f.status in ("quarantine", "question_only")]
        if lost:
            self.add(f'<p class="warn-line">{len(lost)} критичных замечаний не подтверждены цитатой, '
                     'см. <a href="#appendix-b">приложение Б</a>.</p>')
        if v.blockers:
            self.add("<h2>Блокеры</h2>")
            rows = self._blocker_rows()
            shown = len(rows) if len(rows) <= FIRST_SCREEN_BLOCKERS_ALL else FIRST_SCREEN_BLOCKERS
            self.add('<ul class="blockers">')
            for f, joined in rows[:shown]:
                self.add(f"<li>{self.blocker_line(f, joined)}</li>")
            rest = len(rows) - shown
            if rest > 0:
                self.add(f'<li>и ещё {rest}, полный список в <a href="#summary">разделе 5</a></li>')
            self.add("</ul>")
        if r.questions:
            self.add("<h2>Главные вопросы автору ТЗ</h2>")
            self.add('<ul class="topq">')
            for q in r.questions[:FIRST_SCREEN_QUESTIONS]:
                self.add(f'<li>{self.link(q.id, "qid")} <span class="sep">·</span> {esc(_addressee(q.addressee))}: '
                         f"{esc(_one_line(q.text, 220))}</li>")
            self.add("</ul>")
            self.add('<p>Все вопросы в <a href="#questions">разделе 7</a>, для отправки автору: '
                     "файл <code>report.questions.md</code>.</p>")
        self.add("</section>")

    def incomplete_block(self) -> None:
        r = self.r
        failed = [s for s in r.steps if s.status in ("failed", "degraded")]
        if not (r.failed_steps or r.unreviewed or failed or r.fatal):
            return
        self.add('<div class="incomplete" role="note"><p><strong>Отчёт неполный.</strong> Часть работы не выполнена:</p><ul>')
        if r.fatal:
            self.add(f"<li>причина: {esc(_one_line(r.fatal, 400))}</li>")
        for s in failed:
            self.add(f"<li>шаг {esc(s.number)} «{esc(s.name)}»: {esc(md.STEP_STATUS_RU[s.status])}</li>")
        for item in r.failed_steps:
            self.add(f"<li>{esc(_one_line(item, 300))}</li>")
        if r.unreviewed:
            self.add(f"<li>требования без проверки: {self.links(r.unreviewed)}</li>")
        self.add("</ul></div>")

    # ---------- 1. паспорт ----------

    def passport(self) -> None:
        # Тексты паспорта печатает report.py, здесь только другая разметка тех же таблиц.
        source = md._Report(self.r)
        source.passport()
        self.section("passport", "1. Паспорт прогона")
        for t in _md_tables(source.out):
            rows = [[_cell_html(c) for c in row] for row in t["rows"]]
            head = [esc(h) for h in t["head"]]
            if t["summary"]:
                self.add(f'<details class="journal"><summary>{esc(t["summary"])}</summary>')
                for row in rows:
                    status = row[2] if len(row) > 2 else ""
                    if status in ("не выполнен", "частично"):
                        row[2] = f'<span class="st-{"bad" if status == "не выполнен" else "warn"}">{status}</span>'
                self.table(head, rows, "steps")
                self.add("</details>")
            else:
                self.table(head, rows, "kv")
        self.end()

    # ---------- 2. нарезка ----------

    def segmentation(self) -> None:
        r = self.r
        self.section("segmentation", "2. Нарезка на требования")
        with_id = sum(1 for x in r.requirements if x.source_id)
        self.add(
            f"<p>Выделено требований: <strong>{len(r.requirements)}</strong>, у {with_id} есть идентификатор в документе. "
            "Границы заданы номерами строк, текст требований вырезан из документа кодом. "
            "Дословный текст каждого требования стоит в разделе 3.</p>"
        )
        self.add(f"<details><summary>Таблица нарезки: {len(r.requirements)} требований</summary>")
        rows = []
        for x in r.requirements:
            lines = f"{x.line_start}-{x.line_end}" if x.line_end != x.line_start else str(x.line_start)
            if x.page:
                lines += f", стр. {x.page}"
            rows.append([self.link(x.id), esc(x.source_id or "без номера"), esc(_short_section(x.section)),
                         esc(lines), esc(x.summary)])
        self.table(["ID", "ID в документе", "Раздел", "Строки", "Суть"], rows, "seg")
        self.add("</details>")
        if r.skipped_lines:
            by_reason: dict[str, list[tuple[int, int]]] = {}
            for span in r.skipped_lines:
                by_reason.setdefault(span.reason, []).append((span.line_start, span.line_end))
            self.add("<p>Не вошли в требования (эти строки видит проверка набора в разделе 4):</p><ul>")
            for reason, spans in by_reason.items():
                self.add(f"<li>{esc(SKIP_REASONS_RU.get(reason, reason))}: строки {esc(_ranges(sorted(spans)))}</li>")
            self.add("</ul>")
        if r.uncovered_lines:
            self.add(
                f"<p>Строки с текстом, которые не попали ни в требования, ни в список выше: "
                f"{esc(_ranges(r.uncovered_lines))}. Их стоит проверить глазами.</p>"
            )
        q = r.quality
        if q.ids_missing:
            self.add(f"<p>Идентификаторы из документа, которых нет в нарезке: {esc(', '.join(q.ids_missing))}.</p>")
        self.end()

    # ---------- 3. каждое требование ----------

    def notes_html(self, x: Requirement, explained: set[str], with_na: bool = True) -> list[str]:
        """То же, что _Report._notes, но с отметкой вместо значка."""
        visible, st = self._statuses(x)
        notes = []
        for c in visible:
            status = st["statuses"][c.code]
            if status == "pass" or (status == "na" and not with_na) or (status == "fail" and c.code in explained):
                continue
            check = st["checks"].get(c.code)
            text = _no_dot(_one_line(check.note if check and check.note else STATUS_RU[status]))
            notes.append(f'<span class="mark st-{status}" title="{esc(STATUS_RU[status])}">{MARKS[status]}</span> '
                         f"{esc(c.name)}: {esc(text)}")
        return notes

    def moved_html(self, x: Requirement, shown: frozenset[str] = frozenset()) -> str:
        """То же, что _Report._moved, со ссылками в HTML."""
        merged: list[str] = []
        folded: list[str] = []
        other: dict[str, list[str]] = {}
        for f in self.req_findings.get(x.id, []):
            if f.status == "merged" and f.merged_into in shown and f.id in self.absorbed.get(f.merged_into, []):
                continue
            if f.status == "merged" and f.merged_into:
                (merged if f.critic_reason else folded).append(f"{self.link(f.id)} в {self.link(f.merged_into)}")
            elif not _active(f):
                other.setdefault(FINDING_STATUS_RU.get(f.status, f.status), []).append(self.link(f.id))
        parts = []
        if merged:
            parts.append("слито критиком: " + ", ".join(merged))
        if folded:
            parts.append("свёрнуто в системное: " + ", ".join(folded))
        for status, ids in other.items():
            parts.append(f'{esc(status)}: {", ".join(ids)}, см. <a href="#appendix-b">приложение Б</a>')
        return "; ".join(parts)

    def requirements(self) -> None:
        self.section("requirements", "3. Проверка каждого требования")
        legend = ", ".join(
            f'<span class="mark st-{s}">{MARKS[s]}</span> {t}'
            for s, t in (("pass", "выполнен"), ("fail", "нарушен"), ("na", "не применим"), ("unknown", "нельзя оценить по тексту"))
        )
        self.add(
            f'<p class="legend">Отметки: {legend}. Шесть основных критериев показаны всегда, '
            "уместность уровня, атомарность и корректность только при нарушении.</p>"
        )
        quiet = [x for x in self.r.requirements if self._quiet(x)]
        moved = [x for x in quiet if self._has_defect(x.id)]
        noted = [x for x in quiet if x not in moved and (self._moved(x) or self._notes(x, set(), with_na=False))]
        plain = [x for x in quiet if x not in moved and x not in noted]
        set_refs: dict[str, list[str]] = {}
        for f in self.active:
            if f.scope == "set":
                for rid in f.req_ids:
                    set_refs.setdefault(rid, []).append(f.id)
        touched = [x for x in plain if x.id in set_refs]
        plain = [x for x in plain if x.id not in set_refs]
        if plain:
            items = ", ".join(f"<span{self.tid(x.id)}>{esc(x.id)} ({_lines(x.line_start, x.line_end)})</span>" for x in plain)
            self.add(f'<p class="plain"><strong>Без замечаний, все применимые критерии выполнены ({len(plain)}):</strong> {items}.</p>')
        if touched:
            self.add(f"<p><strong>Своих замечаний нет, но требование затронуто общими замечаниями ({len(touched)}):</strong></p><ul>")
            for x in touched:
                self.add(f"<li><strong{self.tid(x.id)}>{esc(self._req_head(x))}</strong>: {self.links(set_refs[x.id])}.</li>")
            self.add("</ul>")
        for title, group in (
            ("Дефект описан в общем замечании, на которое ссылается строка", moved),
            ("Без замечаний, с пометками к оценкам", noted),
        ):
            if not group:
                continue
            self.add(f"<p><strong>{title} ({len(group)}):</strong></p><ul>")
            for x in group:
                tail = "; ".join(([self.moved_html(x)] if self._moved(x) else []) + self.notes_html(x, set(), with_na=False))
                self.add(f"<li><strong{self.tid(x.id)}>{esc(self._req_head(x))}</strong>: {tail}.</li>")
            self.add("</ul>")
        for x in self.r.requirements:
            if x not in quiet:
                self.requirement_block(x)
        self.end()

    def requirement_block(self, x: Requirement) -> None:
        r = self.r
        self.add(f'<section class="req"{self.tid(x.id)}>')
        self.add(f"<h3>{esc(self._req_head(x))}</h3>")
        if "\n" in x.quote.strip():
            self.add(f'<pre class="doc">{esc(x.quote.strip(chr(10)))}</pre>')
        else:
            self.add(f'<blockquote class="doc">{esc(x.quote.strip())}</blockquote>')
        if x.id in r.unreviewed:
            self.add("<p>Требование не проверено: модель не вернула по нему результат.</p></section>")
            return
        shown = [f for f in self.req_findings.get(x.id, []) if _active(f)]
        visible, st = self._statuses(x)
        chips = " ".join(
            f'<span class="chip st-{st["statuses"][c.code]}" title="{esc(c.name)}: {esc(STATUS_RU[st["statuses"][c.code]])}">'
            f'{MARKS[st["statuses"][c.code]]} {esc(c.short)}</span>'
            for c in visible
        )
        self.add(f'<p class="checks">Оценки: {chips}</p>')
        notes = self.notes_html(x, {f.criterion for f in shown})
        if notes:
            self.add('<ul class="check-notes">' + "".join(f"<li>{n}</li>" for n in notes) + "</ul>")
        for f in shown:
            self.defect(f)
        moved = self.moved_html(x, frozenset(f.id for f in shown))
        if moved:
            self.add(f'<p class="moved">{moved[0].upper()}{moved[1:]}.</p>')
        if x.id in r.rewritten:
            self.add(f'<div class="rewrite"><strong>Готовая формулировка:</strong> {esc(_one_line(r.rewritten[x.id]))}</div>')
        self.add("</section>")

    def card_head(self, f: Finding, title: str) -> str:
        return (f'<header><span class="badge sev-{_sev(f)}">{esc(f.severity)}</span> '
                f'<span class="fid">{esc(f.id)}</span> <span class="ftitle">{esc(title)}</span></header>')

    def defect(self, f: Finding) -> None:
        self.add(f'<article class="card sev-{_sev(f)}" data-sev="{_sev(f)}"{self.tid(f.id)}>')
        self.add(self.card_head(f, _criterion(f.criterion)))
        self.add(f'<p class="problem">{esc(f.problem)}</p>')
        found = md._found(f.evidence)
        if found:
            self.add('<p class="cite"><span class="k">Цитата:</span> ' + "; ".join(self.evidence(e) for e in found) + ".</p>")
        if f.impact and f.severity != "MINOR":
            self.add(f'<p><span class="k">Последствие:</span> {esc(f.impact)}</p>')
        others = [i for i in f.req_ids[1:] if i in self.reqs]
        if others:
            self.add(f'<p class="note">Тот же дефект: {self.links(others)}.</p>')
        self.critic_line(f)
        self.question_line(f)
        if not (f.req_ids and f.req_ids[0] in self.r.rewritten):
            self.add(f'<p class="fix"><span class="k">Как исправить:</span> {esc(f.recommendation)}</p>')
        self.add("</article>")

    def critic_line(self, f: Finding) -> None:
        if f.severity_raised_from:
            what = md._DIVERGENCE_RU.get(f.divergence or "", "разное поведение")
            self.add(f'<p class="note">Уровень поднят кодом с {esc(f.severity_raised_from)} до CRITICAL: '
                     f"два места документа задают {esc(what)}.</p>")
        absorbed = self.absorbed.get(f.id)
        if absorbed:
            self.add(f'<p class="note">Критик слил сюда: {self.links(absorbed)}, их текст в '
                     '<a href="#appendix-b">приложении Б</a>.</p>')
        if f.status == "downgraded" and f.severity_before:
            self.add(f'<p class="note">Критик понизил уровень с {esc(f.severity_before)}: {esc(f.critic_reason or "")}</p>')
        elif f.severity_before:
            self.add(f'<p class="note">Уровень поднят до {esc(f.severity)} при слиянии с более критичным повтором.</p>')

    def question_line(self, f: Finding) -> None:
        if f.question:
            see = f" См. {self.link(f.question_id, 'qid')}." if f.question_id else ""
            self.add(f'<p class="ask"><span class="k">Вопрос {esc(_addressee(f.addressee))}:</span> {esc(f.question)}{see}</p>')
        elif f.question_id:
            q = self.questions.get(f.question_id)
            text = f" {esc(q.text)}" if q else ""
            self.add(f'<p class="ask"><span class="k">Вопрос {esc(_addressee(q.addressee if q else None))}:</span>{text} '
                     f"См. {self.link(f.question_id, 'qid')}.</p>")

    # ---------- 4. набор ----------

    def set_review(self) -> None:
        r = self.r
        self.section("set-review", "4. Проверка набора требований целиком")
        analyses = {a.criterion: a for a in r.set_analyses}
        set_findings = [f for f in r.findings if f.scope == "set" and _active(f)]
        number = 0
        for group in ("completeness", "consistency", "feasibility"):
            number += 1
            criteria = [c for c in SET_CRITERIA if c.group == group]
            codes = {c.code for c in criteria}
            self.add(f"<h3>4.{number}. {esc(SET_SECTIONS[group])}</h3>")
            self.add('<p><strong>Анализ.</strong></p><ul class="analysis">')
            for c in criteria:
                a = analyses.get(c.code)
                if a:
                    self.add(f"<li>{esc(c.name)} ({esc(c.source)}): <strong class=\"set-{esc(a.status)}\">"
                             f"{esc(SET_STATUS_RU[a.status])}</strong>. {esc(_one_line(a.analysis))}</li>")
                else:
                    self.add(f"<li>{esc(c.name)} ({esc(c.source)}): анализ не получен.</li>")
            self.add("</ul>")
            if group == "feasibility":
                correct = [f for f in r.findings if f.scope == "requirement" and f.criterion == "CORRECT" and _active(f)]
                if correct:
                    self.add(f"<p>Дефекты корректности в отдельных требованиях: {self.links([f.id for f in correct])}.</p>")
            items = [f for f in set_findings if f.criterion in codes or (not f.criterion.startswith("SET_") and group == SYSTEM_GROUP.get(f.criterion, "completeness"))]
            if not items:
                self.add("<p>Замечаний нет.</p>")
            for f in items:
                self.set_finding(f)
        self.end()

    def set_finding(self, f: Finding) -> None:
        self.add(f'<article class="card sev-{_sev(f)}" data-sev="{_sev(f)}"{self.tid(f.id)}>')
        self.add(self.card_head(f, f.title or _criterion(f.criterion)))
        meta = [esc(KIND_RU.get(f.kind, f.kind).capitalize()), esc(_criterion(f.criterion))]
        req_ids = [i for i in f.req_ids if i in self.reqs]
        if req_ids:
            meta.append(self.links(req_ids))
        if f.section:
            meta.append(f"раздел «{esc(_no_dot(f.section))}»")
        self.add(f'<p class="meta">{" · ".join(meta)}.</p>')
        if f.places:
            self.add(f'<p><span class="k">Места:</span> {esc("; ".join(f.places))}.</p>')
        found = md._found(f.evidence)
        if found:
            label = "Цитата" if len(found) == 1 else "Цитаты"
            self.add(f'<p class="cite"><span class="k">{label}:</span> ' + "; ".join(self.evidence(e) for e in found) + ".</p>")
        else:
            self.add('<p class="cite">Цитаты нет: в документе этих сведений нет.</p>')
        impact = f' <span class="k">Последствие:</span> {esc(f.impact)}' if f.impact and f.severity != "MINOR" else ""
        self.add(f'<p class="problem"><span class="k">Что не так:</span> {esc(f.problem)}{impact}</p>')
        self.critic_line(f)
        self.question_line(f)
        self.add(f'<p class="fix"><span class="k">Как исправить:</span> {esc(f.recommendation)}</p>')
        self.add("</article>")

    # ---------- 5. сводка ----------

    def summary(self) -> None:
        r = self.r
        self.section("summary", "5. Сводка")
        reviewed = [x for x in r.requirements if x.id not in r.unreviewed]
        with_defects = [x for x in reviewed if self._has_defect(x.id)]
        sev = Counter(f.severity for f in self.active)
        rows = [
            ["Требований всего", len(r.requirements)],
            ["без дефектов", len(reviewed) - len(with_defects)],
            ["с дефектами", len(with_defects)],
        ]
        if r.unreviewed:
            rows.append(["не проверено", len(r.unreviewed)])
        rows += [
            ["Замечаний всего", len(self.active)],
            ["в отдельных требованиях", sum(1 for f in self.active if f.scope == "requirement")],
            ["по набору", sum(1 for f in self.active if f.scope == "set")],
            *([f"{s} ({SEVERITY_RU[s]})", sev.get(s, 0)] for s in SEVERITIES),
            ["Вопросов автору", len(r.questions)],
        ]
        self.table(["Показатель", "Значение"], [[esc(a), esc(b)] for a, b in rows], "kv num")
        blockers = self._blocker_rows()
        self.add("<h3>Блокеры</h3>")
        if not blockers:
            self.add("<p>Критичных замечаний нет.</p>")
            self.end()
            return
        number, used = 0, set()
        for title, match in BLOCKER_GROUPS:
            group = [(f, joined) for f, joined in blockers if f.id not in used and match(f)]
            if not group:
                continue
            self.add(f"<p><strong>{esc(title)}</strong></p>")
            self.add(f'<ol class="blockers" start="{number + 1}">')
            for f, joined in group:
                used.add(f.id)
                number += 1
                self.add(f"<li>{self.blocker_line(f, joined, 200)}</li>")
            self.add("</ol>")
        self.end()

    # ---------- 6. вердикт ----------

    def verdict(self) -> None:
        v = self.r.verdict
        self.section("verdict", "6. Вердикт")
        self.add(f'<p class="decision-line v-{DECISION_CLASS.get(v.decision, "none")}"><strong>{esc(v.decision)}.</strong></p>')
        if v.partial:
            self.add(f"<p>{esc(_partial_verdict(v, with_reason=False))}</p>")
        if v.blockers and not v.critic_done:
            self.add("<p>Критичные замечания не перепроверены отдельным шагом.</p>")
        self.add(f'<p class="rule">Правило. {esc(v.rule)}</p>')
        self.add(f"<p>{esc(v.rationale)}</p>")
        if v.top_fixes:
            self.add("<p>Что исправить в первую очередь:</p><ol>")
            for fix in v.top_fixes:
                self.add(f"<li>{esc(fix.action)} ({self.links(fix.finding_ids)})</li>")
            self.add("</ol>")
        self.end()

    # ---------- 7. вопросы ----------

    def questions_section(self) -> None:
        r = self.r
        self.section("questions", "7. Вопросы к автору ТЗ")
        if not r.questions:
            self.add("<p>Вопросов нет.</p>")
            self.end()
            return
        if not r.verdict.questions_by_model:
            self.add("<p>Сводные вопросы не сформированы, ниже вопросы из замечаний по убыванию критичности.</p>")
        main = [q for q in r.questions if not _review_only_question(q, self.by_id)]
        review = [q for q in r.questions if _review_only_question(q, self.by_id)]
        if len({q.addressee for q in main}) > 1:
            self.add(f"<p>{QUESTION_NUMBERS_NOTE}</p>")
        order = list(md.ADDRESSEES)
        for addressee in sorted({q.addressee for q in main}, key=lambda a: order.index(a) if a in order else len(order)):
            group = sorted((q for q in main if q.addressee == addressee), key=lambda q: -q.priority)
            self.add(f"<h3>Вопросы {esc(_addressee(addressee))}</h3>")
            for q in group:
                self.question(q)
        if review:
            self.add("<h3>Требует проверки</h3>")
            self.add("<p>Противоречие подтверждено только одной цитатой. Стоит проверить, прежде чем задавать вопрос.</p>")
            for q in review:
                self.question(q)
        self.end()

    def question(self, q: Question) -> None:
        label = _blocks_label(q, self.by_id)
        cls = {"блокирует разработку": "critical", "нужен до начала спринта": "major"}.get(label, "minor")
        self.add(f'<article class="card qcard sev-{cls}"{self.tid(q.id)}>')
        self.add(f'<header><span class="fid">{esc(q.id)}</span> <span class="sep">·</span> {esc(_addressee(q.addressee))} '
                 f'<span class="sep">·</span> <span class="badge sev-{cls}">{esc(label)}</span></header>')
        self.add(f'<p class="qtext">{esc(q.text)}</p>')
        self.add(self.question_body(q))
        self.add(f'<p class="note">Закрывает замечания: {self.links(q.finding_ids)}.</p>')
        self.add("</article>")

    def question_body(self, q: Question) -> str:
        """То же, что report._question_body, в HTML."""
        rows: list[str] = []
        quotes = distinct_quotes(q.quotes)
        if quotes:
            rows.append('<p class="cite"><span class="k">Сейчас в документе:</span> '
                        + "; ".join(self.evidence(e) for e in quotes) + ".</p>")
            if q.doc_says and not _repeats_quotes(q.doc_says, quotes):
                rows.append(f'<p><span class="k">Суть:</span> {esc(q.doc_says)}</p>')
        elif q.doc_says:
            rows.append(f'<p><span class="k">Сейчас в документе:</span> {esc(q.doc_says)}</p>')
        else:
            rows.append('<p><span class="k">Сейчас в документе:</span> не описано.</p>')
        if q.options:
            rows.append('<p class="k">Варианты:</p><ol class="options">')
            for number, option in enumerate(q.options, start=1):
                rec = ' class="recommended"' if q.recommended == number else ""
                rows.append(f"<li{rec}>{esc(option.answer.rstrip('.'))}. "
                            f'<span class="k">Последствие:</span> {esc(_no_dot(_sentence_case(option.consequence)))}.</li>')
            rows.append("</ol>")
        if q.recommended:
            why = f", потому что {esc(_no_dot(_sentence_case(q.why_recommended)))}." if q.why_recommended else "."
            rows.append(f'<p class="rec"><span class="k">Рекомендуем:</span> вариант {esc(q.recommended)}{why}</p>')
        if q.blocks:
            rows.append(f'<p><span class="k">Без ответа:</span> {esc(_no_dot(_sentence_case(q.blocks)))}.</p>')
        return "\n".join(rows)

    # ---------- приложения ----------

    def appendix_criteria(self) -> None:
        self.section("appendix-a", "Приложение А. Критерии и уровни критичности")
        self.add("<p>Для отдельного требования:</p><ul>")
        for c in REQ_CRITERIA:
            self.add(f"<li><strong>{esc(c.name)}</strong> ({esc(c.source)}). {esc(c.question)}</li>")
        self.add("</ul><p>Для набора требований:</p><ul>")
        for c in SET_CRITERIA:
            self.add(f"<li><strong>{esc(c.name)}</strong> ({esc(c.source)}, подраздел «{esc(SET_SECTIONS[c.group])}»). "
                     f"{esc(c.question)}</li>")
        self.add("</ul><p>Уровни критичности:</p><ul>")
        for line in SEVERITY_RULES.splitlines():
            self.add(f"<li>{esc(line[2:] if line.startswith('- ') else line)}</li>")
        self.add("</ul>")
        self.end()

    def appendix_removed(self) -> None:
        self.section("appendix-b", "Приложение Б. Снятые, слитые и неподтверждённые замечания")
        if not self.inactive:
            self.add("<p>Таких замечаний нет.</p>")
            self.end()
            return
        self.add('<ul class="removed">')
        for f in self.inactive:
            reason = esc(FINDING_STATUS_RU.get(f.status, f.status))
            if f.merged_into:
                reason += f" {self.link(f.merged_into)}"
            if f.critic_reason:
                reason += f": {esc(_no_dot(f.critic_reason))}"
            item = (f'<li{self.tid(f.id)}><span class="badge sev-{_sev(f)}">{esc(f.severity)}</span> '
                    f"<strong>{esc(f.id)} {esc(_criterion(f.criterion))}</strong> · {self.where(f)} · "
                    f"{esc(_no_dot(_gist(f, 200)))}. Причина: {reason}.")
            if f.status != "merged" and f.evidence:
                item += "<ul>" + "".join(f"<li>Цитата модели: {self.evidence(e)}</li>" for e in f.evidence) + "</ul>"
            self.add(item + "</li>")
        self.add("</ul>")
        self.end()

    # ---------- страница ----------

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
        body = "\n".join(self.out)
        # Ссылка на замечание или вопрос, которого на странице нет (например, вопрос отброшен), становится текстом.
        body = re.sub(
            r'<a href="#([^"]*)"[^>]*>(.*?)</a>',
            lambda m: m.group(0) if m.group(1) in self.ids else f'<span class="dead">{m.group(2)}</span>',
            body,
        )
        title = esc(f"Отчёт о проверке требований: {self.r.document_name}")
        return (
            '<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "<meta http-equiv=\"content-security-policy\" content=\"default-src 'none'; "
            "style-src 'unsafe-inline'; script-src 'unsafe-inline'\">\n"
            '<meta name="color-scheme" content="light dark">\n'
            f"<title>{title}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main class=\"wrap\">\n"
            f"{body}\n</main>\n<script>{JS}</script>\n</body>\n</html>\n"
        )


def render_html(result: RunResult) -> str:
    return _Html(result).render()


CSS = """
:root {
  --bg: #ffffff; --fg: #1b1d21; --muted: #545a63; --line: #d5d9df; --surface: #f4f6f8; --link: #0b57b0;
  --crit-bg: #fde7e7; --crit-fg: #8b1010; --crit-bd: #c62828;
  --maj-bg: #fdf0d6; --maj-fg: #6e4300; --maj-bd: #d48806;
  --min-bg: #e7eef7; --min-fg: #1f426b; --min-bd: #5b7fa8;
  --ok-bg: #e2f3e6; --ok-fg: #1b5a2d; --ok-bd: #2e7d43;
  --none-bg: #eceef1; --none-fg: #3a3f46; --none-bd: #8a929c;
  --quote-bg: #eef1f5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171a; --fg: #e6e8eb; --muted: #a9b0b8; --line: #343a41; --surface: #1d2024; --link: #8bb8ff;
    --crit-bg: #4a1818; --crit-fg: #ffd0d0; --crit-bd: #ef6060;
    --maj-bg: #43310d; --maj-fg: #ffe2a6; --maj-bd: #e0a630;
    --min-bg: #1d2d43; --min-fg: #cfe0f6; --min-bd: #7fa3cf;
    --ok-bg: #173520; --ok-fg: #bde8c8; --ok-bd: #55b06f;
    --none-bg: #2a2e33; --none-fg: #d6dadf; --none-bd: #8a929c;
    --quote-bg: #252a30;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  overflow-wrap: anywhere; }
.wrap { max-width: 980px; margin: 0 auto; padding: 16px; }
a { color: var(--link); }
h1 { font-size: 1.5rem; line-height: 1.25; margin: 0.2em 0 0.3em; }
h2 { font-size: 1.3rem; margin: 1.6em 0 0.6em; padding-bottom: 0.25em; border-bottom: 1px solid var(--line); }
h3 { font-size: 1.1rem; margin: 1.4em 0 0.5em; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.88em; }
.sub, .legend, .note, .meta { color: var(--muted); }
.sep { color: var(--muted); }
.toc { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
  padding: 6px 0; margin-bottom: 12px; }
.toc ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.92rem; }
.tools { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 6px; font-size: 0.9rem; }
.tools[hidden] { display: none; }
.tools-label { color: var(--muted); }
.tools button { font: inherit; color: var(--fg); background: var(--surface); border: 1px solid var(--line);
  border-radius: 6px; padding: 2px 10px; cursor: pointer; }
.tools button[aria-pressed="true"] { border-color: var(--fg); font-weight: 600; }
.verdict { border: 2px solid var(--none-bd); background: var(--none-bg); color: var(--none-fg);
  border-radius: 10px; padding: 14px 16px; margin: 8px 0 14px; }
.verdict-main .label { display: block; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
.decision { display: block; font-size: 1.9rem; line-height: 1.2; }
.verdict-note { margin: 0.5em 0 0; }
.v-bad { border-color: var(--crit-bd); background: var(--crit-bg); color: var(--crit-fg); }
.v-warn { border-color: var(--maj-bd); background: var(--maj-bg); color: var(--maj-fg); }
.v-ok { border-color: var(--ok-bd); background: var(--ok-bg); color: var(--ok-fg); }
.ready { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 12px 0 0; }
.ready dt { font-size: 0.85rem; }
.ready dd { margin: 0; font-weight: 700; font-size: 1.1rem; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 8px; margin: 0 0 12px; }
.tile { border: 1px solid var(--line); background: var(--surface); border-radius: 8px; padding: 8px 10px; }
.tile b { display: block; font-size: 1.6rem; line-height: 1.1; }
.tile span { font-size: 0.85rem; }
.tile.sev-critical { background: var(--crit-bg); color: var(--crit-fg); border-color: var(--crit-bd); }
.tile.sev-major { background: var(--maj-bg); color: var(--maj-fg); border-color: var(--maj-bd); }
.tile.sev-minor { background: var(--min-bg); color: var(--min-fg); border-color: var(--min-bd); }
.first h2 { font-size: 1.15rem; }
.blockers li, .topq li { margin: 0.35em 0; }
.bid { font-weight: 700; }
.incomplete { border: 2px solid var(--maj-bd); background: var(--maj-bg); color: var(--maj-fg);
  border-radius: 8px; padding: 8px 14px; margin: 8px 0; }
.incomplete a { color: inherit; }
.warn-line { color: var(--crit-fg); }
.table-wrap { overflow-x: auto; margin: 0.6em 0 1em; border: 1px solid var(--line); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid var(--line); }
th { background: var(--surface); }
tbody tr:last-child td { border-bottom: 0; }
table.kv td:first-child { white-space: nowrap; font-weight: 600; }
table.num td:last-child { text-align: center; }
table.seg, table.steps { min-width: 640px; }
table.kv { min-width: 0; }
table.kv td { overflow-wrap: anywhere; }
details { margin: 0.6em 0; }
summary { cursor: pointer; font-weight: 600; }
.st-bad { color: var(--crit-fg); font-weight: 700; }
.st-warn { color: var(--maj-fg); font-weight: 700; }
.req { border-top: 1px solid var(--line); margin-top: 1.4em; padding-top: 0.2em; }
.req h3 { margin-top: 0.8em; }
blockquote.doc, pre.doc { margin: 0.4em 0 0.8em; padding: 8px 12px; background: var(--quote-bg);
  border-left: 3px solid var(--none-bd); border-radius: 4px; }
pre.doc { overflow-x: auto; white-space: pre; }
.checks { line-height: 2; }
.chip, .mark { display: inline-block; border-radius: 4px; padding: 0 6px; font-size: 0.85rem; line-height: 1.5;
  border: 1px solid var(--line); white-space: nowrap; }
.mark { padding: 0 4px; }
.st-pass { background: var(--ok-bg); color: var(--ok-fg); border-color: var(--ok-bd); }
.st-fail { background: var(--crit-bg); color: var(--crit-fg); border-color: var(--crit-bd); }
.st-na { background: var(--none-bg); color: var(--none-fg); }
.st-unknown { background: var(--maj-bg); color: var(--maj-fg); border-color: var(--maj-bd); }
.check-notes { margin: 0.2em 0 0.6em; }
.card { border: 1px solid var(--line); border-left: 5px solid var(--none-bd); border-radius: 8px;
  padding: 10px 14px; margin: 10px 0; background: var(--bg); }
.card[hidden] { display: none; }
.card header { font-weight: 600; margin-bottom: 4px; }
.card p { margin: 0.35em 0; }
.card.sev-critical { border-left-color: var(--crit-bd); }
.card.sev-major { border-left-color: var(--maj-bd); }
.card.sev-minor { border-left-color: var(--min-bd); }
.badge { display: inline-block; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em; border-radius: 4px;
  padding: 1px 7px; border: 1px solid var(--line); }
.badge.sev-critical { background: var(--crit-bg); color: var(--crit-fg); border-color: var(--crit-bd); }
.badge.sev-major { background: var(--maj-bg); color: var(--maj-fg); border-color: var(--maj-bd); }
.badge.sev-minor { background: var(--min-bg); color: var(--min-fg); border-color: var(--min-bd); }
.k { font-weight: 600; }
.quote { background: var(--quote-bg); border-radius: 3px; padding: 0 4px; box-decoration-break: clone;
  -webkit-box-decoration-break: clone; }
.ln { color: var(--muted); white-space: nowrap; }
.ask { background: var(--surface); border-radius: 6px; padding: 6px 8px; }
.rewrite { background: var(--ok-bg); color: var(--ok-fg); border-radius: 6px; padding: 8px 12px; margin: 0.6em 0; }
.qtext { font-weight: 700; font-size: 1.05rem; }
.options li.recommended { font-weight: 600; }
.decision-line { font-size: 1.3rem; }
.decision-line.v-bad { color: var(--crit-fg); }
.decision-line.v-warn { color: var(--maj-fg); }
.decision-line.v-ok { color: var(--ok-fg); }
.removed > li { margin: 0.5em 0; }
.set-fail { color: var(--crit-fg); }
.set-partial { color: var(--maj-fg); }
.set-ok { color: var(--ok-fg); }
.dead { font-weight: inherit; }
[id] { scroll-margin-top: 100px; }
.card:target, .req:target, li:target, span:target, strong:target { outline: 2px solid var(--link); outline-offset: 2px; }
@media (max-width: 600px) {
  .wrap { padding: 12px 16px; }
  h1 { font-size: 1.25rem; }
  .decision { font-size: 1.5rem; }
  .toc { position: static; }
  ul, ol { padding-left: 1.3em; }
}
@media print {
  :root { --bg: #fff; --fg: #000; --muted: #333; --surface: #f3f3f3; --link: #000; }
  body { font-size: 11pt; }
  .toc, .tools { display: none; }
  .wrap { max-width: none; padding: 0; }
  .card, .req h3, blockquote.doc, tr { break-inside: avoid; }
  h2, h3 { break-after: avoid; }
  a { text-decoration: none; }
  .table-wrap { overflow: visible; border: 0; }
  table.seg, table.steps { min-width: 0; }
  pre.doc { white-space: pre-wrap; }
  .card[hidden] { display: block; }
}
"""

# Фильтр по уровню и «развернуть всё». Без скрипта панель скрыта, всё содержимое и ссылки работают.
JS = """
(function () {
  var tools = document.getElementById('tools');
  if (!tools) { return; }
  tools.hidden = false;
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card[data-sev]'));
  var details = Array.prototype.slice.call(document.querySelectorAll('details'));
  var sevButtons = Array.prototype.slice.call(tools.querySelectorAll('button[data-sev]'));
  function filter(sev) {
    cards.forEach(function (c) { c.hidden = !!sev && c.getAttribute('data-sev') !== sev; });
    sevButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-sev') === sev)); });
  }
  tools.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) { return; }
    if (b.hasAttribute('data-sev')) { filter(b.getAttribute('data-sev')); return; }
    var open = b.getAttribute('data-open') !== '1';
    details.forEach(function (d) { d.open = open; });
    b.setAttribute('data-open', open ? '1' : '0');
    b.textContent = open ? 'свернуть всё' : 'развернуть всё';
  });
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#"]');
    if (!a) { return; }
    var t = document.getElementById(a.getAttribute('href').slice(1));
    if (t && (t.hidden || t.closest('[hidden]'))) { filter(''); }
    var d = t && t.closest('details');
    if (d) { d.open = true; }
  });
  window.addEventListener('beforeprint', function () { details.forEach(function (d) { d.open = true; }); filter(''); });
})();
"""
