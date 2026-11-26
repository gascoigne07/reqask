"""Чтение PDF в строки (Ч-01 ... Ч-07).

- Страница без таблиц: текст берёт pypdf.
- Страница с таблицами: таблицы берёт pdfplumber и превращает в строки Markdown с вертикальными
  чертами, текст вне таблиц тоже берёт pdfplumber, чтобы ячейки не попали в текст второй раз.
  Таблицы и текст идут в том порядке, в каком стоят на странице.
- Колонтитулы: строка вверху или внизу страницы, которая после замены цифр на # повторяется
  на половине страниц и больше, удаляется. Для документа из одной или двух страниц правило не работает.
- Колонтитул таблицей: таблица у края страницы с тем же правилом повтора удаляется целиком.
- Перенесённые строки склеиваются, и через границу страницы тоже: строка без точки, двоеточия или точки с запятой в конце
  и следующая со строчной буквы. Перенос слова через дефис склеивается без дефиса.
  Строки таблиц, пункты списков и заголовки не склеиваются.
- Заголовки по шаблону «1.2 Название», «Раздел 3», «Приложение А».
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


@dataclass
class PdfText:
    lines: list[PdfLine]
    pages: int
    empty_pages: list[int] = field(default_factory=list)
    removed_headers: int = 0


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


def _clean(text: str) -> str:
    text = LEADER_RE.sub(" ", _ligatures(text))
    # Выравнивание по ширине даёт двойные пробелы между словами.
    return re.sub(r"[ \t ]{2,}", " ", text.replace(" ", " ")).strip()


def _cell(value: str | None) -> str:
    """Перенос внутри ячейки склеивается пробелом, пустая ячейка остаётся пустой (Ч-03)."""
    if not value:
        return ""
    return " ".join(_ligatures(value).split()).replace("|", "\\|")


def _table_lines(rows: list[list[str | None]], page: int) -> list[PdfLine]:
    rows = [row for row in rows if row and any(cell for cell in row)]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    out = [PdfLine("", page)]
    for index, row in enumerate(rows):
        cells = [_cell(c) for c in row] + [""] * (width - len(row))
        out.append(PdfLine("| " + " | ".join(cells) + " |", page, "table"))
        if index == 0:
            # Строка-разделитель после шапки, как в Markdown.
            out.append(PdfLine("| " + " | ".join(["---"] * width) + " |", page, "table"))
    out.append(PdfLine("", page))
    return out


def _page_lines(pypdf_page, plumber_page, page_no: int) -> list[PdfLine]:
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
    for table in tables:
        items.append((table.bbox[1], 1, _table_lines(table.extract(), page_no)))
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
    with pdfplumber.open(str(path), password="") as pdf:
        for page_no, (pypdf_page, plumber_page) in enumerate(zip(reader.pages, pdf.pages), start=1):
            pages.append(_page_lines(pypdf_page, plumber_page, page_no))
    empty = [no for no, page in enumerate(pages, start=1) if not any(line.text for line in page)]
    total = len(pages)
    if total == 0 or len(empty) * 2 > total:
        raise ScanError(f"текста нет на {len(empty)} из {total} страниц")
    removed = _drop_headers(pages)
    lines = _join_wrapped([line for page in pages for line in page])
    _mark_headings(lines)
    return PdfText(lines=lines, pages=total, empty_pages=empty, removed_headers=removed)


_SIMPLE_ITEM_RE = re.compile(r"^\d{1,2}[.)]\s")


def _mark_headings(lines: list[PdfLine]) -> None:
    """Заголовки по шаблону после склейки строк. «1. Текст» рядом с «2. Текст» это список, а не заголовки.
    Строка с числом в конце рядом с такой же строкой это оглавление с номерами страниц, а не заголовок.
    Сосед может быть длинным пунктом оглавления, который сам на заголовок не похож."""
    text_lines = [line for line in lines if line.kind == "text" and line.text]
    for index, line in enumerate(text_lines):
        level = heading_level(line.text)
        if not level:
            continue
        if _page_tail(line.text):
            around = text_lines[max(0, index - 1):index] + text_lines[index + 1:index + 2]
            if any(_page_tail(n.text) for n in around):
                continue
        if _SIMPLE_ITEM_RE.match(line.text):
            neighbours = text_lines[max(0, index - 1):index] + text_lines[index + 1:index + 2]
            if any(_SIMPLE_ITEM_RE.match(n.text) for n in neighbours):
                continue
        line.kind, line.level = "heading", level
