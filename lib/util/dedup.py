"""Two dedup helpers — pick by intent, NOT interchangeable.

* :func:`dedupe_lines`         O(n)  exact case-folded set membership.
                                     Use when callers will only repeat
                                     the same text verbatim (or with
                                     trivial whitespace / case
                                     differences).

* :func:`fuzzy_dedupe_lines`   O(n²) adds a substring-collision check
                                     on top of the exact match; kills
                                     ``"X"`` / ``"X."`` style near-
                                     duplicates the supervisor LLM
                                     produces when it re-states a
                                     point with extra punctuation or a
                                     trailing clarifier.  More
                                     aggressive — will sometimes
                                     collapse two genuinely distinct
                                     bullets if one is a prefix of the
                                     other; only use where false
                                     positives are cheaper than ship-
                                     ping duplicates.

History: ``feedback_rewriter`` previously had a function named
``dedupe_lines`` with the fuzzy semantics; the misleading name caused
the supervision orchestrator to write its own exact-match helper
(``_dedupe_text_items``) rather than reuse the public one.  Splitting
the two semantics into clearly named helpers prevents that confusion.
"""
from __future__ import annotations

import re
from collections.abc import Iterable


def dedupe_lines(lines: Iterable[str]) -> list[str]:
    """Keep the first occurrence of each whitespace-normalised line.

    ``"foo"``, ``"  foo"``, and ``"Foo"`` all collapse to a single
    entry.  Order is preserved.  Empty / whitespace-only lines are
    dropped.
    """
    kept: list[str] = []
    seen: set[str] = set()
    for item in lines:
        value = " ".join(str(item or "").strip().split())
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        kept.append(value)
        seen.add(key)
    return kept


def fuzzy_dedupe_lines(lines: Iterable[str]) -> list[str]:
    """Like :func:`dedupe_lines` plus a substring-collision check.

    A new line is dropped when any previously-kept line is a substring
    of it OR it is a substring of any previously-kept line.  This kills
    near-duplicates such as ``"Add a unit test."`` vs ``"Add a unit
    test"`` that the supervisor LLM emits across cycles, at the cost
    of occasionally collapsing two genuinely distinct bullets when one
    is a prefix of the other.
    """
    kept: list[str] = []
    lowered: list[str] = []
    for line in lines:
        value = str(line or "").strip()
        if not value:
            continue
        key = re.sub(r"\s+", " ", value).strip().lower()
        if any(key == seen or key in seen or seen in key for seen in lowered):
            continue
        kept.append(value)
        lowered.append(key)
    return kept
