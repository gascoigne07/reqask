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
    """Строка документа после очистки. Номер строки видят модель и отчёт."""

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
    # PDF: страницы без текста и число удалённых строк колонтитулов.
    empty_pages: list[int] = field(default_factory=list)
    removed_headers: int = 0
    # PDF: страницы, прочитанные запасным способом (pypdf без таблиц), потому что pdfplumber на них упал.
    fallback_pages: list[int] = field(default_factory=list)

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

    @cached_property
    def _heading_nos(self) -> frozenset[int]:
        return frozenset(h[0] for h in self._headings)

    def is_heading(self, no: int) -> bool:
        return no in self._heading_nos

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


# Метка порядка байтов: UTF-32 проверяется раньше UTF-16, у них общее начало FF FE.
_BOMS = ((b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
         (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"))
# Доля управляющих символов (кроме табуляции и переводов строк), выше которой текст считается двоичным.
MAX_CONTROL_SHARE = 0.02


def _decode(data: bytes) -> tuple[str, str]:
    """Текст и название кодировки, в которой он прочитан."""
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            try:
                return data.decode(encoding), encoding
            except UnicodeDecodeError:
                break
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8"


_CYRILLIC_RE = re.compile("[А-Яа-яЁё]")
_WORD_RE = re.compile("[A-Za-zА-Яа-яЁё]+")
_LATIN_RE = re.compile("[A-Za-z]")
# Самые частые буквы русского текста: у настоящего русского их доля 0.6-0.7, у KOI8-R и CP866,
# прочитанных как cp1251, 0.35-0.45.
_COMMON_RU_LETTERS = "оеаинтсрвл"
# Меньше этого числа кириллических букв частоту не считаем: на коротком тексте она шумит.
_MIN_LETTERS_FOR_FREQUENCY = 200
_DOS_JUNK = "¤¦¬"


def _wrong_cp1251(text: str) -> bool:
    """Текст, прочитанный как cp1251, похож на кракозябры: файл в другой кодировке (KOI8-R, Latin-1, CP866).

    cp1251 принимает почти любые байты, поэтому ошибки декодирования не будет. Признаки:
    у длинного текста доля частых русских букв ниже обычной; у короткого заглавных букв больше
    половины и внутри слов строчная стоит перед заглавной (KOI8-R меняет регистр); слова из латиницы
    с вкраплением кириллицы («caf?», «Gr??e») встречаются заметно часто (Latin-1 с диакритикой);
    знаки ¤ ¦ ¬ в заметном числе выдают CP866.
    """
    cyrillic = _CYRILLIC_RE.findall(text)
    words = _WORD_RE.findall(text)
    if len(cyrillic) >= _MIN_LETTERS_FOR_FREQUENCY:
        common = sum(1 for ch in cyrillic if ch.lower() in _COMMON_RU_LETTERS) / len(cyrillic)
        if common < 0.5:
            return True
    elif cyrillic:
        upper = sum(1 for ch in cyrillic if ch.isupper()) / len(cyrillic)
        inverted = sum(1 for w in words if re.search("[а-яё][А-ЯЁ]", w))
        if upper > 0.6 and inverted >= 1:
            return True
    # CP866 (старый DOS) даёт в середине слов знаки ¤ ¦ ¬, которых нет в настоящем тексте cp1251.
    odd = sum(1 for ch in text if ch in _DOS_JUNK)
    if odd >= 5 and odd >= 0.01 * (len(cyrillic) + odd):
        return True
    mixed = sum(1 for w in words if _CYRILLIC_RE.search(w) and _LATIN_RE.search(w))
    return mixed >= 2 and mixed >= 0.03 * len(words)


def _looks_binary(text: str) -> bool:
    """NUL или заметная доля управляющих символов: это не текст (архив, картинка, текст в UTF-16 без метки)."""
    if "\x00" in text:
        return True
    control = sum(1 for ch in text if ord(ch) < 32 and ch not in "\t\n\r\f\v" or ch == "\ufffd")
    return control > MAX_CONTROL_SHARE * max(1, len(text))


# Разделители, которые не переводят строку в редакторе: внутри строки они становятся пробелом.
_SOFT_BREAKS_RE = re.compile("[\f\v\x1c-\x1e\x85\u2028\u2029]")


def _load_text(data: bytes, path: Path) -> list[tuple[str, int | None]]:
    text, encoding = _decode(data)
    if _looks_binary(text):
        raise LoadError(
            f"Файл похож на двоичный, а не на текст: {path.name}. Передайте PDF, Markdown, DOCX или TXT "
            "в кодировке UTF-8."
        )
    if encoding == "cp1251" and _wrong_cp1251(text):
        raise LoadError(
            f"Не удалось определить кодировку файла {path.name}: текст читается как набор случайных символов. "
            "Сохраните файл в UTF-8 (в редакторе: «Сохранить как», кодировка UTF-8) и запустите снова."
        )
    # Строки делим только по переводу строки, как редактор: str.splitlines() режет ещё по \f, \v,
    # \x1c-\x1e, \x85, U+2028 и U+2029, и номера строк в отчёте расходились бы с редактором.
    rows = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if rows and rows[-1] == "":
        rows.pop()  # перевод строки в конце файла не даёт лишней строки
    return [(_SOFT_BREAKS_RE.sub(" ", raw).rstrip(), None) for raw in rows]


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


def _row_cells(row) -> list[str]:
    """Тексты ячеек строки таблицы DOCX. Объединённая ячейка идёт один раз, знак | экранируется."""
    cells: list[str] = []
    previous = None
    for cell in row.cells:
        # python-docx отдаёт объединённую по горизонтали ячейку столько раз, сколько колонок она занимает.
        if previous is not None and cell._tc is previous:
            continue
        previous = cell._tc
        cells.append(" ".join(cell.text.split()).replace("|", "\\|"))
    return cells


def _load_docx(path: Path) -> list[tuple[str, int | None]]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = docx.Document(str(path))
    except Exception as exc:  # noqa: BLE001  python-docx бросает свои исключения на битых файлах
        raise LoadError(
            f"Не удалось разобрать DOCX, файл повреждён или это не DOCX: {path.name} ({type(exc).__name__}). "
            "Откройте его в Word и сохраните заново как DOCX или PDF."
        ) from exc
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
            for number, row in enumerate(table.rows):
                cells = _row_cells(row)
                rows.append(("| " + " | ".join(cells) + " |", None))
                if number == 0:
                    rows.append(("| " + " | ".join(["---"] * len(cells)) + " |", None))
            rows.append(("", None))
    return rows


def load_document(path: str | Path) -> Document:
    path = Path(path)
    if path.is_dir():
        raise LoadError(f"Это папка, укажите файл документа: {path}")
    if not path.is_file():
        raise LoadError(f"Файл не найден: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise LoadError(f"Не удалось прочитать файл {path}: {exc.strerror or exc}") from exc
    if not data.strip():
        raise LoadError(f"Файл пуст: {path}")

    ext = path.suffix.lower()
    if ext == ".pdf" or data[:5] == b"%PDF-":
        pdf = _load_pdf(path)
        lines = [Line(no=i, text=line.text, page=line.page, kind=line.kind, level=line.level)
                 for i, line in enumerate(pdf.lines, start=1)]
        return Document(path=path, fmt="pdf", lines=lines, sha256=hashlib.sha256(data).hexdigest(),
                        empty_pages=pdf.empty_pages, removed_headers=pdf.removed_headers,
                        fallback_pages=pdf.fallback_pages)
    if ext in (".doc", ".rtf"):
        raise LoadError(f"Формат {ext} не поддерживается. Сохраните документ как DOCX или PDF.")
    if ext == ".docx":
        fmt, rows = "docx", _load_docx(path)
    elif ext in TEXT_EXTENSIONS or not ext:
        fmt, rows = (ext.lstrip(".") or "txt"), _load_text(data, path)
    else:
        # Незнакомое расширение читаем как текст, бинарные файлы отсекаем.
        if b"\x00" in data[:4096]:
            raise LoadError(f"Формат {ext} не поддерживается. Передайте PDF, Markdown, DOCX или TXT.")
        fmt, rows = ext.lstrip("."), _load_text(data, path)

    lines = [Line(no=i, text=text, page=page) for i, (text, page) in enumerate(rows, start=1)]
    if not any(line.text.strip() for line in lines):
        raise LoadError(f"В документе нет текста: {path}")
    return Document(path=path, fmt=fmt, lines=lines, sha256=hashlib.sha256(data).hexdigest())
