"""Чтение PDF: заголовки, списки, служебные символы. Без сети и без модели."""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reqask.pdfread import PdfLine, _cell, _clean, _mark_headings, read_pdf


def headings(texts: list[str]) -> list[str]:
    lines = [PdfLine(text, 1) for text in texts]
    _mark_headings(lines)
    return [line.text for line in lines if line.kind == "heading"]


def test_section_heading_before_numbered_list():
    # «6. Критерии приёмки» продолжает «5. ...», под ним список с «1.»: это заголовок раздела.
    texts = [
        "5. Нефункциональные требования",
        "НФТ-04. Одновременно в системе работают до 60 пользователей.",
        "6. Acceptance criteria",
        "1. Позиция создаётся с артикулом из 8 цифр.",
        "2. Повторный артикул отклоняется.",
    ]
    assert headings(texts) == ["5. Нефункциональные требования", "6. Acceptance criteria"]


def test_numbered_list_stays_list():
    # Короткие пункты без точки похожи на заголовки, но соседи продолжают нумерацию.
    texts = ["2. Термины", "Текст раздела.", "3. Роли", "1. Кладовщик", "2. Старший кладовщик", "3. Администратор"]
    assert headings(texts) == ["2. Термины", "3. Роли"]
    # Номер продолжает раздел, но следующий пункт идёт N+1: это список, как раньше.
    texts = ["2. Термины", "Текст раздела.", "3. Позиция", "4. Ячейка"]
    assert headings(texts) == ["2. Термины"]
    # Предыдущая строка стоит в той же нумерации (N-1): это продолжение списка.
    texts = ["1. Общие сведения", "Текст.", "2. Термины", "1. Позиция", "2. Ячейка", "3. Резерв", "1. Пункт."]
    assert headings(texts) == ["1. Общие сведения", "2. Термины"]
    # Без заголовков вокруг список из одних «1. Текст», «2. Текст» заголовков не даёт.
    assert headings(["1. Введение", "2. Цели", "3. Термины"]) == []


def test_cid_glyphs_cleaned():
    assert _clean("(cid:127) Позиция: товар") == "• Позиция: товар"
    assert _clean("(cid:127)(cid:3)Пункт") == "• Пункт"
    assert _clean("Срок(cid:3)годности") == "Срок годности"
    assert _clean("значение (cid:5), далее") == "значение , далее"
    assert _cell("(cid:127) пункт\nв ячейке") == "• пункт в ячейке"
    assert _clean("без глифов") == "без глифов"


def test_pdf_bullets_without_unicode_map(tmp_path: Path):
    """Маркер «•» стандартным шрифтом Helvetica на странице с таблицей: pdfplumber отдаёт (cid:127)."""
    path = tmp_path / "bullets.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 11)
    c.drawString(60, 780, "1 Terms")
    c.drawString(60, 760, "• Item: one article in the catalogue.")
    c.drawString(60, 745, "• Cell: storage place on a rack.")
    # Таблица, чтобы страницу читал pdfplumber.
    top, xs = 700, [60, 200, 340]
    for y in (top, top - 20, top - 40):
        c.line(xs[0], y, xs[-1], y)
    for x in xs:
        c.line(x, top, x, top - 40)
    c.drawString(65, top - 15, "Field")
    c.drawString(205, top - 15, "Type")
    c.drawString(65, top - 35, "sku")
    c.drawString(205, top - 35, "string")
    c.save()
    texts = [line.text for line in read_pdf(path).lines]
    assert not any("(cid:" in text for text in texts)
    assert "• Item: one article in the catalogue." in texts
