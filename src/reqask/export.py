"""Выгрузка замечаний в CSV для трекера задач, без модели и ключа.

Команда: reqask --export-csv report.json --output tickets.csv.
В файл идут только действующие замечания: не снятые критиком, не слитые в другое и не из карантина.
Какие замечания действующие, решает та же функция, что собирает разделы отчёта.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .criteria import SEVERITY_ORDER
from .report import _active, _gist
from .schemas import Finding, RunResult

COLUMNS = ("Summary", "Issue Type", "Priority", "Labels", "Description",
           "Severity", "Finding ID", "Requirements", "Lines", "Criterion")
PRIORITY = {"CRITICAL": "Highest", "MAJOR": "High", "MINOR": "Low"}
# Ячейка, которая начинается с этих знаков, откроется в Excel как формула.
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
SUMMARY_LIMIT = 120


def protect(value: str) -> str:
    """Текст приходит из документа и от модели: ячейку, похожую на формулу, начинаем с апострофа."""
    return "'" + value if value.startswith(FORMULA_START) else value


def _confirmed(f: Finding) -> list:
    """Цитаты, которые сверка нашла в документе. Ненайденные в выгрузку не идут."""
    return [e for e in f.evidence if getattr(e, "status", "exact") != "missing"]


def _lines(f: Finding) -> list[int]:
    return sorted({e.line for e in _confirmed(f) if e.line is not None})


def _description(f: Finding) -> str:
    parts = [f.problem.strip()]
    quotes = [f"строка {e.line}: «{e.quote.strip()}»" if e.line is not None else f"«{e.quote.strip()}»"
              for e in _confirmed(f) if e.quote.strip()]
    if quotes:
        parts.append("Цитаты:\n" + "\n".join(quotes))
    if f.question:
        parts.append(f"Вопрос автору: {f.question.strip()}")
    if f.recommendation.strip():
        parts.append(f"Предложенное исправление: {f.recommendation.strip()}")
    return "\n\n".join(p for p in parts if p)


def rows(result: RunResult) -> list[dict[str, str]]:
    """Одна строка на действующее замечание: сначала CRITICAL, потом MAJOR и MINOR, внутри уровня как в отчёте."""
    active = [f for f in result.findings if _active(f)]
    active.sort(key=lambda f: SEVERITY_ORDER[f.severity])  # сортировка устойчивая: порядок отчёта сохраняется
    return [{
        "Summary": f"{f.id}: {_gist(f, SUMMARY_LIMIT)}",
        "Issue Type": "Task",
        "Priority": PRIORITY[f.severity],
        "Labels": f"reqask {f.severity.lower()} {f.criterion.lower()}",
        "Description": _description(f),
        "Severity": f.severity,
        "Finding ID": f.id,
        "Requirements": ", ".join(f.req_ids),
        "Lines": ", ".join(str(n) for n in _lines(f)),
        "Criterion": f.criterion,
    } for f in active]


def write_csv(result: RunResult, path: Path) -> int:
    """Пишет файл и возвращает число строк. Все поля в кавычках, кодировка utf-8-sig, чтобы Excel видел кириллицу."""
    data = rows(result)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        for row in data:
            writer.writerow({k: protect(v) for k, v in row.items()})
    return len(data)
