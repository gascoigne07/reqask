"""Проверка цитат: каждая цитата модели должна находиться в тексте документа.

Модель может ошибиться в цитате или выдумать её. Здесь цитата сверяется
с документом без участия модели: точное вхождение после нормализации
(в строку или в склейку соседних строк), затем поиск близкого фрагмента.
Цитата короче четырёх символов сверяется по номеру строки с допуском в две строки.
Что не нашлось, получает статус missing, и замечание уходит в карантин.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from difflib import SequenceMatcher

from .loader import Document

_TRANS = str.maketrans(
    {
        " ": " ", " ": " ", " ": " ", "​": "",
        "«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
        "‘": "'", "’": "'",
        "—": "-", "–": "-", "−": "-", "‑": "-",
        "ё": "е", "Ё": "Е",
    }
)
_MARKUP_RE = re.compile(r"[*`_|\\]")
_SPACE_RE = re.compile(r"\s+")
_ELLIPSIS_RE = re.compile(r"\s*(?:\.{3,}|…|\[\s*\.{3}\s*\])\s*")

MIN_QUOTE_LEN = 4
MIN_FUZZY_LEN = 12
FUZZY_SHARE = 0.8
LINE_TOLERANCE = 2
MAX_FUZZY_HAYSTACK = 200_000


def normalize(text: str) -> str:
    """Убирает различия, которые не меняют смысл: разметку, регистр, виды кавычек и пробелов."""
    text = text.translate(_TRANS)
    text = _MARKUP_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip().casefold()


def clean_quote(quote: str) -> str:
    quote = quote.strip()
    quote = re.sub(r"^(?:\.{3,}|…)\s*", "", quote)
    quote = re.sub(r"\s*(?:\.{3,}|…)$", "", quote)
    if len(quote) >= 2 and quote[0] in "«\"'“" and quote[-1] in "»\"'”":
        quote = quote[1:-1].strip()
    return quote


class TextIndex:
    def __init__(self, doc: Document):
        self._doc = doc
        self._starts: list[int] = []
        self._nos: list[int] = []
        parts: list[str] = []
        pos = 0
        for line in doc.lines:
            norm = normalize(line.text)
            if not norm:
                continue
            self._starts.append(pos)
            self._nos.append(line.no)
            parts.append(norm)
            pos += len(norm) + 1
        self.text = " ".join(parts)

    def _span(self, start: int | None, end: int | None) -> tuple[int, int] | None:
        if start is None or end is None:
            return (0, len(self.text))
        i = bisect_left(self._nos, start)
        j = bisect_right(self._nos, end)
        if i >= j:
            return None
        stop = self._starts[j] - 1 if j < len(self._starts) else len(self.text)
        return (self._starts[i], stop)

    def _line_at(self, offset: int) -> int:
        return self._nos[max(0, bisect_right(self._starts, offset) - 1)]

    def find(self, quote: str, start: int | None = None, end: int | None = None) -> int | None:
        """Номер строки, где начинается цитата, либо None.

        Цитата с многоточием внутри проверяется по частям: все части
        должны идти в документе в том же порядке.
        """
        span = self._span(start, end)
        if span is None:
            return None
        parts = [normalize(p) for p in _ELLIPSIS_RE.split(clean_quote(quote))]
        parts = [p for p in parts if len(p) >= MIN_QUOTE_LEN]
        if not parts:
            return None
        cursor, stop = span
        first: int | None = None
        for part in parts:
            pos = self.text.find(part, cursor, stop)
            if pos < 0:
                return None
            if first is None:
                first = pos
            cursor = pos + len(part)
        return self._line_at(first) if first is not None else None

    def find_short(self, quote: str, line: int | None, tolerance: int = LINE_TOLERANCE) -> int | None:
        """Короткая цитата («GET», «5») ищется только рядом со строкой, которую назвала модель."""
        norm = normalize(clean_quote(quote))
        if not norm or line is None:
            return None
        span = self._span(line - tolerance, line + tolerance)
        if span is None:
            return None
        pos = self.text.find(norm, span[0], span[1])
        return self._line_at(pos) if pos >= 0 else None

    @staticmethod
    def is_short(quote: str) -> bool:
        return len(normalize(clean_quote(quote))) < MIN_QUOTE_LEN

    def fuzzy(self, quote: str, start: int | None = None, end: int | None = None) -> int | None:
        """Строка с самым длинным общим фрагментом, если он покрывает большую часть цитаты."""
        span = self._span(start, end)
        norm = normalize(clean_quote(quote))
        if span is None or len(norm) < MIN_FUZZY_LEN or span[1] - span[0] > MAX_FUZZY_HAYSTACK:
            return None
        hay = self.text[span[0] : span[1]]
        match = SequenceMatcher(None, norm, hay, autojunk=False).find_longest_match(0, len(norm), 0, len(hay))
        if match.size >= max(MIN_FUZZY_LEN, int(FUZZY_SHARE * len(norm))):
            return self._line_at(span[0] + match.b)
        return None


def distinct_quotes(evidence: list, limit: int | None = None) -> list:
    """Подтверждённые цитаты без повторов, в исходном порядке.

    Повтором считается цитата той же строки, которая после нормализации совпадает
    с другой или целиком входит в неё («доступ запрещен» внутри «Ответ ... доступ запрещен.»).
    Остаётся более длинная. Элементы: объекты с полями quote, line, status.
    """
    kept: list = []
    keys: list[tuple[int, str]] = []
    for e in evidence:
        if getattr(e, "status", "exact") == "missing":
            continue
        key = (e.line or 0, normalize(clean_quote(e.quote)).rstrip(". "))
        if not key[1]:
            continue
        if any(k[0] == key[0] and key[1] in k[1] for k in keys):
            continue
        # Новая цитата длиннее и содержит уже взятую: заменяет её на том же месте.
        for i, k in enumerate(keys):
            if k[0] == key[0] and k[1] in key[1]:
                kept[i], keys[i] = e, key
                break
        else:
            kept.append(e)
            keys.append(key)
    # После замены одна длинная цитата могла встать на два места.
    out, seen = [], set()
    for e, k in zip(kept, keys):
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out[:limit] if limit else out
