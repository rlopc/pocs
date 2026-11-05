"""Content of the synthetic documents (invented B2-level English; no third-party text)."""

from __future__ import annotations

from model import (
    Block,
    Box,
    Bullets,
    Cell,
    Column,
    Columns,
    Document,
    Exercise,
    Exercises,
    Heading,
    Numbered,
    PageBreak,
    Paragraph,
    Run,
    Table,
    gap,
    plain,
)


def B(text: str) -> Run:
    return Run(text, "b")


def It(text: str) -> Run:
    return Run(text, "i")


def BI(text: str) -> Run:
    return Run(text, "bi")


def U(text: str) -> Run:
    return Run(text, "u")


def T(text: str) -> Run:
    return Run(text)


# --- 1. exercises ---------------------------------------------------------------


def _ex(n: int, prompt: str, keyword: str, before: str, length: int, after: str) -> Exercise:
    """Exercise whose answer line is ``before`` + blank + ``after``."""
    answer = [T(before), gap(length), T(after)]
    return Exercise(n, plain(prompt), keyword, True, [r for r in answer if r.text or r.gap])


def exercises() -> Document:
    items = [
        _ex(
            1,
            "We decided to leave early because of the traffic.",
            "AVOID",
            "We left early ",
            24,
            " the traffic.",
        ),
        _ex(
            2,
            "I have never seen such a beautiful beach.",
            "MOST",
            "It is ",
            12,
            " beach I have ever seen.",
        ),
        _ex(
            3,
            "Swimming in the sea is something she really enjoys.",
            "FOND",
            "She is ",
            30,
            " in the sea.",
        ),
        _ex(
            4,
            "They arrived at the hotel after the reception had closed.",
            "TIME",
            "By the ",
            18,
            " at the hotel, the reception had closed.",
        ),
        _ex(5, "It was a mistake to forget the sun cream.", "SHOULD", "We ", 26, " the sun cream."),
        _ex(
            6,
            "The waiter suggested that we try the fish.",
            "RECOMMENDED",
            "The waiter ",
            9,
            " the fish.",
        ),
        _ex(
            7,
            "Nobody told us the beach would be so crowded.",
            "EXPECT",
            "We did not ",
            22,
            " so crowded.",
        ),
        _ex(
            8,
            "Getting up at six on a Saturday was difficult for me.",
            "USED",
            "",
            20,
            " getting up at six on a Saturday.",
        ),
        _ex(
            9, "Perhaps the ferry will be late because of the wind.", "MIGHT", "The ferry ", 16, ""
        ),
        _ex(
            10, "Write the second sentence of exercise 9 again, from memory.", "MEMORY", "", 28, ""
        ),
        _ex(11, "We regret booking such a small room.", "WISH", "We ", 26, " such a small room..."),
        _ex(
            12,
            "The trip was so good that we will repeat it next year.",
            "SUCH",
            "It was ",
            14,
            " that we will repeat it next year.",
        ),
    ]
    # Exercise 12 uses a dotted blank: also a blank in the convention.
    last = items[-1]
    items[-1] = Exercise(
        last.number,
        last.prompt,
        last.keyword,
        last.keyword_bold,
        [T("It was "), gap(14, "."), T(" that we will repeat it next year.")],
    )
    answers = [
        "in order to avoid",
        "the most beautiful",
        "fond of swimming",
        "time we arrived",
        "should not have forgotten",
        "recommended",
        "expect the beach to be",
        "I was not used to",
        "might be late",
        "The ferry might be late",
        "wish we had not booked",
        "such a good trip",
    ]
    return Document(
        name="exercises",
        blocks=[
            Heading(1, "Sentence Transformation – A Weekend by the Sea"),
            Paragraph(
                [
                    T("Complete the second sentence so that it means the same as the first. "),
                    B("Do not change the word given."),
                    T(" Use between "),
                    B("two and five words"),
                    T(", including the word given."),
                ]
            ),
            Exercises(items),
            PageBreak(),
            Heading(2, "Answer Key"),
            Numbered([[B(a)] for a in answers]),
        ],
    )


# --- 2. reading -------------------------------------------------------------------

