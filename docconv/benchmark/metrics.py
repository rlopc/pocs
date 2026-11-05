"""Quality metrics: a converted Markdown file against its expected Markdown.

Definitions (fixed before looking at any result):
- Text is extracted by walking the markdown-it-py token tree: tables row by row,
  left to right; image alt text is discarded. The number of an ordered-list item is
  part of the text (it is the original number, i.e. document content), so "1. Foo"
  as a list and "1. Foo" written as plain text give the same words.
- Blank: a run of 3+ underscores or 4+ dots. Excluded from the normalised text,
  kept as one token ("_____") in the strict text.
- Normalised: NFKC, lower case, every Unicode punctuation character (category P*)
  replaced by a space, whitespace collapsed. Strict: NFKC, whitespace collapsed.
- WER (normalised and strict) and CER (normalised) with jiwer. Invented / omitted
  words: multiset difference of the normalised words (order ignored).
- Headings: F1 matching each expected heading to at most one output heading with
  rapidfuzz.fuzz.ratio >= 90 on normalised text; plus % of matches at the right level.
- Lists: % of expected lists whose item count and type (ordered or not) equal those of
  the output list with the same position.
- Tables (matched by position): shape (rows x columns) exact; % of expected cells whose
  strict text equals the output cell at the same position.
- Emphasis: F1 over the multiset of normalised words inside bold spans; same for
  underline (<u>...</u>).
- Images: number of image references.
- A metric with nothing expected is None (N/A) for that document; output elements
  that appear anyway are counted as false positives.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import jiwer
from markdown_it import MarkdownIt
from rapidfuzz import fuzz

GAP = "\x00gap\x00"
STRICT_GAP = "_____"
_GAP_RE = re.compile(r"_{3,}|\.{4,}")
HEADING_MATCH = 90


@dataclass
class Parsed:
    """What the metrics need from one Markdown document."""

    text: list[str] = field(default_factory=list)  # text pieces in reading order
    headings: list[tuple[int, str]] = field(default_factory=list)
    lists: list[tuple[bool, int]] = field(default_factory=list)  # (ordered, items)
    tables: list[list[list[str]]] = field(default_factory=list)  # rows of cell texts
    bold: list[str] = field(default_factory=list)
    underline: list[str] = field(default_factory=list)
    images: int = 0


def _with_gaps(text: str) -> str:
    return _GAP_RE.sub(f" {GAP} ", text)


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text.replace(GAP, " ")).lower()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return " ".join(text.split())


def strict(text: str) -> str:
    text = unicodedata.normalize("NFKC", text.replace(GAP, f" {STRICT_GAP} "))
    return " ".join(text.split())


_MD = MarkdownIt("commonmark").enable("table")


def _inline(children: list[Any], parsed: Parsed) -> str:
    """Text of an inline token; records bold/underline spans and images."""
    out: list[str] = []
    bold = underline = 0
    for tok in children:
        piece = ""
        match tok.type:
            case "text" | "code_inline":
                piece = tok.content
            case "softbreak" | "hardbreak":
                piece = " "
            case "strong_open":
                bold += 1
            case "strong_close":
                bold -= 1
            case "image":
                parsed.images += 1
            case "html_inline":
                tag = tok.content.strip().lower()
                if tag == "<u>":
                    underline += 1
                elif tag == "</u>":
                    underline -= 1
        if piece:
            out.append(piece)
            if bold > 0:
                parsed.bold.append(piece)
            if underline > 0:
                parsed.underline.append(piece)
    return _with_gaps("".join(out))


def parse(markdown: str) -> Parsed:
    parsed = Parsed()
    open_lists: list[int] = []  # indexes into parsed.lists
    heading_level: int | None = None
    row: list[str] | None = None
    for tok in _MD.parse(markdown):
        match tok.type:
            case "heading_open":
                heading_level = int(tok.tag[1:])
            case "heading_close":
                heading_level = None
            case "bullet_list_open" | "ordered_list_open":
                parsed.lists.append((tok.type == "ordered_list_open", 0))
                open_lists.append(len(parsed.lists) - 1)
            case "bullet_list_close" | "ordered_list_close":
                open_lists.pop()
            case "list_item_open":
                ordered, items = parsed.lists[open_lists[-1]]
                parsed.lists[open_lists[-1]] = (ordered, items + 1)
                if tok.info:  # ordered-list number
                    parsed.text.append(tok.info)
            case "table_open":
                parsed.tables.append([])
            case "tr_open":
                row = []
            case "tr_close":
                assert row is not None
                parsed.tables[-1].append(row)
                row = None
            case "inline":
                text = _inline(tok.children or [], parsed)
                parsed.text.append(text)
                if heading_level is not None:
                    parsed.headings.append((heading_level, text))
                if row is not None:
                    row.append(text)
    return parsed


def _f1(expected: Counter[str], output: Counter[str]) -> float | None:
    if not expected:
        return None
    hits = sum((expected & output).values())
    if hits == 0:
        return 0.0
    precision, recall = hits / sum(output.values()), hits / sum(expected.values())
    return 2 * precision * recall / (precision + recall)


def _words(pieces: list[str]) -> Counter[str]:
    return Counter(normalise(" ".join(pieces)).split())


def _wer(reference: str, hypothesis: str, *, cer: bool = False) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    if not hypothesis:
        return 1.0
    return float(jiwer.cer(reference, hypothesis) if cer else jiwer.wer(reference, hypothesis))


def _headings(exp: list[tuple[int, str]], out: list[tuple[int, str]]) -> dict[str, Any]:
    if not exp:
        return {"heading_f1": None, "heading_level_ok": None, "heading_fp": len(out)}
    free = list(range(len(out)))
    matches: list[tuple[int, int]] = []
    for level, text in exp:
        target = normalise(text)
        best, best_score = None, -1.0
        for j in free:
            score = fuzz.ratio(target, normalise(out[j][1]))
            if score > best_score:
                best, best_score = j, score
        if best is not None and best_score >= HEADING_MATCH:
            free.remove(best)
            matches.append((level, out[best][0]))
    m = len(matches)
    f1 = 0.0 if m == 0 else 2 * (m / len(out)) * (m / len(exp)) / (m / len(out) + m / len(exp))
    level_ok = None if m == 0 else sum(a == b for a, b in matches) / m
    return {"heading_f1": f1, "heading_level_ok": level_ok, "heading_fp": 0}


def _tables(exp: list[list[list[str]]], out: list[list[list[str]]]) -> dict[str, Any]:
    if not exp:
        return {"table_shape_ok": None, "table_cells_ok": None, "table_fp": len(out)}
    shape_ok = cells = good = 0
    for i, table in enumerate(exp):
        other = out[i] if i < len(out) else []
        shape = (len(table), max((len(r) for r in table), default=0))
        other_shape = (len(other), max((len(r) for r in other), default=0))
        shape_ok += shape == other_shape
        for r, row in enumerate(table):
            for c, cell in enumerate(row):
                cells += 1
                if r < len(other) and c < len(other[r]):
                    good += strict(cell) == strict(other[r][c])
    return {
        "table_shape_ok": shape_ok / len(exp),
        "table_cells_ok": good / cells if cells else None,
        "table_fp": max(0, len(out) - len(exp)),
    }


def _lists(exp: list[tuple[bool, int]], out: list[tuple[bool, int]]) -> dict[str, Any]:
    if not exp:
        return {"lists_ok": None, "lists_fp": len(out)}
    ok = sum(1 for i, item in enumerate(exp) if i < len(out) and out[i] == item)
    return {"lists_ok": ok / len(exp), "lists_fp": max(0, len(out) - len(exp))}


def compare(expected_md: str, output_md: str) -> dict[str, Any]:
    """All metrics for one document. Rates are fractions (0.01 = 1 %)."""
    exp, out = parse(expected_md), parse(output_md)
    exp_text, out_text = " ".join(exp.text), " ".join(out.text)
    ref_n, hyp_n = normalise(exp_text), normalise(out_text)
    exp_words, out_words = Counter(ref_n.split()), Counter(hyp_n.split())
    result: dict[str, Any] = {
        "wer_norm": _wer(ref_n, hyp_n),
        "wer_strict": _wer(strict(exp_text), strict(out_text)),
        "cer": _wer(ref_n, hyp_n, cer=True),
        "invented": sum((out_words - exp_words).values()),
        "omitted": sum((exp_words - out_words).values()),
        "words_expected": sum(exp_words.values()),
        "bold_f1": _f1(_words(exp.bold), _words(out.bold)),
        "bold_fp": 0 if exp.bold else sum(_words(out.bold).values()),
        "underline_f1": _f1(_words(exp.underline), _words(out.underline)),
        "underline_fp": 0 if exp.underline else sum(_words(out.underline).values()),
        "images_expected": exp.images,
        "images_output": out.images,
    }
    result |= _headings(exp.headings, out.headings)
    result |= _lists(exp.lists, out.lists)
    result |= _tables(exp.tables, out.tables)
    return result
