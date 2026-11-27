"""Сравнение двух прогонов по report.json, без модели: reqask --compare OLD.json NEW.json --output diff.md.

Номера D-xx, S-xx и REQ-xx в каждом прогоне свои, а номера строк сдвигаются, если документ правили.
Поэтому замечания сопоставляются кодом по содержанию:

- общая цитата: нормализованный текст цитаты одного замечания совпадает с цитатой другого или содержит её;
- то же требование и тот же критерий: требование узнаётся по идентификатору из документа (вида «ФТ-3»)
  или по совпадающему тексту требования.

Пара складывается из самых похожих замечаний, каждое замечание входит не больше чем в одну пару.
Код не знает, почему замечания нет в новом отчёте: автор поправил документ, модель ответила иначе
или сопоставление не узнало переписанное место. Поэтому в выводе нет слова «исправлено».
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .criteria import SEVERITIES
from .grounding import normalize
from .report import _gist, _one_line, when
from .schemas import INACTIVE_STATUSES, Finding, RunResult

# Короче этого цитата не считается общей при частичном совпадении: «GET» или «200» есть в десятке мест.
MIN_PART = 15
# Доля общих основ слов в заголовке и описании (0..1), при которой пара складывается: с одной общей цитатой
# и без общей цитаты (тогда нужен ещё тот же критерий). Подобрано на двух прогонах по одному документу.
MIN_WORDS_WITH_QUOTE = 0.1
MIN_WORDS_WITHOUT_QUOTE = 0.25
_LETTER_ID_RE = re.compile(r"[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё]{0,7}-\d+(?:\.\d+)*")

METHOD = (
    "Замечания сопоставлены кодом по содержанию, без модели. Общая цитата: нормализованный текст цитаты совпадает "
    "или одна цитата содержит другую (не короче {n} знаков). Пара складывается, если общих цитат две и больше; "
    "если общая цитата одна и у описаний есть общие слова (доля общих основ слов не меньше {w1}); "
    "или без общей цитаты, если совпадает критерий, требование (по идентификатору из документа или по тексту "
    "требования) и описания похожи сильнее (доля не меньше {w2}). Каждое замечание входит не больше чем в одну пару, "
    "первыми складываются самые похожие. Номера D-xx, S-xx, REQ-xx и номера строк в сопоставлении не участвуют. "
    "«Нет в новом отчёте» значит только, что код не нашёл похожего замечания: причиной может быть правка документа, "
    "разброс модели между прогонами или переписанное описание. Пары можно проверить глазами: у каждой "
    "стоят оба описания."
).format(n=MIN_PART, w1=str(MIN_WORDS_WITH_QUOTE).replace(".", ","), w2=str(MIN_WORDS_WITHOUT_QUOTE).replace(".", ","))
SAME_DOC = "Документ тот же (SHA-256 совпадает): разница показывает разброс между прогонами, а не правки документа."
OTHER_DOC = "Документы разные (SHA-256 не совпадает): разница складывается из правок документа и разброса модели."


@dataclass
class _Item:
    f: Finding
    blocker: bool
    quotes: list[str]
    reqs: set[str] = field(default_factory=set)
    words: set[str] = field(default_factory=set)
    originals: dict[str, str] = field(default_factory=dict)  # нормализованная цитата -> как в отчёте


@dataclass
class Pair:
    old: Finding
    new: Finding
    old_blocker: bool
    new_blocker: bool
    shared: str | None  # общая цитата, если пара сложилась по ней


@dataclass
class Comparison:
    old: RunResult
    new: RunResult
    pairs: list[Pair]
    gone: list[tuple[Finding, bool, str]]  # замечание старого отчёта, блокер ли, пометка про новый отчёт
    added: list[tuple[Finding, bool]]

    @property
    def same_document(self) -> bool:
        return bool(self.old.document_sha256) and self.old.document_sha256 == self.new.document_sha256


def _req_keys(result: RunResult) -> dict[str, str]:
    """REQ-xx прогона -> ключ требования, общий для двух прогонов: идентификатор из документа или текст."""
    keys = {}
    for r in result.requirements:
        sid = (r.source_id or "").strip()
        keys[r.id] = f"id:{sid}" if _LETTER_ID_RE.fullmatch(sid) else f"text:{normalize(r.quote)}"
    return keys


def _items(result: RunResult, active: bool) -> list[_Item]:
    keys = _req_keys(result)
    blockers = set(result.verdict.blockers)
    out = []
    for f in result.findings:
        if (f.status not in INACTIVE_STATUSES) != active:
            continue
        originals = {normalize(e.quote): " ".join(e.quote.split()) for e in reversed(f.evidence)}
        quotes = list(dict.fromkeys(q for q in (normalize(e.quote) for e in f.evidence) if q))
        out.append(_Item(f, f.id in blockers, quotes, {keys[i] for i in f.req_ids if i in keys}, _stems(f), originals))
    return out


def _stems(f: Finding) -> set[str]:
    """Основы слов заголовка и описания: первые пять букв слов длиннее трёх букв."""
    text = normalize(f"{f.title} {f.problem}")
    return {w[:5] for w in re.findall(r"[a-zа-яё0-9]+", text) if len(w) > 3}


def _same_quote(a: str, b: str) -> bool:
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= MIN_PART and short in long_


def _shared(a: _Item, b: _Item) -> list[str]:
    return [qa for qa in a.quotes if any(_same_quote(qa, qb) for qb in b.quotes)]


def _score(a: _Item, b: _Item) -> tuple[float, str | None] | None:
    """Похожесть пары или None, если общего нет: ни цитаты, ни того же требования с тем же критерием."""
    shared = _shared(a, b)
    same_req = bool(a.reqs & b.reqs)
    same_criterion = a.f.criterion == b.f.criterion
    # Похожесть слов описания: одну строку документа часто цитируют замечания о разном.
    words = len(a.words & b.words) / len(a.words | b.words) if a.words and b.words else 0.0
    by_quote = (len(shared) >= 2) or (shared and words >= MIN_WORDS_WITH_QUOTE)
    # Без общей цитаты: тот же критерий и похожее описание. У замечаний к требованию ещё и то же требование;
    # замечание по набору ссылается на много требований, поэтому для него это условие ничего не даёт.
    same_place = same_req if a.f.scope == b.f.scope == "requirement" else a.f.scope == b.f.scope
    by_text = same_criterion and same_place and words >= MIN_WORDS_WITHOUT_QUOTE
    if not (by_quote or by_text):
        return None
    # Доля общих цитат, а не их число: замечание с десятью цитатами не должно забирать себе все пары.
    share = len(shared) / max(len(a.quotes), len(b.quotes)) if shared else 0.0
    score = 3 * share + 4 * words + (1 if shared else 0) + same_criterion + (a.f.scope == b.f.scope) + same_req
    return score, (a.originals.get(shared[0], shared[0]) if shared else None)


def _match(old: list[_Item], new: list[_Item]) -> list[tuple[_Item, _Item, str | None]]:
    candidates = []
    for i, a in enumerate(old):
        for j, b in enumerate(new):
            s = _score(a, b)
            if s:
                candidates.append((-s[0], i, j, s[1]))
    candidates.sort()
    used_old, used_new, pairs = set(), set(), []
    for _, i, j, shared in candidates:
        if i in used_old or j in used_new:
            continue
        used_old.add(i)
        used_new.add(j)
        pairs.append((old[i], new[j], shared))
    pairs.sort(key=lambda p: old.index(p[0]))
    return pairs


def compare(old: RunResult, new: RunResult) -> Comparison:
    old_items, new_items = _items(old, True), _items(new, True)
    matched = _match(old_items, new_items)
    pairs = [Pair(a.f, b.f, a.blocker, b.blocker, shared) for a, b, shared in matched]
    paired_old = {id(a) for a, _, _ in matched}
    paired_new = {id(b) for _, b, _ in matched}
    # Замечание старого отчёта может найтись в новом среди слитых или снятых критиком: это стоит показать.
    new_inactive = _items(new, False)
    gone = []
    for a in old_items:
        if id(a) in paired_old:
            continue
        note = ""
        hit = next((b for b in new_inactive if _score(a, b)), None)
        if hit:
            if hit.f.status == "merged" and hit.f.merged_into:
                note = f"в новом отчёте похожее {hit.f.id} слито в {hit.f.merged_into}"
            else:
                note = f"в новом отчёте похожее {hit.f.id}: {_STATUS_RU.get(hit.f.status, hit.f.status)}"
        gone.append((a.f, a.blocker, note))
    added = [(b.f, b.blocker) for b in new_items if id(b) not in paired_new]
    return Comparison(old, new, pairs, gone, added)


_STATUS_RU = {"dropped": "снято критиком", "quarantine": "цитата не найдена", "question_only": "оставлен только вопрос"}


# ---------- вывод ----------


def _counts(result: RunResult) -> Counter:
    return Counter(f.severity for f in result.findings if f.status not in INACTIVE_STATUSES)


def _where(f: Finding, result: RunResult) -> str:
    reqs = {r.id: r for r in result.requirements}
    names = []
    for rid in f.req_ids:
        r = reqs.get(rid)
        if r:
            names.append(f"{rid} ({r.source_id})" if r.source_id and _LETTER_ID_RE.fullmatch(r.source_id.strip()) else rid)
    return ", ".join(names) if names else ("набор" if f.scope == "set" else "без требования")


def _lines(f: Finding) -> str:
    lines = sorted({e.line for e in f.evidence if e.line})
    return f", строки {', '.join(map(str, lines))}" if lines else ""


def _one(f: Finding, result: RunResult) -> str:
    return f"{f.id} [{f.severity}] · {_where(f, result)}{_lines(f)} · {_gist(f, 160).rstrip('.')}"


def _pair_line(p: Pair, c: Comparison) -> str:
    level = p.old.severity if p.old.severity == p.new.severity else f"{p.old.severity} -> {p.new.severity}"
    by = f" · общая цитата: `{_one_line(p.shared, 90)}`" if p.shared else " · то же требование и критерий"
    was, now = _gist(p.old, 140).rstrip("."), _gist(p.new, 140).rstrip(".")
    text = now if normalize(was) == normalize(now) else f"стало: {now}; было: {was}"
    return f"{p.old.id} -> {p.new.id} [{level}] · {_where(p.new, c.new)} · {text}{by}"


def _parts(c: Comparison):
    blockers_kept = [p for p in c.pairs if p.old_blocker and p.new_blocker]
    blockers_gone = [(p.old, f"в новом отчёте {p.new.id} [{p.new.severity}], не блокер") for p in c.pairs
                     if p.old_blocker and not p.new_blocker] + [(f, n) for f, b, n in c.gone if b]
    blockers_new = [(p.new, f"в старом отчёте {p.old.id} [{p.old.severity}], не блокер") for p in c.pairs
                    if p.new_blocker and not p.old_blocker] + [(f, "") for f, b in c.added if b]
    other_kept = [p for p in c.pairs if not p.old_blocker and not p.new_blocker]
    other_gone = [(f, n) for f, b, n in c.gone if not b]
    other_new = [(f, "") for f, b in c.added if not b]
    return blockers_kept, blockers_gone, blockers_new, other_kept, other_gone, other_new


def summary_lines(c: Comparison) -> list[str]:
    """Короткая сводка для консоли (и начало Markdown)."""
    o, n = c.old, c.new
    so, sn = _counts(o), _counts(n)
    bk, bg, bn, ok, og, on = _parts(c)
    lines = [SAME_DOC if c.same_document else OTHER_DOC,
             f"Вердикт: было «{o.verdict.decision}», стало «{n.verdict.decision}».",
             "Замечаний: " + ", ".join(f"{s} {so.get(s, 0)} -> {sn.get(s, 0)}" for s in SEVERITIES)
             + f". Вопросов: {len(o.questions)} -> {len(n.questions)}. Требований: {len(o.requirements)} -> {len(n.requirements)}.",
             f"Блокеры: было {len(o.verdict.blockers)}, стало {len(n.verdict.blockers)}; "
             f"осталось {len(bk)}, нет среди блокеров нового отчёта {len(bg)}, новых {len(bn)}.",
             f"Остальные замечания: осталось {len(ok)}, нет в новом отчёте {len(og)}, новых {len(on)}."]
    return lines


def render_compare(c: Comparison, old_name: str = "старый", new_name: str = "новый") -> str:
    o, n = c.old, c.new
    out = [f"# Сравнение двух прогонов: {o.document_name} и {n.document_name}\n",
           "Сравнение собрано агентом reqask из двух report.json, модель не вызывалась.\n"]
    out.append("| | Старый отчёт | Новый отчёт |")
    out.append("| :--- | :--- | :--- |")
    so, sn = _counts(o), _counts(n)
    rows = [
        ("Файл", old_name, new_name),
        ("Документ", o.document_name, n.document_name),
        ("SHA-256 документа", f"`{o.document_sha256[:16]}...`", f"`{n.document_sha256[:16]}...`"),
        ("Модель", o.model, n.model),
        ("Дата прогона", when(o.started_at), when(n.started_at)),
        ("Вердикт", o.verdict.decision, n.verdict.decision),
        ("Требований", len(o.requirements), len(n.requirements)),
        *((s, so.get(s, 0), sn.get(s, 0)) for s in SEVERITIES),
        ("Блокеров", len(o.verdict.blockers), len(n.verdict.blockers)),
        ("Вопросов автору", len(o.questions), len(n.questions)),
    ]
    for label, a, b in rows:
        out.append(f"| {label} | {str(a).replace('|', '/')} | {str(b).replace('|', '/')} |")
    out.append("")
    out.extend(f"- {line}" for line in summary_lines(c))
    out.append("")
    out.append(f"**Как сопоставлены замечания.** {METHOD}\n")

    bk, bg, bn, ok, og, on = _parts(c)

    def block(title: str, pairs=None, singles=None, result=None) -> None:
        items = pairs if pairs is not None else singles
        out.append(f"### {title} ({len(items)})\n")
        if not items:
            out.append("Нет.\n")
            return
        if pairs is not None:
            out.extend(f"- {_pair_line(p, c)}" for p in pairs)
        else:
            out.extend(f"- {_one(f, result)}" + (f" ({note})" if note else "") for f, note in singles)
        out.append("")

    out.append("## Блокеры (CRITICAL в вердикте)\n")
    block("Осталось", pairs=bk)
    block("Нет среди блокеров нового отчёта", singles=bg, result=o)
    block("Новые блокеры", singles=bn, result=n)
    out.append("## Остальные действующие замечания\n")
    block("Осталось", pairs=ok)
    block("Нет в новом отчёте", singles=og, result=o)
    block("Новые", singles=on, result=n)
    return "\n".join(out)