_READING: list[Block] = [
    Heading(1, "The Lighthouse Keeper’s Notebook"),
    Paragraph([B("A short story for upper-intermediate readers")]),
    Heading(2, "An unexpected inheritance"),
    Paragraph(
        plain(
            "When my great-aunt Florence died, she left me something nobody in the family"
            " had expected: a small, white lighthouse on a rocky island off the west "
            "coast. I had visited her there only once, as a child, and I remembered three"
            " things about the place. The wind never stopped, the stairs were impossibly "
            "steep, and the kitchen always smelt of fresh bread and paraffin."
        )
    ),
    Paragraph(
        plain(
            "The solicitor’s office was on the first floor of an old building near the "
            "harbour. Mr Fielding, a thin man with enormous eyebrows, read the will aloud"
            " and then pushed a brown envelope across the desk. “Your aunt was very "
            "specific,” he said. “The lighthouse is yours, but only if you spend fifty "
            "nights there before the end of the year.”"
        )
    ),
    Paragraph(
        plain(
            "“Fifty nights?” I repeated. “Alone?” He nodded, as if this were a perfectly "
            "reasonable request, and added that the official paperwork would take several"
            " weeks. I signed everything, shook his hand and walked out into the rain, "
            "wondering whether I had just made the most adventurous decision of my life "
            "or the most irresponsible one."
        )
    ),
    Heading(2, "The first night"),
    Paragraph(
        plain(
            "The ferry left me on the island at four o’clock on a grey October afternoon."
            " The captain, a cheerful woman called Fiona, promised to come back every "
            "Friday with supplies. “If the weather is bad, I’ll be late,” she warned. “If"
            " it’s really bad, I won’t come at all.” Then she waved, turned the boat "
            "around and disappeared into the mist."
        )
    ),
    Paragraph(
        plain(
            "Inside, the lighthouse was colder than I had imagined. I lit the old stove, "
            "found a fluffy blanket in a cupboard and made myself a cup of tea. On the "
            "kitchen table there was a leather notebook with my name written on the cover"
            " in Florence’s careful, old-fashioned handwriting. The first page contained "
            "a single sentence: ‘Read one entry every evening, and not a page more.’"
        )
    ),
    Paragraph(
        plain(
            "Naturally, I wanted to read the whole thing immediately. Nevertheless, "
            "something about the instruction made me hesitate. My aunt had been a "
            "remarkably efficient woman who never did anything without a reason, so I "
            "closed the notebook, finished my tea and climbed the one hundred and twelve "
            "steps to the lamp room."
        )
    ),
    PageBreak(),
    Heading(2, "Florence’s entries"),
    Paragraph(
        plain(
            "The entries turned out to be a mixture of practical advice and strange, "
            "affectionate observations. One evening she explained how to fix the "
            "generator when the flame in the pilot light went out. Another evening she "
            "described a family of seals that, according to her, had been arguing about "
            "the same flat rock for twenty years."
        )
    ),
    Paragraph(
        plain(
            "Gradually, I began to understand the rhythm of the island. I learned to read"
            " the sky, to recognise the difference between a temporary shower and a "
            "serious storm, and to appreciate the extraordinary silence that followed the"
            " wind. I stopped checking my phone, which rarely had a signal anyway, and "
            "started writing my own reflections in the margins of Florence’s notebook."
        )
    ),
    Paragraph(
        plain(
            "On the thirty-first night, the entry was different. ‘By now,’ she had "
            "written, ‘you have probably noticed that the third step from the top is "
            "loose. Lift it carefully.’ I took a torch, climbed the stairs and, with "
            "considerable difficulty, lifted the step. Underneath there was a flat tin "
            "box containing a bundle of letters, a photograph of a young woman on a "
            "fishing boat and a key."
        )
    ),
    Heading(2, "What the key opened"),
    Paragraph(
        plain(
            "I won’t tell you everything I discovered during the remaining nineteen "
            "nights, because some of it belongs to Florence and some of it now belongs to"
            " me. I will only say that the key opened a drawer in the office of the "
            "harbour master, and that the letters told the story of a friendship which "
            "had lasted, in secret, for more than sixty years."
        )
    ),
    Paragraph(
        plain(
            "When Fiona collected me on the fiftieth morning, she looked at my face and "
            "laughed. “You’re not leaving, are you?” she asked. She was right. I went "
            "back to the mainland to sign the final documents, and two weeks later I "
            "returned to the island with a suitcase, a box of books and a new notebook of"
            " my own."
        )
    ),
]


def reading() -> Document:
    return Document(
        name="reading",
        blocks=_READING,
        running_header="Synthetic Reader | B2",
        page_numbers=True,
        layout="reading",
    )


# --- 3. styles ----------------------------------------------------------------------


def styles() -> Document:
    return Document(
        name="styles",
        blocks=[
            Heading(1, "Text Styles in Context"),
            Paragraph(
                [
                    T("Some words in this text are "),
                    B("bold"),
                    T(", some are "),
                    It("italic"),
                    T(", some are "),
                    BI("bold and italic"),
                    T(", and some are "),
                    U("underlined"),
                    T(". A careful reader should notice all of them."),
                ]
            ),
            Paragraph(
                [
                    T("When you learn a new phrasal verb, "),
                    U("write it down"),
                    T(" together with an example, such as “I need to "),
                    B("look up"),
                    T(" this word”. Then "),
                    It("say the sentence aloud"),
                    T(" twice."),
                ]
            ),
            Heading(2, "Common mistakes"),
            Bullets(
                [
                    [
                        T("Do not confuse "),
                        B("make"),
                        T(" and "),
                        B("do"),
                        T(": we "),
                        U("make a decision"),
                        T(" but we "),
                        U("do our homework"),
                        T("."),
                    ],
                    [It("Actually"), T(" means ‘in fact’, not ‘at the moment’.")],
                    [T("The past of "), BI("lie"), T(" (to rest) is "), BI("lay"), T(".")],
                    [T("We say "), U("interested in"), T(", never ‘interested on’.")],
                ]
            ),
            Heading(2, "Reading tip"),
            Paragraph(
                [
                    T("Underlined words are often "),
                    U("key vocabulary"),
                    T(", while "),
                    B("bold"),
                    T(" usually marks grammar. "),
                    It("Italics"),
                    T(" are for titles such as "),
                    It("The Lighthouse Keeper’s Notebook"),
                    T("."),
                ]
            ),
        ],
    )


