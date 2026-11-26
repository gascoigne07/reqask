"""Правила промптов второй волны: нарезка размытых требований, общие фразы вместо случаев
одного документа, сверка пересказа строк, классы граничных случаев в полноте."""

from reqask import prompts


def _final() -> str:
    return prompts.final_prompt("spec.md", 3, [], "решение", 5, "L0001 текст")


def test_segmentation_keeps_vague_requirements():
    text = prompts.segmentation_prompt("L0001 текст", "", None)
    assert "нельзя написать тест" not in text
    assert "даже если оно размытое или его нельзя проверить" in text
    for word in ("should", "may", "желательно", "рекомендуется"):
        assert word in text
    # правило про констатацию отсутствия осталось
    assert "констатация, которая ничего не требует" in text


def test_no_case_list_of_given_document_in_final_prompt():
    text = _final()
    assert "хранение и показ" not in text
    assert "краткая схема и подробное правило" not in text
    assert "обзор и деталь, внутреннее и внешнее представление" in text
    assert "в каталоге полное название книги" in text


def test_identifier_example_and_numbers_rule():
    seg = prompts.segmentation_prompt("L0001 текст", "", None)
    assert "ФТ-3" not in seg and "«ТР-7»" in seg
    assert "сроков, лимитов, объёмов, процентов и количеств" in prompts.NUMBERS_RULE
    assert "порогов" not in prompts.NUMBERS_RULE


def test_final_prompt_checks_line_paraphrase():
    assert "Не приписывай строке документа того, чего в ней нет" in _final()


def test_completeness_prompt_has_edge_case_classes():
    text = prompts.completeness_prompt([], "L0001 текст")
    block = text[text.index("Граничные случаи."):]
    for cls in ("величины:", "границы диапазонов:", "время:", "состояние:", "операции:", "классификация:",
                "смежные системы:", "одновременность:", "количество:", "права:"):
        assert f"- {cls}" in block
    assert "пропусти молча" in block
    assert "kind gap" in block
    # негативные сценарии и ошибки остались в основном списке
    assert "негативные сценарии и обработка ошибок" in text
    assert "3. граничные значения" not in text
