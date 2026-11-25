"""Т-02. Чтение документов: PDF собирается в тесте (reportlab), сеть и готовые файлы не нужны."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reqask.loader import LoadError, load_document

W, H = A4


def header_footer(c, page: int, total: int) -> None:
    c.setFont("Helvetica", 9)
    c.drawString(60, H - 40, "Parking service spec, version 3")
    c.drawString(60, 30, f"Page {page} of {total}")


def grid(c, x: float, top: float, widths: list[float], heights: list[float]) -> None:
    """Таблица с линиями: pdfplumber находит её по линиям."""
    xs = [x]
    for w in widths:
        xs.append(xs[-1] + w)
    ys = [top]
    for h in heights:
        ys.append(ys[-1] - h)
    for y in ys:
        c.line(xs[0], y, xs[-1], y)
    for xx in xs:
        c.line(xx, ys[0], xx, ys[-1])


def build_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    total = 4
    # Страница 1: заголовок, перенесённая строка, перенос слова через дефис.
    header_footer(c, 1, total)
    c.setFont("Helvetica", 11)
    lines = [
        "1 Introduction",
        "The system shall store every parking session",
        "in the audit log within 2 seconds.",
        "The payment opera-",
        "tion is confirmed by the bank.",
        "Users: drivers and operators.",
    ]
    for i, text in enumerate(lines):
        c.drawString(60, H - 100 - 18 * i, text)
    c.showPage()

    # Страница 2: текст, таблица с переносом в ячейке и пустой ячейкой, текст после таблицы.
    header_footer(c, 2, total)
    c.setFont("Helvetica", 11)
    c.drawString(60, H - 100, "2.1 Tariffs")
    c.drawString(60, H - 120, "Tariff table:")
    top = H - 150
    grid(c, 60, top, [120, 200], [20, 34, 20])
    c.drawString(65, top - 14, "Zone")
    c.drawString(185, top - 14, "Price per hour")
    c.drawString(65, top - 34, "Center")
    c.drawString(185, top - 34, "300 KZT on weekdays")
    c.drawString(185, top - 48, "and 200 on weekends")
    c.drawString(65, top - 68, "Airport")
    c.drawString(60, top - 110, "Prices include VAT.")
    c.showPage()

    # Страница 3: пустая (как отсканированная вставка).
    c.showPage()

    # Страница 4: заголовок словом и нумерованный список, который не заголовок.
    header_footer(c, 4, total)
    c.setFont("Helvetica", 11)
    for i, text in enumerate(["Section 3 Limits", "1. Maximum stay", "2. Grace period"]):
        c.drawString(60, H - 100 - 18 * i, text)
    c.showPage()
    c.save()


@pytest.fixture
def pdf_doc(tmp_path: Path):
    path = tmp_path / "spec.pdf"
    build_pdf(path)
    return load_document(path)


def texts(doc):
    return [line.text for line in doc.lines]


def test_pdf_table_becomes_markdown_rows(pdf_doc):
    rows = [line for line in pdf_doc.lines if line.kind == "table"]
    assert [r.text for r in rows] == [
        "| Zone | Price per hour |",
        "| --- | --- |",
        "| Center | 300 KZT on weekdays and 200 on weekends |",  # перенос в ячейке склеен пробелом
        "| Airport |  |",  # пустая ячейка осталась пустой
    ]
    all_text = texts(pdf_doc)
    # Текст из ячеек не попал в документ второй раз, порядок текст, таблица, текст сохранён.
    assert sum("Airport" in t for t in all_text) == 1
    assert all_text.index("Tariff table:") < all_text.index("| Zone | Price per hour |") < all_text.index("Prices include VAT.")
    assert all(r.page == 2 for r in rows)


def test_pdf_headers_and_footers_removed(pdf_doc):
    joined = "\n".join(texts(pdf_doc))
    assert "Parking service spec" not in joined and "Page 1 of 4" not in joined
    assert pdf_doc.removed_headers == 6  # верхний и нижний колонтитул на трёх страницах с текстом


def test_pdf_wrapped_lines_joined(pdf_doc):
    all_text = texts(pdf_doc)
    assert "The system shall store every parking session in the audit log within 2 seconds." in all_text
    assert "The payment operation is confirmed by the bank." in all_text
    assert "Users: drivers and operators." in all_text  # строка с заглавной буквы не приклеена


def test_pdf_pages_and_empty_page(pdf_doc):
    by_text = {line.text: line.page for line in pdf_doc.lines}
    assert by_text["1 Introduction"] == 1 and by_text["Prices include VAT."] == 2 and by_text["2. Grace period"] == 4
    assert pdf_doc.empty_pages == [3]


def test_pdf_headings_by_pattern(pdf_doc):
    headings = [(line.text, line.level) for line in pdf_doc.lines if line.kind == "heading"]
    assert headings == [("1 Introduction", 1), ("2.1 Tariffs", 2), ("Section 3 Limits", 1)]
    assert pdf_doc.section_path(pdf_doc.lines[-1].no).endswith("Section 3 Limits")
    assert "2.1 Tariffs (строка" in pdf_doc.outline()


def test_scan_pdf_is_rejected(tmp_path):
    path = tmp_path / "scan.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(60, H - 100, "Cover page")
    c.showPage()
    c.showPage()
    c.showPage()
    c.save()
    with pytest.raises(LoadError, match="скан"):
        load_document(path)


def test_encrypted_and_broken_pdf(tmp_path):
    locked = tmp_path / "locked.pdf"
    c = canvas.Canvas(str(locked), pagesize=A4, encrypt="secret")
    c.drawString(60, H - 100, "Secret")
    c.showPage()
    c.save()
    with pytest.raises(LoadError, match="паролем"):
        load_document(locked)

    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.4\n garbage without objects")
    with pytest.raises(LoadError, match="PDF"):
        load_document(broken)


def test_txt_cp1251_and_diagnostics(tmp_path):
    txt = tmp_path / "spec.txt"
    txt.write_bytes("Система хранит заявку 30 дней.".encode("cp1251"))
    assert texts(load_document(txt)) == ["Система хранит заявку 30 дней."]

    old = tmp_path / "spec.doc"
    old.write_bytes(b"\xd0\xcf\x11\xe0 binary")
    with pytest.raises(LoadError, match="DOCX"):
        load_document(old)
    (tmp_path / "empty.md").write_text("  \n", encoding="utf-8")
    with pytest.raises(LoadError, match="пуст"):
        load_document(tmp_path / "empty.md")
    with pytest.raises(LoadError, match="не найден"):
        load_document(tmp_path / "missing.pdf")
