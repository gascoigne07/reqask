"""Командная строка: reqask --input <документ> --output <отчёт.md>."""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

from .config import ConfigError, load_settings
from .llm import LLMClient, LLMError, LLMFatal
from .loader import LoadError, load_document
from .pipeline import DECISIONS, Pipeline
from .schemas import INACTIVE_STATUSES, StepStat
from .report import render, render_questions
from .version import agent_version


# Коды возврата (К-11).
EXIT_OK = 0          # отчёт записан полностью
EXIT_NO_MODEL = 1    # модель недоступна, отчёта нет
EXIT_INPUT = 2       # ошибка входа или настроек
EXIT_PARTIAL = 3     # отчёт записан, но неполный
EXIT_CRITICAL = 10   # с --fail-on-critical: вердикт «Не рекомендуется начинать»
EXIT_INTERRUPTED = 130
REPORT_SUFFIXES = (".md", ".markdown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reqask",
        description="Статическая проверка документа требований по ISO/IEC/IEEE 29148 и IEEE 830.",
        epilog="Коды возврата: 0 отчёт полный, 3 отчёт неполный, 2 ошибка входа или настроек, "
               "1 модель недоступна, 130 прервано, 10 вердикт «Не рекомендуется» (только с --fail-on-critical).",
    )
    parser.add_argument("--input", "-i", help="документ требований: PDF, Markdown, DOCX или TXT")
    parser.add_argument("--output", "-o", help="куда записать отчёт, файл .md")
    parser.add_argument("--check", action="store_true",
                        help="проверить ключ и модель одним коротким вызовом, без документа")
    parser.add_argument("--model", help="модель, если нужно переопределить значение из .env")
    parser.add_argument("--env-file", help="путь к файлу с ключом (по умолчанию .env в текущей папке)")
    parser.add_argument("--batch-size", type=int, help="сколько требований проверять одним запросом")
    parser.add_argument("--no-cache", action="store_true", help="не брать ответы модели из кэша и не писать в него")
    parser.add_argument("--no-critic", action="store_true", help="не запускать шаг критика (перепроверку CRITICAL и MAJOR)")
    parser.add_argument("--no-edge", action="store_true",
                        help="не запускать третий проход шага 5 (неописанные граничные случаи)")
    parser.add_argument("--no-json", action="store_true", help="не сохранять report.json рядом с отчётом")
    parser.add_argument("--fail-on-critical", action="store_true",
                        help="код возврата 10, если вердикт «Не рекомендуется начинать» (для CI)")
    parser.add_argument("--quiet", "-q", action="store_true", help="не печатать ход прогона")
    return parser


def _error(text: str) -> None:
    print(f"Ошибка: {text}", file=sys.stderr)


def _check_output(path: str) -> Path:
    """Отчёт пишется только в Markdown (Ч-11). Проверка идёт до чтения входа и до вызовов модели."""
    output = Path(path)
    if output.is_dir():
        raise ConfigError(f"«{output}» это папка, укажите файл, например {output / 'report.md'}")
    if output.suffix.lower() not in REPORT_SUFFIXES:
        raise ConfigError(
            f"отчёт пишется в Markdown, а указан файл «{output.name}». Укажите путь с расширением .md, "
            "например reports/report.md. Нужен PDF: откройте .md в редакторе или на GitHub и сохраните в PDF."
        )
    return output


def _make_output_dir(output: Path) -> None:
    """Папку отчёта создаём после чтения входа, но до вызовов модели, чтобы не потерять прогон на записи."""
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"не удалось создать папку для отчёта «{output.parent}»: {exc}") from exc


