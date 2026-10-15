"""Split a SQL file into named blocks marked `-- @<kind> <name>`."""

from __future__ import annotations

import re
from collections.abc import Iterator

_MARK = re.compile(r"^-- @(\w+) (\w+)\s*$", re.MULTILINE)


def split_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    marks = list(_MARK.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        yield m.group(1), m.group(2), text[m.end() : end].strip()
