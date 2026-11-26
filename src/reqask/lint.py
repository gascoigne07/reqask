"""Линтер формулировок без модели.

Ищет слова и обороты, которые ISO/IEC/IEEE 29148 (п. 5.2.7) советует избегать
в требованиях. Результат служит подсказкой для модели: решение, дефект это
или нет, она принимает сама с учётом контекста.

Отдельно ищет маркеры незаполненных мест (TODO, TBD, «уточняется»). Их ищем по всему
документу, а не только в требованиях: заглушка часто стоит во вводной части или в пустом
разделе, куда нарезка не заглядывает. Найденные строки идут подсказками в проход по набору.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol

_RULES: list[tuple[str, str]] = [
    (r"\b(быстр\w*|медленн\w*|оперативн\w*|своевременн\w*|мгновенн\w*)\b", "оценка скорости без числа"),
    (r"\b(удобн\w*|прост\w{1,3}|понятн\w*|интуитивн\w*|дружественн\w*|красив\w*)\b", "субъективная оценка"),
    (r"\b(качественн\w*|современн\w*|гибк\w*|оптимальн\w*|эффективн\w*|над[её]жн\w*|безопасн\w*)\b",
     "свойство без измеримого критерия"),
    (r"\b(достаточн\w*|приемлем\w*|разумн\w*|адекватн\w*|минимальн\w* возможн\w*)\b", "расплывчатая мера"),
    (r"\b(несколько|много|мало|примерно|около|порядка|как можно)\b", "расплывчатое количество"),
    (r"\b(при необходимости|по возможности|если возможно|как правило|обычно|иногда|желательно|может быть)\b",
     "лазейка: условие без критерия"),
    (r"(и\s+т\.\s?д\.|и\s+т\.\s?п\.|и\s+др\.|и\s+так\s+далее|и\s+другие|и\s+прочее|\bи\s+далее\b)",
     "открытый перечень"),
    (r"\bи\s*/\s*или\b", "оборот «и/или»"),
    (r"\b(fast|quick\w*|user[- ]friendly|easy|simple|flexible|robust|as appropriate|if possible|etc\.?)\b",
     "расплывчатая формулировка"),
]

PLACEHOLDER_LABEL = "незаполненное место"

# Общий словарь заглушек: служебные пометки авторов, а не слова конкретного документа.
# Латинские сокращения ищутся только заглавными: «todo» строчными бывает обычным словом.
# «заполнить» ловится только как пометка (в скобках, отдельной строкой или с «позже»):
# «пользователь должен заполнить форму» это нормальное требование.
_PLACEHOLDERS: list[re.Pattern[str]] = [
    re.compile(r"(?<![\w])(?:TODO|TBD|TBC|TBA|FIXME|XXX)(?![\w])"),
    re.compile(r"\?{3,}"),
    re.compile(r"[<\[(](?:\.{3}|…)[>\])]"),
    re.compile(r"\bto be (?:determined|defined|decided|confirmed|clarified|specified|added|completed)\b",
               re.IGNORECASE),
    re.compile(r"\b(?:уточняется|уточняются|определяется позже|в стадии уточнения)\b", re.IGNORECASE),
    re.compile(r"\bбуд(?:ет|ут) (?:определ|уточн|добавл|описан|заполн|согласован)\w*", re.IGNORECASE),
    re.compile(r"\b(?:подлеж|требу)\w* уточнени\w*", re.IGNORECASE),
    re.compile(r"\b(?:заполн|допис)\w+ (?:позже|позднее|дополнительно|потом)\b", re.IGNORECASE),
    re.compile(r"(?:^|[\[(<«\"'])\s*(?:заполнить|дописать|уточнить)\s*(?:$|[\])>»\"'.!:])",
               re.IGNORECASE | re.MULTILINE),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in _RULES]


class _Line(Protocol):
    no: int
    text: str


def _word(match: re.Match[str]) -> str:
    return " ".join(match.group(0).strip(" \t[](){}<>«»\"'.!:").split()) or match.group(0).strip()


def placeholder_marks(text: str) -> list[str]:
    """Маркеры незаполненных мест в тексте, без повторов, в порядке появления."""
    found: list[tuple[int, str]] = []
    for regex in _PLACEHOLDERS:
        for match in regex.finditer(text):
            found.append((match.start(), _word(match)))
    marks: list[str] = []
    for _, word in sorted(found):
        if word.casefold() not in {m.casefold() for m in marks}:
            marks.append(word)
    return marks


def placeholders(lines: Iterable[_Line]) -> list[tuple[int, list[str]]]:
    """Строки документа с маркерами незаполненных мест: (номер строки, маркеры)."""
    out = []
    for line in lines:
        marks = placeholder_marks(line.text) if line.text else []
        if marks:
            out.append((line.no, marks))
    return out


def lint(text: str) -> list[str]:
    """Возвращает подсказки вида «слово: причина», без повторов."""
    hints: list[str] = []
    seen: set[str] = set()
    for regex, label in _COMPILED:
        for match in regex.finditer(text):
            word = " ".join(match.group(0).split()).lower()
            if word not in seen:
                seen.add(word)
                hints.append(f"«{word}»: {label}")
    for word in placeholder_marks(text):
        if word.lower() not in seen:
            seen.add(word.lower())
            hints.append(f"«{word.lower()}»: {PLACEHOLDER_LABEL}")
    return hints
