from __future__ import annotations

import pytest

from benchmark.metrics import compare, normalise, parse, strict

DOC = """# Title

Intro with **bold words** and <u>underlined</u> text.

## Section

1. First item.

   **ORDER**

   I went _____ the city.

2. Second item.

| | A | B |
| --- | --- | --- |
| 1 ![Illustration 1](x.assets/image-001.png) | cell **one** | cell two |
"""


def test_identical_documents_are_perfect() -> None:
    m = compare(DOC, DOC)
    assert m["wer_norm"] == m["wer_strict"] == m["cer"] == 0
    assert m["invented"] == m["omitted"] == 0
    assert m["heading_f1"] == m["heading_level_ok"] == 1
    assert m["lists_ok"] == 1
    assert m["table_shape_ok"] == m["table_cells_ok"] == 1
    assert m["bold_f1"] == m["underline_f1"] == 1
    assert m["images_expected"] == m["images_output"] == 1


def test_normalisation_and_gaps() -> None:
    assert normalise("“Hello,” World’s—end") == "hello world s end"
    variants = [
        "I went _____ the city.",
        r"I went \_\_\_\_\_\_\_\_ the city.",
        "I went .... the city.",
    ]
    texts = [" ".join(parse(v).text) for v in variants]
    assert {normalise(t) for t in texts} == {"i went the city"}
    assert {strict(t) for t in texts} == {"I went _____ the city."}
    assert strict("Wait...") == "Wait..."  # an ellipsis is not a blank


def test_word_errors_ignore_order_and_punctuation() -> None:
    m = compare("Alpha beta gamma.", "gamma, beta alpha delta")
    assert m["invented"] == 1 and m["omitted"] == 0
    assert m["wer_norm"] > 0


def test_headings_fuzzy_match_and_level() -> None:
    m = compare("# A long heading text\n\n## Other\n", "## A long heading texts\n\nOther\n")
    assert m["heading_f1"] == pytest.approx(2 * (1 / 1) * (1 / 2) / (1 + 1 / 2))
    assert m["heading_level_ok"] == 0


def test_lists_tables_and_na() -> None:
    m = compare("- a\n- b\n", "1. a\n2. b\n")
    assert m["lists_ok"] == 0
    assert m["table_shape_ok"] is None and m["heading_f1"] is None and m["bold_f1"] is None
    m = compare("Plain text.\n", "# Heading\n\n**bold**\n")
    assert m["heading_fp"] == 1 and m["bold_fp"] == 1


def test_table_shape_and_cells() -> None:
    exp = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    out = "| a | b |\n| --- | --- |\n| 1 | 3 |\n"
    m = compare(exp, out)
    assert m["table_shape_ok"] == 1
    assert m["table_cells_ok"] == pytest.approx(3 / 4)
    assert compare(exp, "| a |\n| --- |\n")["table_shape_ok"] == 0


def test_empty_output() -> None:
    m = compare(DOC, "")
    assert m["wer_norm"] == 1 and m["heading_f1"] == 0 and m["table_shape_ok"] == 0


def test_list_numbers_are_text() -> None:
    m = compare("1. Foo.\n2. Bar.\n", "1\\. Foo.\n\n2\\. Bar.\n")
    assert m["invented"] == m["omitted"] == 0
    assert m["lists_ok"] == 0  # same words, but no list in the output