def run_check(settings, log) -> int:
    """--check: ключ, модель, режим JSON и уровень рассуждения одним вызовом (М-14).

    Идёт по той же цепочке моделей, что и прогон (М-10): основная не ответила, пробуется запасная.
    """
    # Проверка короткая: ждать ответ дольше минуты нет смысла, зависшая модель должна быть видна сразу.
    chain = [settings.model, *[m for m in settings.fallback_models if m != settings.model]]
    llm = LLMClient(settings.with_overrides(timeout_sec=min(settings.timeout_sec, 60.0)), log)
    print(f"Провайдер: {settings.provider}. Модель: {settings.model}. Адрес: {settings.base_url or 'по умолчанию'}")
    if len(chain) > 1:
        print("Запасные модели: " + ", ".join(chain[1:]) + ".")
    try:
        info = llm.check()
    except LLMError as exc:
        print(f"Проверка не прошла: {exc}", file=sys.stderr)
        if len(chain) > 1:
            print("Не ответила ни одна модель цепочки: " + ", ".join(chain) + ".", file=sys.stderr)
        return EXIT_NO_MODEL
    answered = llm.model
    print(f"Ключ принят, отвечает модель {answered}.")
    if answered != settings.model:
        print(f"Основная модель не отвечает, прогон пойдёт на {answered}.")
    print(f"Режим JSON: {info['json_mode']}. Уровень рассуждения: {info['reasoning']}. "
          f"Лимит вывода max_tokens: {'принят' if info['max_tokens'] else 'не принят'}.")
    print(f"Время вызова: {info['seconds']} с, токенов: {info['tokens']}.")
    for note in info["notes"]:
        print(f"{'Переход' if 'перехожу на запасную' in note else 'Отказ провайдера'}: {note}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Любая непредвиденная ошибка даёт сообщение и код 1, трассировка только при REQASK_DEBUG=1."""
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print("Прогон прерван.", file=sys.stderr)
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001  последний рубеж: человек видит причину, а не трассировку
        debug = os.getenv("REQASK_DEBUG", "").strip() not in ("", "0")
        if debug:
            traceback.print_exc()
        print(f"Внутренняя ошибка агента: {type(exc).__name__}: {exc}", file=sys.stderr)
        if not debug:
            print("Трассировка: запустите снова с REQASK_DEBUG=1.", file=sys.stderr)
        return EXIT_NO_MODEL


def _main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    t0 = time.monotonic()

    def log(message: str) -> None:
        if not args.quiet:
            print(f"[{time.monotonic() - t0:6.1f} с] {message}", file=sys.stderr, flush=True)

    try:
        settings = None
        if args.check:
            settings = load_settings(args.env_file).with_overrides(model=args.model)
            return run_check(settings, log)
        if not args.input or not args.output:
            parser.print_usage(sys.stderr)
            _error("нужны --input и --output (или --check для проверки ключа)")
            return EXIT_INPUT
        if args.batch_size is not None and args.batch_size < 1:
            _error(f"--batch-size должен быть 1 или больше, указано {args.batch_size}")
            return EXIT_INPUT
        output = _check_output(args.output)
        doc = load_document(args.input)
        settings = load_settings(args.env_file).with_overrides(model=args.model, batch_size=args.batch_size)
        _make_output_dir(output)
        if args.no_cache:
            settings = settings.with_overrides(cache_dir="")
        if args.no_critic:
            settings = settings.with_overrides(critic=False)
        if args.no_edge:
            settings = settings.with_overrides(edge=False)
        log(f"Документ: {doc.name} ({doc.fmt}, строк: {doc.n}). Модель: {settings.model} ({settings.provider})")
        llm = LLMClient(settings, log)
        result = Pipeline(llm, settings, log).run(doc, agent_version())
    except (LoadError, ConfigError) as exc:
        _error(str(exc))
        return EXIT_INPUT
    except LLMFatal as exc:
        # Ключ не принят или модель не найдена на первом же вызове: отчёт не пишется (К-10).
        print(f"Модель недоступна, отчёт не записан. {exc}", file=sys.stderr)
        return EXIT_NO_MODEL
    except LLMError as exc:
        print(f"Ошибка модели: {exc}", file=sys.stderr)
        return EXIT_NO_MODEL
    except KeyboardInterrupt:
        print("Прогон прерван.", file=sys.stderr)
        return EXIT_INTERRUPTED

    questions_path = output.with_name(output.stem + ".questions.md")
    log("Шаг 9. Отчёт")
    t9 = time.monotonic()
    written = [output, questions_path] + ([] if args.no_json else [output.with_suffix(".json")])
    result.steps.append(StepStat(
        number="9", name="Отчёт", summary="записаны: " + ", ".join(p.name for p in written),
    ))
    try:
        output.write_text(render(result), encoding="utf-8")
        questions_path.write_text(render_questions(result), encoding="utf-8")
        if not args.no_json:
            output.with_suffix(".json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    except OSError as exc:
        _error(f"не удалось записать отчёт: {exc}")
        return EXIT_INPUT
    log(f"    итог шага: {result.steps[-1].summary} ({round(time.monotonic() - t9, 1)} с)")

    severity = Counter(f.severity for f in result.findings if f.status not in INACTIVE_STATUSES)
    log(
        f"Готово. Требований: {len(result.requirements)}, замечаний: {sum(severity.values())} "
        f"(CRITICAL {severity.get('CRITICAL', 0)}, MAJOR {severity.get('MAJOR', 0)}, MINOR {severity.get('MINOR', 0)})"
    )
    print(f"Отчёт: {output}\nВопросы автору: {questions_path}")
    if is_incomplete(result):
        if not result.requirements and not result.failed_steps:
            print("Требования не найдены: все строки с текстом отмечены как не требования. "
                  "Проверьте, что передан документ с требованиями.", file=sys.stderr)
        else:
            print("Отчёт неполный: часть шагов не выполнена, причина в начале отчёта.", file=sys.stderr)
        return EXIT_PARTIAL
    if args.fail_on_critical and result.verdict.decision == DECISIONS[0]:
        return EXIT_CRITICAL
    return EXIT_OK


def is_incomplete(result) -> bool:
    """Отчёт неполный (код 3): фатальная ошибка, сбой шага, требования без проверки или требований нет совсем."""
    return bool(result.fatal or result.failed_steps or result.unreviewed or not result.requirements
                or any(s.status in ("failed", "degraded") for s in result.steps))


if __name__ == "__main__":
    raise SystemExit(main())
