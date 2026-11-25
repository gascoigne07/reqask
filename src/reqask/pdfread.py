"""Чтение PDF в строки (Ч-01 ... Ч-07).

- Страница без таблиц: текст берёт pypdf.
- Страница с таблицами: таблицы берёт pdfplumber и превращает в строки Markdown с вертикальными
  чертами, текст вне таблиц тоже берёт pdfplumber, чтобы ячейки не попали в текст второй раз.
  Таблицы и текст идут в том порядке, в каком стоят на странице.
- Колонтитулы: строка вверху или внизу страницы, которая после замены цифр на # повторяется
  на половине страниц и больше, удаляется. Для документа из одной или двух страниц правило не работает.
- Перенесённые строки склеиваются: строка без точки, двоеточия или точки с запятой в конце
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


def _clean(text: str) -> str:
    # Выравнивание по ширине даёт двойные пробелы между словами.
    return re.sub(r"[ \t ]{2,}", " ", text.replace(" ", " ")).strip()


def _cell(value: str | None) -> str:
    """Перенос внутри ячейки склеивается пробелом, пустая ячейка остаётся пустой (Ч-03)."""
    if not value:
        return ""
    return " ".join(value.split()).replace("|", "\\|")


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


def _drop_headers(pages: list[list[PdfLine]]) -> int:
    """Колонтитулы: повтор вверху или внизу страницы на половине страниц и больше (Ч-04).

    Верх и низ считаются вместе: pypdf отдаёт строки в порядке потока страницы, и нижний
    колонтитул часто стоит вторым сверху (проверено на PDF из reportlab).
    """
    with_text = [p for p in pages if any(line.text for line in p)]
    if len(with_text) < 3:
        return 0
    need = max(2, math.ceil(len(with_text) / 2))

    def edges(page: list[PdfLine]) -> list[PdfLine]:
        text = [line for line in page if line.text and line.kind == "text"]
        return text[:2] + [line for line in text[-2:] if all(line is not t for t in text[:2])]

    counts: dict[str, int] = {}
    for page in with_text:
        for key in {_header_key(line.text) for line in edges(page)}:
            counts[key] = counts.get(key, 0) + 1
    repeated = {k for k, v in counts.items() if v >= need}
    removed = 0
    for page in with_text:
        drop = {id(line) for line in edges(page) if _header_key(line.text) in repeated}
        if drop:
            removed += len(drop)
            page[:] = [line for line in page if id(line) not in drop]
    return removed


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
    """Склейка перенесённых строк внутри страницы (Ч-05)."""
    out: list[PdfLine] = []
    for line in lines:
        prev = out[-1] if out else None
        if (prev is not None and prev.kind == "text" and line.kind == "text" and prev.text and line.text
                and prev.page == line.page and line.text[0].islower() and not LIST_RE.match(line.text)):
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
    from pypdf import PdfReader

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
    lines: list[PdfLine] = []
    for page in pages:
        lines.extend(_join_wrapped(page))
    _mark_headings(lines)
    return PdfText(lines=lines, pages=total, empty_pages=empty, removed_headers=removed)


_SIMPLE_ITEM_RE = re.compile(r"^\d{1,2}[.)]\s")


def _mark_headings(lines: list[PdfLine]) -> None:
    """Заголовки по шаблону после склейки строк. «1. Текст» рядом с «2. Текст» это список, а не заголовки."""
    text_lines = [line for line in lines if line.kind == "text" and line.text]
    for index, line in enumerate(text_lines):
        level = heading_level(line.text)
        if not level:
            continue
        if _SIMPLE_ITEM_RE.match(line.text):
            neighbours = text_lines[max(0, index - 1):index] + text_lines[index + 1:index + 2]
            if any(_SIMPLE_ITEM_RE.match(n.text) for n in neighbours):
                continue
        line.kind, line.level = "heading", level
