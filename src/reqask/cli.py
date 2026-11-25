"""Командная строка: reqask --input <документ> --output <отчёт.md>."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

from .config import ConfigError, load_settings
from .llm import LLMClient, LLMError
from .loader import LoadError, load_document
from .pipeline import Pipeline
from .schemas import StepStat
from .report import render, render_questions
from .version import agent_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqask",
        description="Статическая проверка документа требований по ISO/IEC/IEEE 29148 и IEEE 830.",
    )
    parser.add_argument("--input", "-i", required=True, help="документ требований: PDF, Markdown, DOCX или TXT")
    parser.add_argument("--output", "-o", required=True, help="куда записать отчёт (Markdown)")
    parser.add_argument("--model", help="модель, если нужно переопределить значение из .env")
    parser.add_argument("--env-file", help="путь к файлу с ключом (по умолчанию .env в текущей папке)")
    parser.add_argument("--batch-size", type=int, help="сколько требований проверять одним запросом")
    parser.add_argument("--no-cache", action="store_true", help="не брать ответы модели из кэша и не писать в него")
    parser.add_argument("--no-json", action="store_true", help="не сохранять report.json рядом с отчётом")
    parser.add_argument("--quiet", "-q", action="store_true", help="не печатать ход прогона")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    t0 = time.monotonic()

    def log(message: str) -> None:
        if not args.quiet:
            print(f"[{time.monotonic() - t0:6.1f} с] {message}", file=sys.stderr, flush=True)

    try:
        doc = load_document(args.input)
        settings = load_settings(args.env_file).with_overrides(model=args.model, batch_size=args.batch_size)
        if args.no_cache:
            settings = settings.with_overrides(cache_dir="")
        log(f"Документ: {doc.name} ({doc.fmt}, строк: {doc.n}). Модель: {settings.model} ({settings.provider})")
        llm = LLMClient(settings, log)
        result = Pipeline(llm, settings, log).run(doc, agent_version())
    except (LoadError, ConfigError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    except LLMError as exc:
        print(f"Ошибка модели: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Прогон прерван.", file=sys.stderr)
        return 130

    output = Path(args.output)
    questions_path = output.with_name(output.stem + ".questions.md")
    log("Шаг 9. Отчёт")
    t9 = time.monotonic()
    written = [output, questions_path] + ([] if args.no_json else [output.with_suffix(".json")])
    result.steps.append(StepStat(
        number="9", name="Отчёт", summary="записаны: " + ", ".join(p.name for p in written),
    ))
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(result), encoding="utf-8")
        questions_path.write_text(render_questions(result), encoding="utf-8")
        if not args.no_json:
            output.with_suffix(".json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"Ошибка записи отчёта: {exc}", file=sys.stderr)
        return 2
    log(f"    итог шага: {result.steps[-1].summary} ({round(time.monotonic() - t9, 1)} с)")

    severity = Counter(f.severity for f in result.findings)
    log(
        f"Готово. Требований: {len(result.requirements)}, нарушений: {len(result.findings)} "
        f"(CRITICAL {severity.get('CRITICAL', 0)}, MAJOR {severity.get('MAJOR', 0)}, MINOR {severity.get('MINOR', 0)})"
    )
    if result.failed_steps or result.unreviewed:
        log("Внимание: часть шагов не выполнена, подробности в паспорте отчёта.")
    print(f"Отчёт: {output}\nВопросы автору: {questions_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
