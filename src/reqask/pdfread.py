"""Чтение PDF в строки (Ч-01 ... Ч-07).

- Страница без таблиц: текст берёт pypdf.
- Страница с таблицами: таблицы берёт pdfplumber и превращает в строки Markdown с вертикальными
  чертами, текст вне таблиц тоже берёт pdfplumber, чтобы ячейки не попали в текст второй раз.
  Таблицы и текст идут в том порядке, в каком стоят на странице.
- Залитые прямоугольники-подложки под текстом (их рисует Word при экспорте в PDF) не считаются
  линиями таблицы, если на странице есть настоящие линии. Иначе каждая строка текста в ячейке
  становится отдельной строкой таблицы и появляются лишние пустые столбцы.
- Таблица, продолженная на следующей странице, склеивается в одну (_join_tables): повтор шапки
  убирается, строка, разорванная границей страницы, собирается обратно.
- Колонтитулы: строка вверху или внизу страницы, которая после замены цифр на # повторяется
  на половине страниц и больше, удаляется. Для документа из одной или двух страниц правило не работает.
- Колонтитул таблицей: таблица у края страницы с тем же правилом повтора удаляется целиком.
- Перенесённые строки склеиваются, и через границу страницы тоже: строка без точки, двоеточия или точки с запятой в конце
  и следующая со строчной буквы. Перенос слова через дефис склеивается без дефиса.
  Строки таблиц, пункты списков и заголовки не склеиваются.
- Заголовки по шаблону «1.2 Название», «Раздел 3», «Приложение А».
  «6. Название» с нумерованным списком «1. ...» под ним остаётся заголовком, если продолжает номер раздела.
- Неизвестный глиф «(cid:N)» в начале строки становится маркером списка, в середине строки убирается.
- Страницы без текста перечисляются; если их больше половины, это скан и чтение останавливается.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

# Пункт списка в начале строки: маркер или номер со скобкой.
LIST_RE = re.compile(r"^\s*(?:[-–—•●▪◦*·]|\d{1,3}[.)]\s|[a-zа-яё][.)]\s)", re.IGNORECASE)
# «1 Название», «1.2 Название», «1.2. Название»: номер раздела и текст с заглавной буквы.
NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,4})\.?\s+([A-ZА-ЯЁ].*)$")
WORD_HEADING_RE = re.compile(
    r"^(?:Раздел|Глава|Часть|Приложение|Section|Chapter|Part|Appendix)\s+([\dIVXLCА-ЯЁA-Z]{1,4})\b\.?(.*)$"
)
MAX_HEADING_CHARS = 90
MAX_HEADING_WORDS = 12
SENTENCE_END = ".:;!?"
# Строка оглавления: после названия стоит номер страницы («1.1 Purpose 6»).
# Точки-заполнители к этому времени уже убраны в _clean, остаётся хвостовой номер.
# Заголовок тела тоже может кончаться числом («4.2 Ответ с кодом 400»), поэтому одного
# хвоста мало: строки оглавления идут подряд, заголовок тела стоит один (см. _mark_headings).
TOC_PAGE_TAIL_RE = re.compile(r"[^\W\d_].*\s\d{1,4}$")


@dataclass
class PdfLine:
    text: str
    page: int
    kind: str = "text"  # text, table, heading
    level: int = 0
    # Только для строк таблицы (кроме разделителя): ячейки, страница конца строки и положение
    # таблицы на странице (верх и низ в долях высоты страницы). Нужны для склейки таблиц через страницу.
    cells: list[str] | None = field(default=None, repr=False)
    end_page: int = field(default=0, repr=False)
    box: tuple[float, float] = field(default=(0.0, 0.0), repr=False)


@dataclass
class PdfText:
    lines: list[PdfLine]
    pages: int
    empty_pages: list[int] = field(default_factory=list)
    removed_headers: int = 0
    # Страницы, на которых pdfplumber упал: их текст взят через pypdf, таблицы там не разобраны.
    fallback_pages: list[int] = field(default_factory=list)
    # Сколько раз продолжение таблицы на следующей странице приклеено к её началу.
    joined_tables: int = 0


class ScanError(Exception):
    """В PDF нет текстового слоя на большей части страниц."""


# Лигатуры. Без таблицы Unicode у шрифта pypdf выдаёт имя глифа («Speci/f_ication»),
# с таблицей приходит символ из блока U+FB00. Оба вида дают обычные буквы,
# иначе цитаты модели не сойдутся с текстом.
LIGATURE_NAME_RE = re.compile(r"/(f_f_i|f_f_l|f_f|f_i|f_l|f_j|f_t|s_t)")
LIGATURE_CHARS = str.maketrans({
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
})
# Точки-заполнители в строке оглавления.
LEADER_RE = re.compile(r"(?:\s*\.){5,}\s*")


def _ligatures(text: str) -> str:
    return LIGATURE_NAME_RE.sub(lambda m: m.group(1).replace("_", ""), text).translate(LIGATURE_CHARS)


# Глиф без таблицы Unicode pdfminer отдаёт как «(cid:127)». В начале строки это почти всегда
# маркер списка (шрифт Symbol в PDF из Word), в середине строки знак ничего не значит для текста.
CID_RE = re.compile(r"\(cid:\d+\)")
CID_START_RE = re.compile(r"^\s*(?:\(cid:\d+\)\s*)+")


def _cid(text: str) -> str:
    if "(cid:" not in text:
        return text
    text = CID_START_RE.sub("• ", text)
    # Между двумя буквами или цифрами неизвестный глиф мог быть пробелом: слова не склеиваем.
    text = re.sub(r"(?<=\w)(?:\(cid:\d+\))+(?=\w)", " ", text)
    return CID_RE.sub("", text)


def _clean(text: str) -> str:
    text = LEADER_RE.sub(" ", _ligatures(_cid(text)))
    # Выравнивание по ширине даёт двойные пробелы между словами.
    return re.sub(r"[ \t ]{2,}", " ", text.replace(" ", " ")).strip()


# Перенос слова через дефис внутри ячейки: буква, дефис, конец строки, строчная буква.
CELL_HYPHEN_RE = re.compile(r"(?<=[^\W\d_])-[ \t]*\n\s*(?=[a-zа-яё])")


def _cell(value: str | None) -> str:
    """Перенос внутри ячейки склеивается пробелом, перенос слова через дефис без дефиса,
    как в обычном тексте; пустая ячейка остаётся пустой (Ч-03)."""
    if not value:
        return ""
    value = CELL_HYPHEN_RE.sub("", _ligatures(_cid(value)))
    return " ".join(value.split()).replace("|", "\\|")


def _row_text(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _table_lines(rows: list[list[str | None]], page: int, box: tuple[float, float] = (0.0, 0.0)) -> list[PdfLine]:
    rows = [row for row in rows if row and any(cell for cell in row)]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    out = [PdfLine("", page)]
    for index, row in enumerate(rows):
        cells = [_cell(c) for c in row] + [""] * (width - len(row))
        out.append(PdfLine(_row_text(cells), page, "table", cells=cells, end_page=page, box=box))
        if index == 0:
            # Строка-разделитель после шапки, как в Markdown.
            out.append(PdfLine(_row_text(["---"] * width), page, "table"))
    out.append(PdfLine("", page))
    return out


# Толщина, до которой залитый прямоугольник считается линией (рамки таблиц в PDF из Word
# рисуются залитыми прямоугольниками толщиной около 0,5 pt).
RULE_THICKNESS = 2.0


def _is_rule(obj: dict) -> bool:
    if obj.get("object_type") in ("line", "curve"):
        return True
    return obj.get("object_type") == "rect" and (
        bool(obj.get("stroke")) or min(obj["width"], obj["height"]) <= RULE_THICKNESS)


def _is_backdrop(obj: dict) -> bool:
    """Залитый прямоугольник без обводки шире линии: подложка ячейки или строки текста."""
    return (obj.get("object_type") == "rect" and bool(obj.get("fill")) and not obj.get("stroke")
            and min(obj["width"], obj["height"]) > RULE_THICKNESS)


def _without_backdrops(plumber_page):
    """Страница без подложек, если на ней есть настоящие линии; иначе как есть.
    Без линий таблицу могут задавать только сами заливки, их не трогаем."""
    rects = plumber_page.rects
    if not any(_is_backdrop(r) for r in rects):
        return plumber_page
    if not (plumber_page.lines or plumber_page.curves or any(_is_rule(r) for r in rects)):
        return plumber_page
    return plumber_page.filter(lambda obj: not _is_backdrop(obj))


def _page_lines(pypdf_page, plumber_page, page_no: int) -> list[PdfLine]:
    plumber_page = _without_backdrops(plumber_page)
    tables = plumber_page.find_tables()
    if not tables:
        text = pypdf_page.extract_text() or ""
        return [PdfLine(_clean(raw), page_no) for raw in text.splitlines()]
    outside = plumber_page
    for table in tables:
        outside = outside.outside_bbox(table.bbox)
    items: list[tuple[float, int, list[PdfLine]]] = []
    for line in outside.extract_text_lines():
        items.append((line["top"], 0, [PdfLine(_clean(line["text"]), page_no)]))
    height = float(plumber_page.height) or 1.0
    for table in tables:
        box = (table.bbox[1] / height, table.bbox[3] / height)
        items.append((table.bbox[1], 1, _table_lines(table.extract(), page_no, box)))
    items.sort(key=lambda item: (item[0], item[1]))
    return [line for _, _, lines in items for line in lines]


def _header_key(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.split())).casefold()


def _table_blocks(page: list[PdfLine]) -> list[tuple[int, int]]:
    """Границы таблиц на странице: (первая, последняя строка) подряд идущих строк таблицы."""
    blocks: list[tuple[int, int]] = []
    start = None
    for index, line in enumerate(page + [PdfLine("", 0)]):
        if line.kind == "table" and start is None:
            start = index
        elif line.kind != "table" and start is not None:
            blocks.append((start, index - 1))
            start = None
    return blocks


def _edge_tables(page: list[PdfLine]) -> list[tuple[int, int]]:
    """Таблицы у края страницы: до или после них не больше двух строк текста."""
    content = [i for i, line in enumerate(page) if line.text]
    if not content:
        return []
    head, tail = set(content[:3]), set(content[-3:])
    return [(a, b) for a, b in _table_blocks(page) if a in head or b in tail]


def _table_key(page: list[PdfLine], block: tuple[int, int]) -> str:
    a, b = block
    return "\n".join(_header_key(line.text) for line in page[a : b + 1])


def _drop_headers(pages: list[list[PdfLine]]) -> int:
    """Колонтитулы: повтор вверху или внизу страницы на половине страниц и больше (Ч-04).

    Верх и низ считаются вместе: pypdf отдаёт строки в порядке потока страницы, и нижний
    колонтитул часто стоит вторым сверху (проверено на PDF из reportlab).
    Колонтитул бывает свёрстан таблицей (документ PURE «puget sound»): таблица у края страницы,
    которая повторяется так же часто, удаляется целиком вместе с пустыми строками вокруг.
    """
    with_text = [p for p in pages if any(line.text for line in p)]
    if len(with_text) < 3:
        return 0
    need = max(2, math.ceil(len(with_text) / 2))

    def edges(page: list[PdfLine]) -> list[PdfLine]:
        text = [line for line in page if line.text and line.kind == "text"]
        return text[:2] + [line for line in text[-2:] if all(line is not t for t in text[:2])]

    counts: dict[str, int] = {}
    table_counts: dict[str, int] = {}
    for page in with_text:
        for key in {_header_key(line.text) for line in edges(page)}:
            counts[key] = counts.get(key, 0) + 1
        for key in {_table_key(page, block) for block in _edge_tables(page)}:
            table_counts[key] = table_counts.get(key, 0) + 1
    repeated = {k for k, v in counts.items() if v >= need}
    repeated_tables = {k for k, v in table_counts.items() if v >= need}
    removed = 0
    for page in with_text:
        drop = {id(line) for line in edges(page) if _header_key(line.text) in repeated}
        removed += len(drop)
        for a, b in _edge_tables(page):
            if _table_key(page, (a, b)) not in repeated_tables:
                continue
            removed += sum(1 for line in page[a : b + 1] if not set(line.text) <= set("|- "))
            a = a - 1 if a > 0 and not page[a - 1].text else a
            b = b + 1 if b + 1 < len(page) and not page[b + 1].text else b
            drop.update(id(line) for line in page[a : b + 1])
        if drop:
            page[:] = [line for line in page if id(line) not in drop]
    return removed


def _page_tail(text: str) -> bool:
    """Строка кончается числом без точки после текста: так выглядит строка оглавления с номером страницы."""
    return bool(TOC_PAGE_TAIL_RE.search(text.strip()))


def heading_level(text: str) -> int:
    """Уровень заголовка по шаблону (Ч-06) или 0, если строка на заголовок не похожа."""
    text = text.strip()
    if not text or len(text) > MAX_HEADING_CHARS or len(text.split()) > MAX_HEADING_WORDS:
        return 0
    if text[-1] in ".;:,":
        return 0
    match = WORD_HEADING_RE.match(text)
    if match:
        return 1
    match = NUMBERED_HEADING_RE.match(text)
    if match:
        return match.group(1).count(".") + 1
    return 0


def _join_wrapped(lines: list[PdfLine]) -> list[PdfLine]:
    """Склейка перенесённых строк (Ч-05), в том числе через границу страницы:
    колонтитулы к этому времени уже удалены. Склеенная строка остаётся на странице начала."""
    out: list[PdfLine] = []
    for line in lines:
        prev = out[-1] if out else None
        if (prev is not None and prev.kind == "text" and line.kind == "text" and prev.text and line.text
                and line.text[0].islower() and not LIST_RE.match(line.text)):
            tail = prev.text.rstrip()
            if tail.endswith("-") and len(tail) > 1 and tail[-2].isalpha():
                prev.text = tail[:-1] + line.text
                continue
            if tail[-1] not in SENTENCE_END:
                prev.text = tail + " " + line.text
                continue
        out.append(line)
    return out


# Таблица считается доходящей до низа страницы, если её низ ниже этой доли высоты,
# и начинающейся сверху, если её верх выше этой доли.
TABLE_BOTTOM_EDGE = 0.7
TABLE_TOP_EDGE = 0.3
# Служебные слова, на которых ячейка не может кончаться, если строка не разорвана.
OPEN_WORDS = frozenset(
    "и или а но в во на с со к ко по для от до из у о об при без над под за через между что как "
    "and or but of to in on at by for with from the a an".split()
)


def _norm_cells(cells: list[str]) -> list[str]:
    return [" ".join(c.split()).casefold() for c in cells]


def _unfinished(cell: str) -> bool:
    """Ячейка обрывается: кончается запятой, дефисом, открытой скобкой или служебным словом."""
    cell = cell.rstrip()
    if not cell:
        return False
    if cell[-1] in ",(-/":
        return True
    words = cell.split()
    return words[-1].casefold() in OPEN_WORDS


def _row_continues(prev: list[str], nxt: list[str], first_col_always_filled: bool) -> bool:
    """Первая строка продолжения дописывает последнюю строку предыдущей части таблицы."""
    filled = [(a, b) for a, b in zip(prev, nxt) if b]
    if not filled:
        return False
    for a, b in filled:
        if a and _unfinished(a):
            return True
    # Первая непустая ячейка продолжения начинается со строчной буквы и состоит из нескольких слов,
    # а ячейка над ней не кончается точкой: фраза разорвана. Одно слово со строчной («да», «daily»)
    # бывает началом обычной строки, такое не клеим.
    a, b = filled[0]
    if a and a[-1] not in SENTENCE_END and b[0].islower() and len(b.split()) > 1 and len(a.split()) > 1:
        return True
    # Пустая первая ячейка при заполненной сверху, а во всей таблице первая ячейка нигде больше не пуста.
    return first_col_always_filled and not nxt[0] and bool(prev[0])


def _glue(a: str, b: str) -> str:
    if not a or not b:
        return a or b
    if a.endswith("-") and len(a) > 1 and a[-2].isalpha() and b[0].islower():
        return a[:-1] + b
    return a + " " + b


def _join_tables(lines: list[PdfLine]) -> int:
    """Склейка таблицы, продолженной на следующей странице (после снятия колонтитулов).

    Склеиваются две таблицы, между которыми нет текста, если первая кончается внизу страницы,
    вторая начинается вверху следующей и у них одно число столбцов, больше одного. Повтор шапки в начале
    продолжения убирается. Первая строка продолжения, которая дописывает разорванную строку
    (_row_continues), приклеивается к ней по ячейкам. У склеенной строки остаётся страница начала.
    При любом сомнении таблицы остаются раздельными.
    """
    joined = 0
    index = 0
    while True:
        blocks = _table_blocks(lines)
        pair = None
        for (a0, a1), (b0, b1) in zip(blocks, blocks[1:]):
            if b0 <= index:
                continue
            if any(line.text for line in lines[a1 + 1:b0]):
                continue
            rows_a = [line for line in lines[a0:a1 + 1] if line.cells is not None]
            rows_b = [line for line in lines[b0:b1 + 1] if line.cells is not None]
            if not rows_a or not rows_b:
                continue
            last, first = rows_a[-1], rows_b[0]
            # Таблица в один столбец обычно рамка вокруг страницы (слайды, плакаты), а не данные.
            if (first.page == last.end_page + 1 and len(first.cells) == len(last.cells) > 1
                    and last.box[1] >= TABLE_BOTTOM_EDGE and first.box[0] <= TABLE_TOP_EDGE):
                pair = (a0, a1, b0, b1, rows_a, rows_b)
                break
        if pair is None:
            return joined
        a0, a1, b0, b1, rows_a, rows_b = pair
        if _norm_cells(rows_b[0].cells) == _norm_cells(rows_a[0].cells):
            rows_b = rows_b[1:]
        last = rows_a[-1]
        if rows_b:
            first_filled = all(r.cells[0] for r in rows_a + rows_b[1:])
            if _row_continues(last.cells, rows_b[0].cells, first_filled):
                head = rows_b.pop(0)
                last.cells = [_glue(a, b) for a, b in zip(last.cells, head.cells)]
                last.text = _row_text(last.cells)
                last.end_page, last.box = head.end_page, (last.box[0], head.box[1])
        # Строки продолжения сохраняют свою страницу и положение: таблицу на три страницы
        # и больше следующий шаг склеивает по низу последней части.
        lines[a1 + 1:b1 + 1] = rows_b
        joined += 1
        index = a0


def read_pdf(path: Path) -> PdfText:
    """Бросает ScanError для скана; ошибки pypdf пробрасывает вызывающему."""
    import pdfplumber
    import logging

    from pypdf import PdfReader

    # Мелкие поломки структуры файла pypdf пишет в журнал предупреждениями, на чтение они не влияют.
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    reader = PdfReader(str(path))
    if reader.is_encrypted and not reader.decrypt(""):
        raise PermissionError("PDF защищён паролем")
    pages: list[list[PdfLine]] = []
    fallback: list[int] = []
    with pdfplumber.open(str(path), password="") as pdf:
        for page_no, (pypdf_page, plumber_page) in enumerate(zip(reader.pages, pdf.pages), start=1):
            try:
                pages.append(_page_lines(pypdf_page, plumber_page, page_no))
            except Exception:  # noqa: BLE001  pdfminer бросает свои исключения на битых объектах страницы
                # Одна битая страница не должна делать нечитаемым весь документ: текст берёт pypdf, без таблиц.
                # Если не прочтёт и pypdf, ошибка уходит выше, как раньше.
                text = pypdf_page.extract_text() or ""
                pages.append([PdfLine(_clean(raw), page_no) for raw in text.splitlines()])
                fallback.append(page_no)
    empty = [no for no, page in enumerate(pages, start=1) if not any(line.text for line in page)]
    total = len(pages)
    if total == 0 or len(empty) * 2 > total:
        raise ScanError(f"текста нет на {len(empty)} из {total} страниц")
    removed = _drop_headers(pages)
    # Страница, на которой после снятия колонтитулов ничего не осталось (или осталась пустая
    # таблица из одних разделителей), для читателя тоже пустая. Проверка на скан выше идёт
    # по исходному тексту: у такой страницы текстовый слой есть.
    empty = sorted(set(empty) | {no for no, page in enumerate(pages, start=1) if not any(_has_text(line) for line in page)})
    lines = [line for page in pages for line in page]
    joined = _join_tables(lines)
    lines = _join_wrapped(lines)
    _mark_headings(lines)
    return PdfText(lines=lines, pages=total, empty_pages=empty, removed_headers=removed, fallback_pages=fallback,
                   joined_tables=joined)


def _has_text(line: PdfLine) -> bool:
    return bool(line.text) and not set(line.text) <= set("|- ")


_SIMPLE_ITEM_RE = re.compile(r"^\d{1,2}[.)]\s")


def _item_no(text: str) -> int | None:
    match = _SIMPLE_ITEM_RE.match(text)
    return int(re.match(r"\d+", text).group()) if match else None


def _section_before_list(no: int, prev: PdfLine | None, next_: PdfLine | None, last_top: int) -> bool:
    """«6. Критерии приёмки», а под ним список «1. ...», «2. ...»: это заголовок раздела.
    Номер продолжает предыдущий заголовок верхнего уровня, следующая строка не продолжает
    нумерацию (не «7.»), предыдущая не стоит перед ним в той же нумерации (не «5.»)."""
    if no != last_top + 1:
        return False
    if next_ is not None and _item_no(next_.text) == no + 1:
        return False
    return prev is None or _item_no(prev.text) != no - 1


def _mark_headings(lines: list[PdfLine]) -> None:
    """Заголовки по шаблону после склейки строк. «1. Текст» рядом с «2. Текст» это список, а не заголовки.
    Исключение: заголовок раздела, за которым сразу идёт нумерованный список (_section_before_list).
    Строка с числом в конце рядом с такой же строкой это оглавление с номерами страниц, а не заголовок.
    Сосед может быть длинным пунктом оглавления, который сам на заголовок не похож."""
    text_lines = [line for line in lines if line.kind == "text" and line.text]
    last_top = 0  # номер последнего заголовка верхнего уровня вида «5» или «5.»
    for index, line in enumerate(text_lines):
        level = heading_level(line.text)
        if not level:
            continue
        if _page_tail(line.text):
            around = text_lines[max(0, index - 1):index] + text_lines[index + 1:index + 2]
            if any(_page_tail(n.text) for n in around):
                continue
        if _SIMPLE_ITEM_RE.match(line.text):
            prev = text_lines[index - 1] if index > 0 else None
            next_ = text_lines[index + 1] if index + 1 < len(text_lines) else None
            if (any(n is not None and _SIMPLE_ITEM_RE.match(n.text) for n in (prev, next_))
                    and not _section_before_list(_item_no(line.text), prev, next_, last_top)):
                continue
        line.kind, line.level = "heading", level
        top = re.match(r"(\d{1,2})\.?\s", line.text)
        if level == 1 and top:
            last_top = int(top.group(1))
