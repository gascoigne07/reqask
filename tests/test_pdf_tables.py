"""Таблицы PDF: подложки под текстом, перенос в ячейке, таблица через границу страницы.

PDF собирается в тесте (reportlab), шрифт Helvetica: кириллицы в нём нет, поэтому текст латиницей,
как в test_loader.py.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reqask.loader import load_document
from reqask.pdfread import read_pdf

W, H = A4
LINE = 14  # шаг строки текста в ячейке


def header_footer(c, page: int, total: int) -> None:
    c.setFont("Helvetica", 9)
    c.drawString(60, H - 40, "Clinic portal spec, version 2")
    c.drawString(60, 30, f"Page {page} of {total}")


def draw_table(c, top: float, widths: list[float], rows: list[list[list[str]]], word_style: bool = False) -> float:
    """Таблица с рамкой; ячейка задаётся списком строк текста. Возвращает низ таблицы.

    word_style: рамка из тонких залитых прямоугольников и белая подложка под каждой строкой
    текста, как в PDF, который выдаёт Word.
    """
    xs = [60.0]
    for w in widths:
        xs.append(xs[-1] + w)
    ys = [top]
    for row in rows:
        ys.append(ys[-1] - LINE * max(len(cell) for cell in row) - 8)
    c.setFont("Helvetica", 10)
    for r, row in enumerate(rows):
        for col, cell in enumerate(row):
            for i, text in enumerate(cell):
                y = ys[r] - 14 - LINE * i
                if word_style:
                    c.setFillColorRGB(1, 1, 1)
                    c.rect(xs[col] + 4, y - 4, widths[col] - 8, LINE, stroke=0, fill=1)
                    c.setFillColorRGB(0, 0, 0)
                c.drawString(xs[col] + 6, y, text)
    c.setFillColorRGB(0, 0, 0)
    for y in ys:
        if word_style:
            c.rect(xs[0], y - 0.25, xs[-1] - xs[0], 0.5, stroke=0, fill=1)
        else:
            c.line(xs[0], y, xs[-1], y)
    for x in xs:
        if word_style:
            c.rect(x - 0.25, ys[-1], 0.5, ys[0] - ys[-1], stroke=0, fill=1)
        else:
            c.line(x, ys[0], x, ys[-1])
    return ys[-1]


def body(c, top: float, lines: list[str]) -> None:
    c.setFont("Helvetica", 11)
    for i, text in enumerate(lines):
        c.drawString(60, top - 18 * i, text)


def table_rows(doc):
    return [line for line in doc.lines if line.kind == "table"]


def split_pdf(path: Path, first: list, second: list, widths_second: list[float] | None = None,
              between: list[str] | None = None, word_style: bool = False) -> None:
    """Три страницы: текст и таблица у низа первой, продолжение у верха второй, текст на третьей."""
    widths = [130, 300]
    c = canvas.Canvas(str(path), pagesize=A4)
    header_footer(c, 1, 3)
    body(c, H - 100, ["1 Appointments", "Table 1 Booking rules"])
    # Таблица дорисована почти до нижнего поля: низ около 0.85 высоты страницы.
    height = sum(LINE * max(len(cell) for cell in row) + 8 for row in first)
    draw_table(c, 130 + height, widths, first, word_style)
    c.showPage()
    header_footer(c, 2, 3)
    top = H - 70
    if between:
        body(c, top, between)
        top -= 18 * len(between) + 10
    bottom = draw_table(c, top, widths_second or widths, second, word_style)
    body(c, bottom - 30, ["Bookings are stored for one year."])
    c.showPage()
    header_footer(c, 3, 3)
    body(c, H - 100, ["2 Limits", "A patient can hold three bookings."])
    c.showPage()
    c.save()


HEADER = [["Rule"], ["Description"]]


def test_word_backdrops_do_not_split_cells(tmp_path):
    # Подложка под каждой строкой текста не даёт лишних столбцов и строк: перенос в ячейке,
    # в том числе через дефис, остаётся одной ячейкой одной строки таблицы.
    path = tmp_path / "word.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    body(c, H - 100, ["Booking rules:"])
    draw_table(c, H - 130, [130, 300], [
        HEADER,
        [["Cancel"], ["A patient can cancel a booking", "up to two hours before the visit."]],
        [["Remind", "by SMS"], ["The portal sends a remin-", "der one day before the visit."]],
    ], word_style=True)
    c.showPage()
    c.save()

    doc = load_document(path)
    assert [r.text for r in table_rows(doc)] == [
        "| Rule | Description |",
        "| --- | --- |",
        "| Cancel | A patient can cancel a booking up to two hours before the visit. |",
        "| Remind by SMS | The portal sends a reminder one day before the visit. |",
    ]


def test_table_across_pages_with_repeated_header(tmp_path):
    # Одна таблица, шапка один раз, строк столько же, сколько в исходных данных.
    # Короткие ячейки со строчной буквы («daily») не считаются продолжением строки.
    path = tmp_path / "two_pages.pdf"
    first = [HEADER] + [[[f"R{i}"], ["daily"]] for i in range(1, 6)]
    second = [HEADER] + [[[f"R{i}"], ["weekly"]] for i in range(6, 9)]
    split_pdf(path, first, second, word_style=True)

    pdf = read_pdf(path)
    rows = [line for line in pdf.lines if line.kind == "table"]
    assert [r.text for r in rows] == (
        ["| Rule | Description |", "| --- | --- |"]
        + [f"| R{i} | daily |" for i in range(1, 6)]
        + [f"| R{i} | weekly |" for i in range(6, 9)]
    )
    assert pdf.joined_tables == 1
    assert [r.page for r in rows] == [1] * 7 + [2] * 3
    # Колонтитулы между частями сняты, текст после таблицы на месте, пустых страниц нет.
    assert pdf.removed_headers == 6 and pdf.empty_pages == [] and pdf.fallback_pages == []
    texts = [line.text for line in pdf.lines]
    assert "Bookings are stored for one year." in texts
    assert not any("Clinic portal spec" in t for t in texts)


def test_row_split_by_page_break_is_rejoined(tmp_path):
    # Последняя строка первой страницы дописана в начале второй: одна строка с полным текстом,
    # страница у неё первая. Шапка в продолжении не повторена.
    path = tmp_path / "split_row.pdf"
    first = [HEADER, [["Cancel"], ["A patient can cancel a booking"]],
             [["Lock"], ["The portal locks the account after"]]]
    second = [[[""], ["five failed sign-in attempts."]], [["Unlock"], ["An operator unlocks the account."]]]
    split_pdf(path, first, second)

    pdf = read_pdf(path)
    rows = [line for line in pdf.lines if line.kind == "table"]
    assert [r.text for r in rows] == [
        "| Rule | Description |",
        "| --- | --- |",
        "| Cancel | A patient can cancel a booking |",
        "| Lock | The portal locks the account after five failed sign-in attempts. |",
        "| Unlock | An operator unlocks the account. |",
    ]
    assert [r.page for r in rows] == [1, 1, 1, 1, 2]
    assert pdf.joined_tables == 1


def test_row_split_with_lowercase_phrase_in_every_cell(tmp_path):
    # Разрыв посреди фразы в нескольких ячейках, первая ячейка продолжения не пуста.
    path = tmp_path / "split_cells.pdf"
    first = [HEADER, [["Client"], ["Cancel by phone"]], [["Client", "software"], ["Browsers Firefox, Chrome or"]]]
    second = [HEADER, [["for the desk staff"], ["Safari not older than one year"]]]
    split_pdf(path, first, second, word_style=True)

    rows = [line.text for line in read_pdf(path).lines if line.kind == "table"]
    assert rows[-1] == "| Client software for the desk staff | Browsers Firefox, Chrome or Safari not older than one year |"
    assert len(rows) == 4


def test_different_tables_are_not_joined(tmp_path):
    # Разное число столбцов на соседних страницах: две таблицы.
    path = tmp_path / "widths.pdf"
    first = [HEADER] + [[[f"R{i}"], ["daily"]] for i in range(1, 6)]
    second = [[["Code"], ["Meaning"], ["Owner"]], [["E1"], ["no free slot"], ["desk"]]]
    split_pdf(path, first, second, widths_second=[100, 200, 130])
    pdf = read_pdf(path)
    assert pdf.joined_tables == 0
    assert sum(line.text.startswith("| ---") for line in pdf.lines) == 2

    # Абзац текста между таблицами: тоже две таблицы, даже при той же шапке.
    path = tmp_path / "paragraph.pdf"
    second = [HEADER, [["R9"], ["monthly"]]]
    split_pdf(path, first, second, between=["Table 2 Doctor rules"])
    pdf = read_pdf(path)
    assert pdf.joined_tables == 0
    assert sum(line.text == "| Rule | Description |" for line in pdf.lines) == 2
    texts = [line.text for line in pdf.lines]
    assert texts.index("Table 2 Doctor rules") < texts.index("| R9 | monthly |")


def test_table_in_middle_of_page_is_not_joined(tmp_path):
    # Первая таблица кончается в середине страницы (дальше страница пуста): это не разрыв таблицы.
    path = tmp_path / "middle.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    for page in (1, 2, 3):
        header_footer(c, page, 3)
        if page < 3:
            draw_table(c, H - 100, [130, 300], [HEADER, [[f"R{page}"], ["daily"]]])
        else:
            body(c, H - 100, ["End of rules."])
        c.showPage()
    c.save()
    pdf = read_pdf(path)
    assert pdf.joined_tables == 0


def test_single_column_frames_are_not_joined(tmp_path):
    # Слайды: каждая страница обведена рамкой-таблицей в один столбец от верха до низа.
    path = tmp_path / "slides.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    # Текст разный (не только цифры), иначе одинаковая рамка снимается как колонтитул.
    for title in ("Goals", "Schedule", "Contacts"):
        draw_table(c, H - 60, [470], [[[title]], [[f"About {title.lower()}"] + [""] * 40]])
        c.showPage()
    c.save()
    pdf = read_pdf(path)
    assert pdf.joined_tables == 0
    assert sum(line.text.startswith("| ---") for line in pdf.lines) == 3


def _rows_after_split(tmp_path, name, first, second, **kw):
    path = tmp_path / name
    split_pdf(path, first, second, **kw)
    pdf = read_pdf(path)
    return pdf, [line.text for line in pdf.lines if line.kind == "table"]


VALUES = [["Req"], ["Default value"]]


def test_finished_rows_are_not_glued(tmp_path):
    # Прочерк, одна буква, короткое значение ничего не обрывают: R6 остаётся отдельной строкой.
    for last in ("-", "Group A", "Mode on", "Zone (", "Cash,"):
        first = [VALUES] + [[[f"R{i}"], ["daily"]] for i in range(1, 5)] + [[["R5"], [last]]]
        second = [VALUES, [["R6"], ["weekly"]], [["R7"], ["monthly"]]]
        pdf, rows = _rows_after_split(tmp_path, "values.pdf", first, second)
        assert pdf.joined_tables == 1, last
        assert f"| R5 | {last} |" in rows and "| R6 | weekly |" in rows, last
        assert len(rows) == 2 + 7, last


def test_new_key_in_first_column_is_a_new_row(tmp_path):
    # Длинная ячейка оборвана запятой, но в первой колонке продолжения новый идентификатор: новая строка.
    first = [VALUES, [["R1"], ["daily"]], [["R2"], ["Reminders go by SMS, e-mail,"]]]
    second = [VALUES, [["R3"], ["push messages are not used"]]]
    _, rows = _rows_after_split(tmp_path, "keys.pdf", first, second)
    assert rows[-2:] == ["| R2 | Reminders go by SMS, e-mail, |", "| R3 | push messages are not used |"]


def test_broken_sentence_in_long_cell_is_glued(tmp_path):
    # Первая колонка продолжения пуста, а в таблице она есть у одной строки из двух: склеивает
    # только оборванная фраза в длинной ячейке.
    first = [VALUES, [["R1"], ["daily"]], [[""], ["note"]], [["R2"], ["Reminders go by SMS or"]]]
    second = [[[""], ["by a call from the desk"]], [["R3"], ["weekly"]]]
    _, rows = _rows_after_split(tmp_path, "broken.pdf", first, second)
    assert "| R2 | Reminders go by SMS or by a call from the desk |" in rows
    assert rows[-1] == "| R3 | weekly |"


def test_other_table_with_own_header_is_not_joined(tmp_path):
    # Вторая таблица со своей шапкой наверху следующей страницы, без подписи: две таблицы.
    first = [VALUES] + [[[f"R{i}"], ["daily"]] for i in range(1, 6)]
    second = [[["Code"], ["Meaning"]], [["E1"], ["no free slot"]], [["E2"], ["doctor is away"]]]
    pdf, rows = _rows_after_split(tmp_path, "two_tables.pdf", first, second)
    assert pdf.joined_tables == 0
    assert "| Code | Meaning |" in rows and rows.count("| --- | --- |") == 2

    # Та же шапка, но столбцы другой ширины: тоже другая таблица.
    second = [VALUES, [["R6"], ["weekly"]]]
    pdf, _ = _rows_after_split(tmp_path, "widths2.pdf", first, second, widths_second=[200, 230])
    assert pdf.joined_tables == 0


def test_table_over_three_pages(tmp_path):
    # Таблица на три страницы: средняя часть занимает страницу целиком, последняя строка
    # второй страницы разорвана и дописана на третьей.
    path = tmp_path / "three.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    rows1 = [HEADER] + [[[f"R{i}"], ["daily"]] for i in range(1, 6)]
    rows2 = [HEADER] + [[[f"R{i}"], ["weekly"]] for i in range(6, 30)] + [[["R30"], ["The portal sends the report to"]]]
    rows3 = [HEADER, [[""], ["the head doctor every Monday."]], [["R31"], ["monthly"]]]
    header_footer(c, 1, 4)
    body(c, H - 100, ["1 Appointments"])
    h1 = sum(LINE * max(len(cell) for cell in row) + 8 for row in rows1)
    draw_table(c, 130 + h1, [130, 300], rows1)
    c.showPage()
    header_footer(c, 2, 4)
    draw_table(c, H - 70, [130, 300], rows2)
    c.showPage()
    header_footer(c, 3, 4)
    bottom = draw_table(c, H - 70, [130, 300], rows3)
    body(c, bottom - 30, ["End of table."])
    c.showPage()
    header_footer(c, 4, 4)
    body(c, H - 100, ["2 Limits"])
    c.showPage()
    c.save()

    pdf = read_pdf(path)
    rows = [line for line in pdf.lines if line.kind == "table"]
    texts = [r.text for r in rows]
    assert pdf.joined_tables == 2
    assert texts.count("| Rule | Description |") == 1 and len(texts) == 2 + 31
    assert "| R30 | The portal sends the report to the head doctor every Monday. |" in texts
    assert {r.page for r in rows if r.text.startswith("| R30 ")} == {2}
