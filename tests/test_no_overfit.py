"""Т-08. Код, промпты и правила не привязаны к выданному документу.

Тест берёт из input/requirements.md то, что отличает именно этот документ: идентификаторы
требований, пути, имена полей латиницей, числа с единицами. Ни одно из них не должно стоять
в промптах, линтере и справочнике критериев. Список дефектов документа нигде не хранится.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "input" / "requirements.md"
# Проверяем все модули агента, а не только промпты и правила: привязки к выданному
# документу не должно быть нигде в коде. Список берётся из папки, новые модули войдут сами.
CHECKED = sorted(p.name for p in (ROOT / "src" / "reqask").glob("*.py"))

# Общие технические слова: встречаются в любом документе требований, привязкой не считаются.
# Сюда же обычные слова из словаря кода (path, message, body, field): документ их тоже
# содержит как подписи полей («Path-параметры», «Request body»), но к выданному документу
# они не привязывают. Доменные токены (saveLimit, alerts, cardId, limit_kzt, тиын) не общие
# и остаются под проверкой.
COMMON = {
    "api", "http", "https", "json", "id", "url", "pdf", "rest", "get", "post", "put", "delete",
    "curl", "data", "integer", "string", "boolean", "result", "text", "type", "error", "true", "false",
    "path", "message", "body", "field",
}
UNITS = r"(?:₸|KZT|тенге|руб\w*|сек\w*|мин\w*|мс|час\w*|дн\w*|%|МБ|КБ|ГБ)"


def _markers(doc: str) -> set[str]:
    latin = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", doc) if w.casefold() not in COMMON}
    paths = set(re.findall(r"/[A-Za-z][\w/]+", doc))
    ids = set(re.findall(r"\b[А-ЯЁA-Z]{1,4}-\d+(?:\.\d+)*\b", doc))
    numbers = {" ".join(m.group(0).split()) for m in re.finditer(rf"\d[\d\s]*\s?{UNITS}", doc)}
    return latin | paths | ids | numbers


@pytest.mark.skipif(not DOC.exists(), reason="выданного документа нет в этой копии")
@pytest.mark.parametrize("name", CHECKED)
def test_no_given_document_markers_in_sources(name):
    markers = _markers(DOC.read_text(encoding="utf-8"))
    assert len(markers) > 10  # тест на самом деле что-то сравнивает
    source = (ROOT / "src" / "reqask" / name).read_text(encoding="utf-8")
    source = " ".join(source.split())
    found = sorted(m for m in markers if re.search(rf"(?<![\w/]){re.escape(m)}(?![\w])", source))
    assert found == [], f"{name}: {found}"
