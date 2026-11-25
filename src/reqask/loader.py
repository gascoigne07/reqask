"""Чтение входного документа (PDF, Markdown, текст, DOCX) в пронумерованные строки.

Номер строки служит адресом: по нему агент вырезает дословные цитаты
и ставит ссылки на место дефекта.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
RULE_RE = re.compile(r"^\s*([-*_]\s*){3,}$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".text"}


class LoadError(Exception):
    """Документ не удалось прочитать."""


@dataclass(frozen=True)
class Line:
    """Строка документа после очистки (Ч-01). Номер строки видят модель и отчёт."""

    no: int
    text: str
    page: int | None = None
    # text, table, heading. В Markdown заголовок и таблица видны по разметке, в PDF их размечает чтение.
    kind: str = "text"
    level: int = 0


@dataclass
class Document:
    path: Path
    fmt: str
    lines: list[Line]
    sha256: str
    # PDF: страницы без текста (Ч-07) и число удалённых строк колонтитулов (Ч-04).
    empty_pages: list[int] = field(default_factory=list)
    removed_headers: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def n(self) -> int:
        return len(self.lines)

    def line(self, no: int) -> Line:
        return self.lines[no - 1]

    def text(self, start: int, end: int) -> str:
        return "\n".join(line.text for line in self.lines[start - 1 : end])

    def numbered(self, start: int = 1, end: int | None = None) -> str:
        """Текст с разметкой строк вида `L0012| ...` для промптов."""
        end = end or self.n
        width = max(4, len(str(self.n)))
        return "\n".join(f"L{line.no:0{width}d}| {line.text}" for line in self.lines[start - 1 : end])

    @cached_property
    def _headings(self) -> list[tuple[int, int, str]]:
        found = []
        in_fence = False
        for line in self.lines:
            if line.kind == "heading" and line.level:
                found.append((line.no, line.level, line.text.strip()))
                continue
            if FENCE_RE.match(line.text):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = HEADING_RE.match(line.text)
            if match:
                found.append((line.no, len(match.group(1)), match.group(2).strip()))
        return found

    @cached_property
    def _section_paths(self) -> list[str]:
        paths = [""] * (self.n + 1)
        stack: list[tuple[int, str]] = []
        headings = {no: (level, title) for no, level, title in self._headings}
        for no in range(1, self.n + 1):
            if no in headings:
                level, title = headings[no]
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
            # Корневой заголовок документа в путь не включаем, он одинаков для всех строк.
            parts = [title for level, title in stack if level > 1] or [title for _, title in stack]
            paths[no] = " / ".join(parts)
        return paths

    def is_heading(self, no: int) -> bool:
        return any(h[0] == no for h in self._headings)

    def section_path(self, no: int) -> str:
        if 1 <= no <= self.n:
            return self._section_paths[no]
        return ""

    def outline(self) -> str:
        return "\n".join(f"{'  ' * (level - 1)}{title} (строка {no})" for no, level, title in self._headings)

    def is_content(self, no: int) -> bool:
        """Строка несёт содержание: не пустая, не заголовок и не служебная разметка."""
        text = self.line(no).text
        if not text.strip():
            return False
        if self.is_heading(no) or TABLE_SEP_RE.match(text) or RULE_RE.match(text) or FENCE_RE.match(text):
            return False
        return True


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _load_text(data: bytes) -> list[tuple[str, int | None]]:
    return [(raw.rstrip(), None) for raw in _decode(data).splitlines()]


def _load_pdf(path: Path):
    from pypdf.errors import PdfReadError

    from .pdfread import ScanError, read_pdf

    try:
        return read_pdf(path)
    except PermissionError as exc:
        raise LoadError("PDF защищён паролем. Снимите защиту и повторите запуск.") from exc
    except ScanError as exc:
        raise LoadError(
            f"Это скан, нужен текстовый PDF: {exc}. Распознайте текст (OCR) "
            "или передайте документ в Markdown, DOCX или TXT."
        ) from exc
    except (PdfReadError, ValueError, KeyError, OSError) as exc:
        raise LoadError(f"Не удалось разобрать PDF, файл повреждён или это не PDF: {exc}") from exc
    except Exception as exc:  # noqa: BLE001  pdfminer бросает свои исключения на битых файлах
        raise LoadError(f"Не удалось разобрать PDF: {type(exc).__name__}: {exc}") from exc


def _load_docx(path: Path) -> list[tuple[str, int | None]]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    rows: list[tuple[str, int | None]] = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.rstrip()
            style = (paragraph.style.name or "") if paragraph.style is not None else ""
            match = re.match(r"(?:Heading|Заголовок)\s*(\d)", style)
            if match and text:
                text = "#" * int(match.group(1)) + " " + text
            rows.append((text, None))
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            for row in table.rows:
                cells = [" ".join(cell.text.split()) for cell in row.cells]
                rows.append(("| " + " | ".join(cells) + " |", None))
            rows.append(("", None))
    return rows


def load_document(path: str | Path) -> Document:
    path = Path(path)
    if not path.is_file():
        raise LoadError(f"Файл не найден: {path}")
    data = path.read_bytes()
    if not data.strip():
        raise LoadError(f"Файл пуст: {path}")

    ext = path.suffix.lower()
    if ext == ".pdf" or data[:5] == b"%PDF-":
        pdf = _load_pdf(path)
        lines = [Line(no=i, text=line.text, page=line.page, kind=line.kind, level=line.level)
                 for i, line in enumerate(pdf.lines, start=1)]
        return Document(path=path, fmt="pdf", lines=lines, sha256=hashlib.sha256(data).hexdigest(),
                        empty_pages=pdf.empty_pages, removed_headers=pdf.removed_headers)
    if ext == ".doc":
        raise LoadError("Старый формат .doc не поддерживается. Сохраните документ как DOCX или PDF.")
    if ext == ".docx":
        fmt, rows = "docx", _load_docx(path)
    elif ext in TEXT_EXTENSIONS or not ext:
        fmt, rows = (ext.lstrip(".") or "txt"), _load_text(data)
    else:
        # Незнакомое расширение читаем как текст, бинарные файлы отсекаем.
        if b"\x00" in data[:4096]:
            raise LoadError(f"Формат {ext} не поддерживается. Передайте PDF, Markdown, DOCX или TXT.")
        fmt, rows = ext.lstrip("."), _load_text(data)

    lines = [Line(no=i, text=text, page=page) for i, (text, page) in enumerate(rows, start=1)]
    if not any(line.text.strip() for line in lines):
        raise LoadError(f"В документе нет текста: {path}")
    return Document(path=path, fmt=fmt, lines=lines, sha256=hashlib.sha256(data).hexdigest())