# --- 4. summary ------------------------------------------------------------------------


def summary() -> Document:
    return Document(
        name="summary",
        blocks=[
            Heading(1, "Phrasal Verbs and Collocations"),
            Paragraph(plain("B2 Summary Sheet")),
            Heading(2, "1 PHRASAL VERBS"),
            Columns(
                [
                    Column(
                        "1. Travel",
                        [
                            Bullets(
                                [
                                    [T("We "), B("set off"), T(" at dawn.")],
                                    [T("The plane "), B("took off"), T(" late.")],
                                    [T("They "), B("checked in"), T(" online.")],
                                    [
                                        T("She "),
                                        B("saw"),
                                        T(" him "),
                                        B("off"),
                                        T(" at the station."),
                                    ],
                                ]
                            )
                        ],
                    ),
                    Column(
                        "2. Work",
                        [
                            Bullets(
                                [
                                    [T("He "), B("took on"), T(" a new project.")],
                                    [T("We "), B("ran out of"), T(" time.")],
                                    [T("Please "), B("fill in"), T(" this form.")],
                                    [T("They "), B("called off"), T(" the meeting.")],
                                ]
                            )
                        ],
                    ),
                    Column(
                        "3. Relationships",
                        [
                            Bullets(
                                [
                                    [T("I "), B("get on"), T(" well with my sister.")],
                                    [T("They "), B("fell out"), T(" last year.")],
                                    [T("She "), B("looks up to"), T(" her mother.")],
                                    [T("We "), B("made up"), T(" quickly.")],
                                ]
                            )
                        ],
                    ),
                ]
            ),
            Box([B("A phrasal verb can have more than one meaning: check the context first.")]),
            Heading(2, "2 COLLOCATIONS"),
            Columns(
                [
                    Column(
                        "1. With make",
                        [
                            Bullets(
                                [
                                    [B("make"), T(" a mistake")],
                                    [B("make"), T(" progress")],
                                    [B("make"), T(" an effort")],
                                ]
                            )
                        ],
                    ),
                    Column(
                        "2. With do",
                        [
                            Bullets(
                                [
                                    [B("do"), T(" a favour")],
                                    [B("do"), T(" research")],
                                    [B("do"), T(" your best")],
                                ]
                            )
                        ],
                    ),
                    Column(
                        "3. With take",
                        [
                            Bullets(
                                [
                                    [B("take"), T(" a break")],
                                    [B("take"), T(" part")],
                                    [B("take"), T(" advice")],
                                ]
                            )
                        ],
                    ),
                ]
            ),
        ],
    )


# --- 5. table ---------------------------------------------------------------------------

_TABLE_ROWS = [
    (
        "She **went** to Paris.",
        "She **was walking** home.",
        "She **has visited** Rome.",
        "She **will travel** soon.",
    ),
    (
        "He **cooked** dinner.",
        "He **was cooking** when I called.",
        "He **has made** soup.",
        "He **is going to bake** bread.",
    ),
    (
        "They **won** the match.",
        "They **were playing** well.",
        "They **have won** twice.",
        "They **will play** again.",
    ),
    (
        "I **read** the news.",
        "I **was reading** in bed.",
        "I **have read** three books.",
        "I **will read** it tonight.",
    ),
    (
        "We **built** a sandcastle.",
        "We **were swimming** all day.",
        "We **have been** here before.",
        "We **are meeting** at six.",
    ),
    (
        "You **found** your keys.",
        "You **were looking** everywhere.",
        "You **have lost** them again.",
        "You **will find** them.",
    ),
    (
        "It **rained** all night.",
        "It **was snowing** in the hills.",
        "It **has stopped** now.",
        "It **might rain** later.",
    ),
    (
        "She **wrote** a letter.",
        "She **was writing** an email.",
        "She **has written** a novel.",
        "She **is going to publish** it.",
    ),
]


def _cell(text: str) -> Cell:
    runs: list[Run] = []
    for n, piece in enumerate(text.split("**")):
        if piece:
            runs.append(Run(piece, "b" if n % 2 else ""))
    return Cell(runs)


def table() -> Document:
    images = {f"picture-{n}.png": n for n in range(1, 9)}
    rows = [
        [Cell([], image=f"picture-{n}.png", number=n)] + [_cell(t) for t in texts]
        for n, texts in enumerate(_TABLE_ROWS, 1)
    ]
    return Document(
        name="table",
        blocks=[
            Heading(1, "Everyday Stories in Four Tenses"),
            Paragraph([B("Read each row and notice how the verb form changes.")]),
            Table(["", "PAST SIMPLE", "PAST CONTINUOUS", "PRESENT PERFECT", "FUTURE"], rows),
        ],
        layout="table",
        images=images,
    )


ALL = [exercises, reading, styles, summary, table]
