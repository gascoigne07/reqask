# Чужой документ для проверки агента

`pure-puget-sound.pdf`: спецификация требований к доработкам Moodle для университета Пьюджет-Саунд (2007, английский, 14 страниц, 15 таблиц). Документ взят из набора PURE как есть, без правок: файл `req/2007 - puget sound.pdf` из архива `requirements.zip`.

Зачем он здесь: показать, что агент работает на документе другого автора, из другой области и на другом языке, и проверить чтение настоящего PDF. Под этот документ промпты и правила не настраивались.

Источник: Alessio Ferrari, Giorgio Oronzo Spagnolo, Stefania Gnesi. PURE: a Dataset of Public Requirements Documents. Zenodo, 2018. https://doi.org/10.5281/zenodo.1414117. Набор опубликован под лицензией CC BY 4.0.

SHA-256 файла: `bc8fea411b7e40f114e453f09451cd3777da5f218f0d1414fbb640ec5ed9dce8`.

Запуск:

```bash
uv run main.py --input examples/pure-puget-sound.pdf --output reports/pure-puget-sound.md
```
