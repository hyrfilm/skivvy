import difflib
import stat
import unicodedata
from typing import Iterable, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text


EXIT_CODE_SUCCESS = 0
EXIT_CODE_DIFF = 1
EXIT_CODE_ERROR = 2


class RichConsoleDiff:
    """Side-by-side diff using Rich for colors/layout.

    Keeps the spirit of ConsoleDiff (side-by-side, intraline highlights),
    but uses Rich Text + Table instead of manual ANSI sequences.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        tabsize: int = 8,
        line_numbers: bool = False,
        strip_trailing_cr: bool = False,
    ):
        self.console = console or Console()
        self._tabsize = tabsize
        self.line_numbers = line_numbers
        self.strip_trailing_cr = strip_trailing_cr

        # Map logical categories to Rich styles
        self.styles = {
            "add": "bold green",
            "subtract": "bold red",
            "change": "bold yellow",
            "separator": "blue",
            "description": "bold blue",
            "permissions": "yellow",
            "meta": "magenta",
            "line-numbers": "bold white",
        }

    # ---------- preprocessing helpers ----------

    def _tab_newline_replace(
        self, fromlines: Iterable[str], tolines: Iterable[str]
    ) -> Tuple[List[str], List[str]]:
        """Expand tabs and strip trailing newlines (like original)."""

        def expand_tabs(line: str) -> str:
            # keep spaces; just expand tabs
            return line.expandtabs(self._tabsize).rstrip("\n")

        return [expand_tabs(l) for l in fromlines], [
            expand_tabs(l) for l in tolines
        ]

    def _strip_trailing_cr(self, lines: List[str]) -> List[str]:
        return [line.rstrip("\r") for line in lines]

    def _all_cr_nl(self, lines: List[str]) -> bool:
        return all(line.endswith("\r") for line in lines)

    # ---------- core diff -> rows ----------

    def _format_line_text(self, linenum, text: str) -> Text:
        """
        Convert a difflib-marked line (with \0+, \0-, \0^, \1 markers)
        into a Rich Text object with appropriate styles.
        """

        # Build Text based on diff markers
        t = Text()
        current_style: Optional[str] = None
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\0":  # start of a marked region
                i += 1
                if i >= len(text):
                    break
                marker = text[i]
                if marker == "+":
                    current_style = self.styles["add"]
                elif marker == "-":
                    current_style = self.styles["subtract"]
                elif marker == "^":
                    current_style = self.styles["change"]
                i += 1
                continue
            elif ch == "\1":  # end of marked region
                current_style = None
                i += 1
                continue
            elif ch == "\t":
                t.append(" ", style=current_style)
                i += 1
                continue
            elif ch == "\r":
                t.append("\\r", style=current_style)
                i += 1
                continue
            else:
                t.append(ch, style=current_style)
                i += 1

        # Line numbers, if requested
        if self.line_numbers:
            try:
                lid = int(linenum)
                num_text = Text(f"{lid:>4} ", style=self.styles["line-numbers"])
                num_text.append_text(t)
                return num_text
            except (TypeError, ValueError):
                # linenum is '' or '>' for wrapped/continuation lines
                return t

        return t

    def _iter_diff_rows(
        self,
        fromlines: List[str],
        tolines: List[str],
        context: bool,
        numlines: int,
    ):
        """Yield (left_text, right_text) as Rich Text objects."""

        if context:
            context_lines = numlines
        else:
            context_lines = None

        diffs = difflib._mdiff(  # type: ignore[attr-defined]
            fromlines,
            tolines,
            context_lines,
            linejunk=None,
            charjunk=difflib.IS_CHARACTER_JUNK,
        )

        for i, (fromdata, todata, flag) in enumerate(diffs):
            if (fromdata, todata, flag) == (None, None, None):
                # separator between hunks
                if i > 0:
                    sep_style = self.styles["separator"]
                    yield Text("---", style=sep_style), Text(
                        "---", style=sep_style
                    )
                continue

            (fromline, fromtext), (toline, totext) = fromdata, todata

            left = self._format_line_text(fromline, fromtext.rstrip())
            right = self._format_line_text(toline, totext.rstrip())

            yield left, right

    # ---------- public API ----------

    def build_table(
        self,
        fromlines: Iterable[str],
        tolines: Iterable[str],
        fromdesc: str = "",
        todesc: str = "",
        fromperms: Optional[int] = None,
        toperms: Optional[int] = None,
        context: bool = False,
        numlines: int = 5,
        title: Optional[str] = None,
    ) -> Table:
        """Return a Rich Table representing the side-by-side diff."""

        fromlines = list(fromlines)
        tolines = list(tolines)

        fromlines, tolines = self._tab_newline_replace(fromlines, tolines)

        if self.strip_trailing_cr or (
            self._all_cr_nl(fromlines) and self._all_cr_nl(tolines)
        ):
            fromlines = self._strip_trailing_cr(fromlines)
            tolines = self._strip_trailing_cr(tolines)

        table = Table(
            title=title,
            show_header=True,
            header_style=self.styles["description"],
            show_lines=False,
        )

        left_header = fromdesc or "Left"
        right_header = todesc or "Right"
        table.add_column(left_header, overflow="fold", ratio=1)
        table.add_column(right_header, overflow="fold", ratio=1)

        # Optional permissions row
        if fromperms is not None and toperms is not None:
            if fromperms != toperms:
                left_perm = Text(
                    f"{stat.filemode(fromperms)} ({fromperms:o})",
                    style=self.styles["permissions"],
                )
                right_perm = Text(
                    f"{stat.filemode(toperms)} ({toperms:o})",
                    style=self.styles["permissions"],
                )
                table.add_row(left_perm, right_perm)

        # Body rows
        for left, right in self._iter_diff_rows(
            fromlines, tolines, context=context, numlines=numlines
        ):
            table.add_row(left, right)

        return table

    def print_table(
        self,
        fromlines: Iterable[str],
        tolines: Iterable[str],
        **kwargs,
    ):
        """Convenience: build and print table in one go."""
        table = self.build_table(fromlines, tolines, **kwargs)
        self.console.print(table)
