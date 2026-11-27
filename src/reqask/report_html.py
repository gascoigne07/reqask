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
from .criteria import REQ_CRITERIA, SET_CRITERIA, SET_SECTIONS, SEVERITIES, SEVERITY_RULES
from .grounding import distinct_quotes
from .report import (
    BLOCKER_GROUPS,
    FINDING_STATUS_RU,
    FIRST_SCREEN_BLOCKERS,
    FIRST_SCREEN_BLOCKERS_ALL,
    FIRST_SCREEN_QUESTIONS,
    KIND_RU,
    LIMITS,
    LIMITS_ANCHOR,
    LIMITS_LINK_TEXT,
    LIMITS_TITLE,
    PASS_LABEL,
    PLAIN_TITLE,
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
    segmentation_ids,
)
from .schemas import Evidence, Finding, Question, Requirement, RunResult

# Отметки оценок вместо значков report.md: эмодзи в HTML не используем, смысл тот же.
MARKS = {"pass": "✓", "fail": "✗", "na": "○", "unknown": "?"}
DECISION_CLASS = {"Не рекомендуется начинать": "bad", "Условно допускается": "warn", "Допускается": "ok"}
EVIDENCE_NOTES = {"fuzzy": "восстановлена по близкому совпадению", "missing": "не найдена в документе"}
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
        note = EVIDENCE_NOTES.get(item.status, "")
        note = f", {note}" if note else ""
        return f'<span class="quote">{esc(" ".join(item.quote.split()))}</span>{line}{esc(note)}'

    @staticmethod
    def src(rows: list[tuple[str, str]], label: str = "") -> str:
        """Строки документа как в ревью кода: номер в жёлобе слева, текст справа. Текст уже в HTML."""
        aria = f' role="group" aria-label="{esc(label)}"' if label else ""
        cells = "".join(f'<span class="n">{n}</span><span class="t">{t}</span>' for n, t in rows)
        return f'<div class="src"{aria}>{cells}</div>'

    def evidence_src(self, items: list[Evidence], label: str = "Цитата из документа") -> str:
        """Цитаты замечания одним блоком; у нечёткой и ненайденной цитаты номера нет, пометка текстом."""
        rows = []
        for item in items:
            text = esc(" ".join(item.quote.split()))
            note = EVIDENCE_NOTES.get(item.status, "")
            if note:
                text += f' <span class="src-note">({esc(note)})</span>'
            rows.append((str(item.line) if item.line else "", text))
        return self.src(rows, label)

    def requirement_src(self, x: Requirement) -> str:
        """Текст требования: номер у каждой строки, если строк столько же, сколько в диапазоне; иначе диапазон у первой."""
        lines = x.quote.strip("\n").split("\n") if "\n" in x.quote.strip() else [x.quote.strip()]
        if len(lines) == x.line_end - x.line_start + 1:
            numbers = [str(x.line_start + i) for i in range(len(lines))]
        else:
            first = str(x.line_start) if x.line_end == x.line_start else f"{x.line_start}-{x.line_end}"
            numbers = [first] + [""] * (len(lines) - 1)
        return self.src([(n, esc(t)) for n, t in zip(numbers, lines)], "Текст требования")

    @staticmethod
    def head(ident: str, title: str, level: str = "", cls: str = "", tag: str = "header") -> str:
        """Заголовок записи: идентификатор и уровень в левом поле, название в колонке текста. Всё уже в HTML."""
        lvl = f'<span class="lvl lvl-{cls}">{level}</span>' if level else ""
        return (f'<{tag} class="eh"><span class="gut"><span class="eid">{ident}</span>{lvl}</span>'
                f'<span class="et">{title}</span></{tag}>')

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
        return (f'{self.link(f.id, "bid sev-" + _sev(f))} <span class="li-t">'
                f'<span class="where">{self.where(f)}</span> <span class="sep">·</span> {gist}</span>')

    def section(self, key: str, title: str) -> None:
        self.add(f'<section class="part"{self.tid(key)}>')
        self.add(f"<h2>{esc(title)}</h2>")

    def end(self) -> None:
        self.add("</section>")

    def table(self, head: list[str], rows: list[list[str]], cls: str = "") -> None:
        """Ячейки уже в HTML. Широкая таблица прокручивается внутри своей обёртки.

        У таблиц нарезки и журнала ячейки несут подпись колонки (data-h): на узком экране строка таблицы
        становится записью, и подпись стоит перед значением."""
        labels = cls in ("seg", "steps")
        self.add(f'<div class="table-wrap"><table class="{cls}">')
        self.add("<thead><tr>" + "".join(f'<th scope="col">{h}</th>' for h in head) + "</tr></thead><tbody>")
        for row in rows:
            cells = "".join(
                (f'<td data-h="{head[i]}">' if labels and i < len(head) else "<td>") + f"{c}</td>" for i, c in enumerate(row)
            )
            self.add(f"<tr>{cells}</tr>")
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
        self.add(f'<h1><span class="h1-kind">Отчёт о проверке требований<span class="colon">:</span></span> '
                 f'<span class="h1-doc">{esc(r.document_name)}</span></h1>')
        self.add(
            '<p class="sub">Отчёт сформирован агентом reqask автоматически по ISO/IEC/IEEE 29148:2018 и IEEE 830. '
            f"Модель: {esc(r.model)}. Дата: {esc(r.started_at)}.</p>"
        )
        self.add("</header>")
        self.toc()
        self.add('<main class="doc">')
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
        stats = [
            ("reqs", len(self.reqs), "Требований"),
            ("with-defects", with_defects, "с дефектами"),
            *((s.lower(), sev.get(s, 0), s) for s in SEVERITIES),
            ("questions", len(r.questions), "Вопросов автору"),
        ]
        self.add('<div class="stats">')
        for key, value, label in stats:
            hot = " hot" if key == "critical" and value else ""
            self.add(f'<div class="stat{hot}" data-k="{key}"><b>{value}</b><span>{esc(label)}</span></div>')
        self.add("</div>")
        lost = [f for f in self.inactive if f.severity == "CRITICAL" and f.status in ("quarantine", "question_only")]
        if lost:
            self.add(f'<p class="warn-line">{len(lost)} критичных замечаний не подтверждены цитатой, '
                     'см. <a href="#appendix-b">приложение Б</a>.</p>')
        self.add(f'<p>{esc(LIMITS_LINK_TEXT)} <a href="#{LIMITS_ANCHOR}">раздел 6</a>.</p>')
        if v.blockers:
            self.add("<h2>Блокеры</h2>")
            rows = self._blocker_rows()
            shown = len(rows) if len(rows) <= FIRST_SCREEN_BLOCKERS_ALL else FIRST_SCREEN_BLOCKERS
            self.add('<ul class="blockers idlist">')
            for f, joined in rows[:shown]:
                self.add(f"<li>{self.blocker_line(f, joined)}</li>")
            rest = len(rows) - shown
            if rest > 0:
                self.add(f'<li>и ещё {rest}, полный список в <a href="#summary">разделе 5</a></li>')
            self.add("</ul>")
        if r.questions:
            self.add("<h2>Главные вопросы автору ТЗ</h2>")
            self.add('<ul class="topq idlist">')
            for q in r.questions[:FIRST_SCREEN_QUESTIONS]:
                self.add(f'<li>{self.link(q.id, "qid")} <span class="li-t"><span class="where">'
                         f"{esc(_addressee(q.addressee))}:</span> {esc(_one_line(q.text, 220))}</span></li>")
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
        self.add(
            f"<p>Выделено требований: <strong>{len(r.requirements)}</strong>. {esc(segmentation_ids(r))} "
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
            for s, t in (("pass", PASS_LABEL), ("fail", "нарушен"), ("na", "не применим"), ("unknown", "нельзя оценить по тексту"))
        )
        self.add(
            f'<p class="legend">Отметки: {legend}. Шесть основных критериев показаны всегда, '
            "уместность уровня, атомарность и корректность только при нарушении.</p>"
        )
        g = self._groups()
        quiet, moved, noted, touched, plain, set_refs = (
            g["quiet"], g["moved"], g["noted"], g["touched"], g["plain"], g["set_refs"])
        if plain:
            items = ", ".join(f"<span{self.tid(x.id)}>{esc(x.id)} ({_lines(x.line_start, x.line_end)})</span>" for x in plain)
            self.add(f'<p class="plain"><strong>{PLAIN_TITLE} ({len(plain)}):</strong> {items}.</p>')
        if touched:
            self.add(f"<p><strong>Своих замечаний нет, но требование затронуто общими замечаниями ({len(touched)}):</strong></p><ul>")
            for x in touched:
                self.add(f"<li><strong{self.tid(x.id)}>{esc(self._req_head(x))}</strong>: {self.links(set_refs[x.id])}.</li>")
            self.add("</ul>")
        for title, group in (
            ("Дефект описан в общем замечании, на которое ссылается строка", moved),
            ("Замечаний не найдено, есть пометки к оценкам", noted),
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
        head = self._req_head(x)
        rest = head[len(x.id):].removeprefix(" · ") if head.startswith(x.id) else head
        self.add(self.head(esc(x.id), esc(rest), tag="h3"))
        self.add(self.requirement_src(x))
        if x.id in r.unreviewed:
            self.add("<p>Требование не проверено: модель не вернула по нему результат.</p></section>")
            return
        shown = [f for f in self.req_findings.get(x.id, []) if _active(f)]
        visible, st = self._statuses(x)
        checks = " ".join(
            f'<span class="ck st-{st["statuses"][c.code]}" title="{esc(c.name)}: {esc(STATUS_RU[st["statuses"][c.code]])}">'
            f'{MARKS[st["statuses"][c.code]]} {esc(c.short)}</span>'
            for c in visible
        )
        self.add(f'<p class="checks"><span class="k">Оценки:</span> {checks}</p>')
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
        return self.head(esc(f.id), esc(title), esc(f.severity), _sev(f))

    def defect(self, f: Finding) -> None:
        self.add(f'<article class="entry sev-{_sev(f)}" data-sev="{_sev(f)}"{self.tid(f.id)}>')
        self.add(self.card_head(f, _criterion(f.criterion)))
        self.add(f'<p class="problem">{esc(f.problem)}</p>')
        found = md._found(f.evidence)
        if found:
            self.add(self.evidence_src(found))
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
        self.add(f'<article class="entry sev-{_sev(f)}" data-sev="{_sev(f)}"{self.tid(f.id)}>')
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
            self.add(self.evidence_src(found, "Цитата из документа" if len(found) == 1 else "Цитаты из документа"))
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
        rows = self.summary_rows()
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
        self.add(f"<h3{self.tid(LIMITS_ANCHOR)}>{esc(LIMITS_TITLE)}</h3><ul>")
        for item in LIMITS:
            self.add(f"<li>{esc(item)}</li>")
        self.add("</ul>")
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
        self.add(f'<article class="entry q sev-{cls}"{self.tid(q.id)}>')
        self.add(self.head(esc(q.id), f'{esc(_addressee(q.addressee))} <span class="sep">·</span> '
                                      f'<span class="lvl lvl-{cls}">{esc(label)}</span>'))
        self.add(f'<p class="qtext">{esc(q.text)}</p>')
        self.add(self.question_body(q))
        self.add(f'<p class="note">Закрывает замечания: {self.links(q.finding_ids)}.</p>')
        self.add("</article>")

    def question_body(self, q: Question) -> str:
        """То же, что report._question_body, в HTML."""
        rows: list[str] = []
        quotes = distinct_quotes(q.quotes)
        if quotes:
            rows.append('<p class="k k-block">Сейчас в документе:</p>' + self.evidence_src(quotes, "Сейчас в документе"))
            if q.doc_says and not _repeats_quotes(q.doc_says, quotes):
                rows.append(f'<p><span class="k">Суть:</span> {esc(q.doc_says)}</p>')
        elif q.doc_says:
            rows.append(f'<p><span class="k">Сейчас в документе:</span> {esc(q.doc_says)}</p>')
        else:
            rows.append('<p><span class="k">Сейчас в документе:</span> не описано.</p>')
        if q.options:
            rows.append('<p class="k k-block">Варианты:</p><ol class="options">')
            for number, option in enumerate(q.options, start=1):
                chosen = q.recommended == number
                rec = ' class="recommended"' if chosen else ""
                mark = ' <span class="rec-mark">рекомендуем</span>' if chosen else ""
                rows.append(f"<li{rec}><span class=\"ans\">{esc(option.answer.rstrip('.'))}.</span>{mark} "
                            f'<span class="cons"><span class="k">Последствие:</span> '
                            f"{esc(_no_dot(_sentence_case(option.consequence)))}.</span></li>")
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
            item = (f'<li{self.tid(f.id)}><span class="lvl lvl-{_sev(f)}">{esc(f.severity)}</span> '
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
            f"<title>{title}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<div class=\"page\">\n"
            f"{body}\n</main>\n</div>\n<script>{JS}</script>\n</body>\n</html>\n"
        )


def render_html(result: RunResult) -> str:
    return _Html(result).render()


CSS = """
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #1a1b1d; --muted: #5b6066; --ln: #6c7178; --rule: #dadcdf; --strong: #1a1b1d;
  --quote-bg: #f5f5f2; --link: #1f4e8c; --crit: #b42318; --major: #8a5300; --mark: #fff0b3;
  --serif: Charter, "Bitstream Charter", "Sitka Text", Cambria, Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  --measure: 37em; --gutter: 0px; --gap: 1.25rem;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161719; --fg: #e6e4e0; --muted: #a6aab0; --ln: #8f949b; --rule: #34373b; --strong: #e6e4e0;
    --quote-bg: #212326; --link: #93bbf5; --crit: #ff8b7e; --major: #e3ad52; --mark: #4d4214;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 17px/1.58 var(--serif);
  font-kerning: normal; overflow-wrap: break-word; }
a { color: var(--link); text-decoration-thickness: 1px; text-underline-offset: 0.16em; }
.doc a[href^="#"] { white-space: nowrap; }
a:focus-visible, button:focus-visible, summary:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; }
code { font: 0.84em var(--mono); overflow-wrap: anywhere; }
p, ul, ol { margin: 0.55em 0; }
ul, ol { padding-left: 1.35em; }
li { margin: 0.25em 0; }

/* раскладка: узкий экран по умолчанию */
.page { padding: 0 16px 3rem; max-width: calc(var(--measure) + 32px); margin: 0 auto; }
.doc-head { padding: 1.8rem 0 0.6rem; }
h1 { font: 600 1.6rem/1.2 var(--serif); margin: 0 0 0.5rem; letter-spacing: -0.005em; }
.h1-kind { display: block; font: 600 0.72rem/1.4 var(--sans); letter-spacing: 0.09em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 0.45rem; }
.colon { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.h1-doc { overflow-wrap: anywhere; }
.sub { font: 0.82rem/1.5 var(--sans); color: var(--muted); margin: 0; }

.toc { font: 0.86rem/1.4 var(--sans); border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
  padding: 0.6rem 0; margin: 1.2rem 0 0.4rem; }
.toc ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.15rem 1rem; }
.toc li { margin: 0; }
.toc a { color: var(--fg); text-decoration: none; display: inline-block; padding: 0.2rem 0; }
.toc a:hover { color: var(--link); text-decoration: underline; }
.tools { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 0.95rem; margin-top: 0.4rem; }
.tools[hidden] { display: none; }
.tools-label { color: var(--muted); }
.tools button { font: inherit; color: var(--link); background: none; border: 0; padding: 0.3rem 0; cursor: pointer;
  text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
.tools button[aria-pressed="true"] { color: var(--fg); font-weight: 700; text-decoration: none; }

/* заголовки */
h2 { font: 600 1.45rem/1.25 var(--serif); margin: 3rem 0 0.9rem; padding-top: 0.55rem;
  border-top: 1px solid var(--strong); }
h3 { font: 600 1.14rem/1.35 var(--serif); margin: 2rem 0 0.5rem; }
.first h2 { font: 600 0.72rem/1.4 var(--sans); letter-spacing: 0.09em; text-transform: uppercase;
  border: 0; padding: 0; margin: 2rem 0 0.4rem; }

/* вердикт и числа */
.verdict { --v: var(--muted); border-top: 4px solid var(--v); padding-top: 0.75rem; margin: 1.4rem 0 1.6rem; }
.v-bad { --v: var(--crit); } .v-warn { --v: var(--major); } .v-ok { --v: var(--fg); }
.verdict .label { display: block; font: 600 0.72rem/1.4 var(--sans); letter-spacing: 0.09em;
  text-transform: uppercase; color: var(--muted); }
.decision { display: block; font: 600 2.1rem/1.12 var(--serif); color: var(--v); margin: 0.2rem 0 0.5rem;
  letter-spacing: -0.012em; text-wrap: balance; }
.verdict-note { margin: 0.3rem 0; color: var(--muted); }
.ready { font: 0.88rem/1.5 var(--sans); display: flex; flex-wrap: wrap; gap: 0.1rem 1.6rem; margin: 0.5rem 0 0; }
.ready div { display: flex; gap: 0.35em; }
.ready dt::after { content: ":"; }
.ready dd { margin: 0; font-weight: 700; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem 0.75rem; margin: 0 0 1.4rem; }
.stat b { display: block; font: 600 1.85rem/1.05 var(--serif); font-variant-numeric: lining-nums tabular-nums; }
.stat span { display: block; font: 0.74rem/1.3 var(--sans); color: var(--muted); margin-top: 0.25rem; }
.stat.hot b { color: var(--crit); }
.incomplete { border-top: 2px solid var(--major); border-bottom: 1px solid var(--rule); padding: 0.5rem 0;
  margin: 1.2rem 0 0; }
.incomplete strong { color: var(--major); }
.incomplete a { color: inherit; }
.warn-line { color: var(--crit); }

/* списки с идентификатором в поле */
.idlist { list-style: none; padding: 0; margin: 0.3rem 0 1rem; }
.idlist > li { position: relative; margin: 0; padding: 0.5rem 0 0.5rem 3.7rem; border-top: 1px solid var(--rule); }
.idlist > li > .bid, .idlist > li > .qid { position: absolute; left: 0; top: 0.72rem; }
.bid, .qid, .eid { font: 600 0.8rem/1.3 var(--mono); font-variant-numeric: tabular-nums; letter-spacing: 0; white-space: nowrap; }
.idlist a.bid, .idlist a.qid { text-decoration: none; }
.bid.sev-critical { color: var(--crit); }
.idlist .qid { color: var(--fg); }
.entry a.qid, p a.qid { font: inherit; }
.where { font-family: var(--sans); font-size: 0.86em; color: var(--muted); }
.sep { color: var(--muted); }
ol.blockers li { margin: 0.4rem 0; }

/* записи: замечания, требования, вопросы */
.entry { position: relative; border-top: 1px solid var(--rule); padding: 0.95rem 0 1rem; }
.entry[hidden] { display: none; }
.entry > p { margin: 0.4em 0; }
.eh { position: relative; display: block; font: 600 1rem/1.45 var(--serif); margin: 0 0 0.3rem; }
.gut { display: inline; margin-right: 0.15em; }
.gut .eid { margin-right: 0.55em; }
.lvl { font: 700 0.68rem/1.3 var(--sans); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
  white-space: nowrap; }
.gut .lvl { margin-right: 0.6em; }
.lvl-critical { color: var(--crit); }
.lvl-major { color: var(--major); }
.req { margin-top: 2.6rem; }
.req > .eh { font-size: 1.08rem; border-top: 1px solid var(--strong); padding-top: 0.55rem; margin: 0 0 0.6rem; }
.req > .eh .et { font-weight: 600; }
.k { font: 600 0.7rem/1.4 var(--sans); letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted);
  margin-right: 0.3em; }
p.k-block { margin: 0.8em 0 0.25em; }
.problem { font-weight: 400; }
.note, .meta, .moved, .legend { font: 0.84rem/1.5 var(--sans); color: var(--muted); }
.checks { font: 0.84rem/1.7 var(--sans); margin: 0.6rem 0; }
.ck { white-space: nowrap; margin-right: 0.85em; color: var(--muted); }
.st-fail { color: var(--crit); font-weight: 700; }
.st-unknown { color: var(--major); font-weight: 700; }
.mark { font-family: var(--sans); }
.mark.st-pass, .mark.st-na { color: var(--muted); }
.check-notes { font-size: 0.94em; }
.rewrite { background: var(--quote-bg); padding: 0.65rem 0.95rem; margin: 0.4rem 0 0.4rem; }
.rewrite strong { display: block; font: 600 0.7rem/1.4 var(--sans); letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 0.2rem; }
.q .eid { font-size: 1.05rem; color: var(--fg); }
.q .eh { font: 0.86rem/1.6 var(--sans); color: var(--muted); }
.q .eh .lvl { font-size: 0.66rem; }
.qtext { font-weight: 700; margin-top: 0.2rem; }
ol.options { padding-left: 1.5em; margin: 0.2em 0 0.6em; }
ol.options li { margin: 0.45em 0; }
ol.options li::marker { font: 600 0.85em var(--sans); color: var(--muted); }
.cons { display: block; color: var(--muted); font-size: 0.94em; }
.cons .k { color: inherit; }
.rec-mark { font: 700 0.66rem/1 var(--sans); letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg);
  border-bottom: 1px solid currentColor; margin-left: 0.25em; white-space: nowrap; }

/* строки документа: номер в жёлобе, текст справа */
.src { display: grid; grid-template-columns: max-content minmax(0, 1fr); align-items: baseline;
  background: var(--quote-bg); margin: 0.6em 0 0.8em; padding: 0.4rem 0; font-size: 0.94em; line-height: 1.5; }
.src .n { font: 0.72rem/1.5 var(--mono); font-variant-numeric: tabular-nums; color: var(--ln); text-align: right;
  min-width: 2.1rem; padding: 0.1rem 0.5rem 0.1rem 0.5rem; border-right: 1px solid var(--rule);
  align-self: stretch; -webkit-user-select: none; user-select: none; }
.src .t { white-space: pre-wrap; overflow-wrap: anywhere; padding: 0.1rem 0.9rem; min-width: 0; }
.src-note { font: 0.8rem var(--sans); color: var(--muted); white-space: normal; }
.quote { background: var(--quote-bg); padding: 0 0.2em; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.ln { font: 0.8em var(--mono); color: var(--ln); white-space: nowrap; }

/* таблицы: только линейки */
.table-wrap { margin: 0.7rem 0 1.3rem; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font: 0.84rem/1.45 var(--sans); font-variant-numeric: tabular-nums; }
th { font: 600 0.68rem/1.4 var(--sans); letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted);
  text-align: left; vertical-align: bottom; padding: 0.35rem 0.9rem 0.35rem 0; border-bottom: 1px solid var(--strong); }
td { text-align: left; vertical-align: top; padding: 0.45rem 0.9rem 0.45rem 0; border-bottom: 1px solid var(--rule); }
th:last-child, td:last-child { padding-right: 0; }
table.kv td:first-child { white-space: nowrap; color: var(--muted); }
table.kv th:first-child { width: 11.5em; }
table.steps td:nth-child(2) { min-width: 9.5em; }
table.num td:last-child, table.num th:last-child { text-align: right; }
table.steps td:nth-child(1), table.steps td:nth-child(3), table.steps td:nth-child(4), table.steps td:nth-child(5),
table.steps th:nth-child(1), table.steps th:nth-child(3), table.steps th:nth-child(4), table.steps th:nth-child(5),
table.seg td:nth-child(1), table.seg td:nth-child(2), table.seg td:nth-child(4),
table.seg th:nth-child(1), table.seg th:nth-child(2), table.seg th:nth-child(4) { white-space: nowrap; }
table.steps td:nth-child(4), table.steps td:nth-child(5), table.steps th:nth-child(4), table.steps th:nth-child(5) {
  text-align: right; }
table.steps td:nth-child(1), table.seg td:nth-child(1) { font-family: var(--mono); font-size: 0.95em; }
.st-bad { color: var(--crit); font-weight: 700; }
.st-warn { color: var(--major); font-weight: 700; }
details { margin: 0.7rem 0; }
summary { cursor: pointer; font: 600 0.86rem/1.5 var(--sans); padding: 0.25rem 0; }
.set-fail { color: var(--crit); }
.set-partial { color: var(--major); }
.removed { list-style: none; padding: 0; }
.removed > li { margin: 0; padding: 0.6rem 0; border-top: 1px solid var(--rule); }
.removed > li > ul { font-size: 0.94em; }
.decision-line { font-size: 1.3rem; }
.decision-line.v-bad { color: var(--crit); }
.decision-line.v-warn { color: var(--major); }
.rule { color: var(--muted); }
.dead { font-weight: inherit; }

/* переход по ссылке */
[id] { scroll-margin-top: 1rem; }
.entry:target > .eh .eid, .req:target > .eh .eid { background: var(--fg); color: var(--bg); padding: 0 0.3em; }
li:target, span:target, strong:target { background: var(--mark); }

/* узкий экран: строки нарезки и журнала становятся записями */
@media (max-width: 639px) {
  table.seg, table.steps, table.seg tbody, table.steps tbody { display: block; }
  table.seg thead, table.steps thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  table.seg tr, table.steps tr { display: block; padding: 0.5rem 0; border-bottom: 1px solid var(--rule); }
  table.seg td, table.steps td { display: inline; padding: 0; border: 0; white-space: normal; }
  table.seg td:nth-child(-n+2), table.steps td:nth-child(-n+2) { margin-right: 0.5em; }
  table.seg td:nth-child(2) { color: var(--muted); }
  table.seg td:nth-child(3), table.seg td:nth-child(5), table.steps td:nth-child(2), table.steps td:last-child { display: block; }
  table.seg td:nth-child(3) { color: var(--muted); }
  table.steps td:nth-child(2) { display: inline; font-weight: 600; }
  table.steps td:nth-child(2)::after { content: "\\A"; white-space: pre; }
  table.steps td:nth-child(3) { margin-right: 0.9em; }
  table.seg td:nth-child(4)::before, table.steps td:nth-child(4)::before, table.steps td:nth-child(5)::before {
    content: attr(data-h) ": "; color: var(--muted); }
  table.steps td:nth-child(4), table.steps td:nth-child(5) { margin-right: 0.9em; }
  table.kv:not(.num), table.kv:not(.num) thead, table.kv:not(.num) tbody, table.kv:not(.num) tr,
  table.kv:not(.num) td { display: block; }
  table.kv:not(.num) th { display: none; }
  table.kv:not(.num) th:first-child { display: block; width: auto; }
  table.kv:not(.num) td { border: 0; padding: 0; }
  table.kv:not(.num) td:first-child { white-space: normal; font-size: 0.92em; padding-top: 0.5rem; }
  table.kv:not(.num) td:last-child { padding-bottom: 0.5rem; border-bottom: 1px solid var(--rule); }
}

/* широкий экран: идентификаторы висят в левом поле */
@media (min-width: 800px) {
  :root { --gutter: 7rem; }
  .page { max-width: calc(var(--measure) + var(--gutter) + 4rem); padding: 0 2rem 4rem; }
  .doc-head, .doc, .toc { margin-left: var(--gutter); }
  .doc { max-width: var(--measure); }
  .doc-head { padding-top: 3rem; max-width: var(--measure); }
  h1 { font-size: 2rem; }
  .part > h2 { margin-left: calc(-1 * var(--gutter)); padding-left: var(--gutter); }
  .req > .eh { margin-left: calc(-1 * var(--gutter)); padding-left: var(--gutter); }
  .gut { position: absolute; right: calc(100% + var(--gap)); top: 0.1rem; width: calc(var(--gutter) - var(--gap));
    display: flex; flex-direction: column; align-items: flex-end; gap: 0.15rem; margin: 0; text-align: right; }
  .req > .eh > .gut { right: calc(100% - var(--gutter) + var(--gap)); top: 0.62rem; }
  .gut .eid, .gut .lvl { margin: 0; }
  .q .eh .gut { top: -0.05rem; }
  .idlist > li { padding-left: 0; }
  .idlist > li > .bid, .idlist > li > .qid { left: auto; right: calc(100% + var(--gap)); top: 0.68rem; }
  .decision { font-size: 2.5rem; }
  .src .n { min-width: 2.7rem; padding: 0.1rem 0.65rem 0.1rem 0.7rem; }
  .stats { display: flex; flex-wrap: wrap; gap: 0.8rem 0; }
  .stat { padding: 0 1.15rem; border-left: 1px solid var(--rule); }
  .stat:first-child { padding-left: 0; border-left: 0; }
  .stat b { font-size: 2rem; }
}

/* от 1100 px: оглавление слева, липкое */
@media (min-width: 1100px) {
  .page { display: grid; grid-template-columns: 12rem minmax(0, calc(var(--gutter) + var(--measure)));
    grid-template-rows: auto 1fr; column-gap: 2rem; justify-content: center; max-width: none; }
  .doc-head { grid-column: 2; grid-row: 1; }
  .doc { grid-column: 2; grid-row: 2; }
  .toc { grid-column: 1; grid-row: 1 / span 2; align-self: start; position: sticky; top: 0; max-height: 100vh;
    overflow-y: auto; margin: 0; padding: 3.3rem 0 2rem; border: 0; }
  .toc ul { display: block; }
  .toc li { border-top: 1px solid var(--rule); }
  .toc li:first-child { border-top: 1px solid var(--strong); }
  .toc a { display: block; padding: 0.32rem 0; }
  .tools { flex-direction: column; align-items: flex-start; gap: 0; margin-top: 1.4rem; padding-top: 0.5rem;
    border-top: 1px solid var(--strong); }
  .tools-label { padding: 0.3rem 0 0.1rem; }
  .tools button { padding: 0.18rem 0; }
}

@media print {
  :root { --bg: #fff; --fg: #000; --muted: #444; --ln: #555; --rule: #bbb; --strong: #000; --quote-bg: #f2f2f0;
    --link: #000; --crit: #a3150b; --major: #6b4000; --mark: transparent; --gutter: 6rem; }
  @page { margin: 16mm 14mm; }
  body { font-size: 10.5pt; }
  .toc, .tools { display: none; }
  .page { display: block; max-width: none; padding: 0; }
  .doc-head, .doc { margin-left: var(--gutter); max-width: none; padding-top: 0; }
  a { color: inherit; text-decoration: none; }
  .entry, .src, tr, .verdict, .stats, .idlist > li, .removed > li { break-inside: avoid; }
  h2, h3, .eh, p.k-block { break-after: avoid; }
  .entry[hidden] { display: block; }
  .table-wrap { overflow: visible; }
  details::details-content { content-visibility: visible; display: contents; }
  .entry:target > .eh .eid, .req:target > .eh .eid { background: none; color: inherit; padding: 0; }
}
"""

# Фильтр по уровню и «развернуть всё». Без скрипта панель скрыта, всё содержимое и ссылки работают.
JS = """
(function () {
  var tools = document.getElementById('tools');
  if (!tools) { return; }
  tools.hidden = false;
  var entries = Array.prototype.slice.call(document.querySelectorAll('.entry[data-sev]'));
  var details = Array.prototype.slice.call(document.querySelectorAll('details'));
  var sevButtons = Array.prototype.slice.call(tools.querySelectorAll('button[data-sev]'));
  function filter(sev) {
    entries.forEach(function (c) { c.hidden = !!sev && c.getAttribute('data-sev') !== sev; });
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
