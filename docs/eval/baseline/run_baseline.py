"""Базовый замер: одна модель, один запрос, без конвейера.

Запуск: uv run python docs/eval/baseline/run_baseline.py --env-file .env.anthropic
Результат: opus-single-prompt.md (ответ как есть) и opus-single-prompt.meta.json.
"""
import argparse
import datetime
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
MODEL = "claude-opus-5-5"
BASE_URL = "https://api.anthropic.com/v1/"

PROMPT = """Ты опытный ревьюер требований к программным системам. Ниже документ требований, строки пронумерованы.

Проверь его по ISO/IEC/IEEE 29148:2018 (п. 5.2.5 о свойствах отдельного требования и п. 5.2.6 о свойствах набора требований) и по IEEE 830 (п. 4.3, характеристики хорошей спецификации): полнота, непротиворечивость, однозначность, проверяемость, атомарность, осуществимость, необходимость, прослеживаемость, корректность.

Напиши отчёт на русском языке в Markdown, в таком составе:
1. Паспорт: документ, число строк, число найденных требований, число замечаний по уровням.
2. Таблица нарезки: все требования документа (идентификатор, строки, краткая суть).
3. Проверка каждого требования: какие критерии нарушены и почему.
4. Проверка набора требований целиком: противоречия, пробелы, дубли, расхождения между разделами.
5. Сводка: критичные дефекты с пояснением.
6. Итог: можно ли начинать разработку по этому документу.

У каждого замечания дай дословную цитату из документа и номер строки, уровень CRITICAL, MAJOR или MINOR и как исправить.
В конце задай автору документа до 15 уточняющих вопросов: по каждому дай варианты ответа и последствия каждого варианта.

Документ:

{doc}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=".env")
    ap.add_argument("--input", default=str(ROOT / "input" / "requirements.md"))
    args = ap.parse_args()
    load_dotenv(args.env_file)
    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    doc = "\n".join(f"{i:>4} | {t}" for i, t in enumerate(lines, 1))
    client = OpenAI(api_key=os.environ["ANTHROPIC_API_KEY"], base_url=BASE_URL)
    t0 = time.time()
    r = client.chat.completions.create(
        model=MODEL, max_tokens=32000,
        messages=[{"role": "user", "content": PROMPT.format(doc=doc)}])
    secs = time.time() - t0
    (OUT / "opus-single-prompt.md").write_text(r.choices[0].message.content or "", encoding="utf-8")
    meta = {
        "model": MODEL,
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "seconds": round(secs, 1),
        "prompt_tokens": r.usage.prompt_tokens,
        "completion_tokens": r.usage.completion_tokens,
        "finish_reason": r.choices[0].finish_reason,
    }
    (OUT / "opus-single-prompt.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(meta)


if __name__ == "__main__":
    main()
