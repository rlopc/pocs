"""Document model shared by the HTML and the expected-Markdown renderers.

Each synthetic document is a list of blocks. The same blocks produce the HTML
(-> PDF) and the expected Markdown, so the expected output is exact by
construction. The Markdown follows the output convention of the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Literal

Style = Literal["", "b", "i", "bi", "u"]


@dataclass(frozen=True)
class Run:
    """A piece of text with one style. ``gap`` marks an exercise blank."""

    text: str
    style: Style = ""
    gap: int = 0  # length of the printed blank; 0 = not a gap
    gap_char: str = "_"  # "_" or "." (both are blanks in the convention)


def gap(length: int, char: str = "_") -> Run:
    return Run("", gap=length, gap_char=char)


def plain(text: str) -> list[Run]:
    return [Run(text)]


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Paragraph:
    runs: list[Run]


@dataclass(frozen=True)
class Bullets:
    items: list[list[Run]]


@dataclass(frozen=True)
class Box:
    """Highlighted box; Markdown renders it as a blockquote."""

    runs: list[Run]


@dataclass(frozen=True)
class Exercise:
    number: int
    prompt: list[Run]
    keyword: str
    keyword_bold: bool
    answer: list[Run]


@dataclass(frozen=True)
class Exercises:
    items: list[Exercise]


@dataclass(frozen=True)
class Numbered:
    items: list[list[Run]]
    start: int = 1


@dataclass(frozen=True)
class Column:
    title: str
    blocks: list[Block]


@dataclass(frozen=True)
class Columns:
    """Side-by-side columns; read left to right."""

    columns: list[Column]


@dataclass(frozen=True)
class Cell:
    runs: list[Run]
    image: str | None = None  # file name of an illustration (first column)
    number: int | None = None


@dataclass(frozen=True)
class Table:
    header: list[str]
    rows: list[list[Cell]]


@dataclass(frozen=True)
class PageBreak:
    pass


Block = Heading | Paragraph | Bullets | Box | Exercises | Numbered | Columns | Table | PageBreak


@dataclass
class Document:
    name: str  # template id: exercises, reading, styles, summary, table
    blocks: list[Block]
    running_header: str | None = None  # repeated on every page; not in the Markdown
    page_numbers: bool = False
    layout: str = "default"  # CSS layout key
    images: dict[str, int] = field(default_factory=dict)  # image file -> illustration number


# --- Markdown -----------------------------------------------------------------

MD_GAP = "_____"
_MARK = {"": "", "b": "**", "i": "*", "bi": "***"}


def runs_md(runs: list[Run]) -> str:
    out = []
    for r in runs:
        if r.gap:
            out.append(MD_GAP)
        elif r.style == "u":
            out.append(f"<u>{r.text}</u>")
        else:
            out.append(f"{_MARK[r.style]}{r.text}{_MARK[r.style]}")
    text = "".join(out)
    # A blank alone on its line would be a thematic break in CommonMark.
    return r"\_\_\_\_\_" if text == MD_GAP else text


def _blocks_md(blocks: list[Block], doc: Document) -> list[str]:
    parts: list[str] = []
    for block in blocks:
        match block:
            case Heading(level, text):
                parts.append(f"{'#' * level} {text}")
            case Paragraph(runs):
                parts.append(runs_md(runs))
            case Box(runs):
                parts.append(f"> {runs_md(runs)}")
            case Bullets(items):
                parts.append("\n".join(f"- {runs_md(i)}" for i in items))
            case Numbered(items, start):
                parts.append("\n".join(f"{start + n}. {runs_md(i)}" for n, i in enumerate(items)))
            case Exercises(items):
                rendered = []
                for ex in items:
                    marker = f"{ex.number}. "
                    pad = " " * len(marker)
                    kw = f"**{ex.keyword}**" if ex.keyword_bold else ex.keyword
                    rendered.append(
                        f"{marker}{runs_md(ex.prompt)}\n\n{pad}{kw}\n\n{pad}{runs_md(ex.answer)}"
                    )
                parts.append("\n\n".join(rendered))
            case Columns(columns):
                for col in columns:
                    parts.append(f"### {col.title}")
                    parts.extend(_blocks_md(col.blocks, doc))
            case Table(header, rows):
                lines = [
                    "| " + " | ".join(header) + " |",
                    "| " + " | ".join("---" for _ in header) + " |",
                ]
                for row in rows:
                    cells = []
                    for cell in row:
                        if cell.image is not None:
                            n = doc.images[cell.image]
                            link = f"![Illustration {n}](syn-{doc.name}.assets/image-{n:03d}.png)"
                            cells.append(f"{cell.number} {link}")
                        else:
                            cells.append(runs_md(cell.runs))
                    lines.append("| " + " | ".join(cells) + " |")
                parts.append("\n".join(lines))
            case PageBreak():
                pass
    return parts


def to_markdown(doc: Document) -> str:
    return "\n\n".join(_blocks_md(doc.blocks, doc)) + "\n"


# --- HTML fragments (the page skeleton and CSS live in the Jinja2 template) ----

_TAG = {"b": ("<strong>", "</strong>"), "i": ("<em>", "</em>"), "u": ("<u>", "</u>")}


def runs_html(runs: list[Run]) -> str:
    out = []
    for r in runs:
        if r.gap:
            out.append(r.gap_char * r.gap)
        elif r.style == "bi":
            out.append(f"<strong><em>{escape(r.text)}</em></strong>")
        elif r.style:
            opening, closing = _TAG[r.style]
            out.append(f"{opening}{escape(r.text)}{closing}")
        else:
            out.append(escape(r.text))
    return "".join(out)
