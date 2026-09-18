"""Lexer for processing Ren'Py script lines, handling indentation, strings, and comments."""

from dataclasses import dataclass
from typing import Iterator, Optional, Sequence


@dataclass(frozen=True)
class LogicalLine:
    """A processed line of Ren'Py script with indentation and comment metadata."""

    file_path: str
    line_number: int  # 1-indexed
    indent: int  # Number of leading spaces
    raw_text: str
    stripped_code: str  # Code without comments or leading/trailing whitespace
    comment: Optional[str] = None  # Extracted comment text, if any
    is_multiline_string_continuation: bool = False

    @property
    def is_empty(self) -> bool:
        """True if the line contains no executable code (blank or comment only)."""
        return len(self.stripped_code) == 0

    @property
    def column(self) -> int:
        """1-indexed column where code begins."""
        return self.indent + 1


def strip_comment_and_track_strings(
    line: str,
    active_multiline_quote: Optional[str] = None,
) -> tuple[str, Optional[str], Optional[str]]:
    """Split line into code and comment while properly respecting quotes and escape characters.

    Args:
        line: The raw string of the line.
        active_multiline_quote: '\"\"\"' or '\'\'\'' if currently inside a multiline string.

    Returns:
        tuple of (code_part, comment_part, updated_multiline_quote)
    """
    i = 0
    n = len(line)
    quote_char: Optional[str] = None
    is_triple = False

    # If already inside a multiline string from a previous line
    if active_multiline_quote is not None:
        quote_char = active_multiline_quote
        is_triple = len(active_multiline_quote) >= 3

    while i < n:
        # If currently inside a multiline triple-quoted string
        if quote_char is not None and is_triple:
            if line[i] == "\\":
                i += 2
                continue
            if line[i : i + 3] == quote_char:
                # Closed multiline string
                i += 3
                quote_char = None
                is_triple = False
                continue
            i += 1
            continue

        # If currently inside a single or multiline standard string (" or ')
        if quote_char is not None and not is_triple:
            char = line[i]
            if char == "\\":
                # Escaped character, skip next character
                i += 2
                continue
            if char == quote_char:
                # Closed string
                quote_char = None
                i += 1
                continue
            i += 1
            continue

        # Not in any string: check for triple quotes start
        if line[i : i + 3] in ('"""', "'''"):
            quote_char = line[i : i + 3]
            is_triple = True
            i += 3
            continue

        # Check for single quotes start
        if line[i] in ('"', "'"):
            quote_char = line[i]
            is_triple = False
            i += 1
            continue

        # Check for comment character '#'
        if line[i] == "#":
            code_part = line[:i]
            comment_part = line[i + 1 :].strip()
            return code_part, comment_part, None

        i += 1

    # End of line reached
    code_part = line
    comment_part = None
    new_multiline = quote_char
    return code_part, comment_part, new_multiline


class ScriptLexer:
    """Tokenizes lines into LogicalLine objects with indentation and string tracking."""

    @classmethod
    def tokenize(
        cls,
        file_path: str,
        lines: Sequence[str],
    ) -> Iterator[LogicalLine]:
        """Convert raw script lines into a sequence of LogicalLine objects."""
        multiline_quote: Optional[str] = None

        for idx, raw_line in enumerate(lines, start=1):
            # Expand tabs to 4 spaces for consistent indentation measurement
            expanded = raw_line.expandtabs(4)
            unindented = expanded.lstrip()
            indent = len(expanded) - len(unindented)

            # Defensive safeguard: if a standard quote was left open, but we encounter a
            # top-level block declaration at indent 0, avoid swallowing subsequent declarations.
            if multiline_quote is not None and len(multiline_quote) == 1:
                if indent == 0 and unindented.startswith(
                    ("label ", "init ", "screen ", "define ", "default ")
                ):
                    multiline_quote = None

            # Track if this line started inside an active multiline string
            was_in_multiline = multiline_quote is not None

            code_part, comment, multiline_quote = strip_comment_and_track_strings(
                expanded, active_multiline_quote=multiline_quote
            )
            stripped_code = code_part.strip()

            yield LogicalLine(
                file_path=file_path,
                line_number=idx,
                indent=indent,
                raw_text=raw_line,
                stripped_code=stripped_code,
                comment=comment,
                is_multiline_string_continuation=was_in_multiline,
            )
