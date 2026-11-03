"""`table`: tabular data (a pandas or polars DataFrame, records, columns) as a grid.

Python only: rows of `view` and `text`, styled with theme tokens. It reads
the data once per render and draws every row it is given, so for big data
frames pass `max_rows` (there is no scrolling or virtualisation yet).

Future work: nsh-base has Rust `Table` parts (`table.rs`: semantic roles
for screen readers, no look) and `DataTable` (`data_table/`: virtual
scrolling both ways, sorting, selection, resizable and fixed columns). A
Python + Rust primitive wrapping `DataTable` is the way to show large data;
this component is the lightweight one for a few dozen rows.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Union

from nsh._element import Child, Element, StrProp, merge_class
from nsh.primitives import text, view

ROOT_CLASS = "flex-col rounded-md border border-border overflow-hidden"
"""The table's own classes; the caller's `class_` comes after and wins."""

HEADER_ROW_CLASS = "flex-row border-b border-border bg-muted"
ROW_CLASS = "flex-row"
STRIPE_CLASS = "bg-muted/50"
"""Added to every second body row when `striped`."""
SEPARATOR_CLASS = "border-t border-border"
"""Added to body rows after the first when not `striped`."""

CELL_CLASS = "px-3 py-2 text-sm text-foreground"
NUMBER_CLASS = "text-right"
"""Added to the cells (and header) of a column holding only numbers."""
INDEX_CLASS = "text-muted-foreground"
"""Added to the cells of the index columns."""
HEADER_CELL_CLASS = "px-3 py-2 text-sm font-medium text-muted-foreground"
FOOTER_CLASS = "px-3 py-2 text-sm text-muted-foreground border-t border-border"
EMPTY_CLASS = "px-3 py-2 text-sm text-muted-foreground"

DEFAULT_WIDTH = "flex-1"
"""A cell's width class unless `widths` names its column: equal shares."""
INDEX_WIDTH = "w-16"
"""The default width of an index column (row numbers are short)."""

NA_TEXT = "—"
"""Shown for a missing value: `None`, NaN, `pd.NA`, `pd.NaT`."""
EMPTY_TEXT = "No rows"

Format = Union[str, Callable[[Any], Any]]
"""A format string (`"{:,.0f}"`) or a function from a value to what shows."""

_MISSING_TYPES = {"NAType", "NaTType"}  # pandas' pd.NA and pd.NaT, without importing pandas


def table(
    data: Any,
    *,
    columns: Sequence[Any] | None = None,
    index: bool | None = None,
    header: bool = True,
    striped: bool = True,
    max_rows: int | None = None,
    format: Format | Mapping[Any, Format] | None = None,  # noqa: A002
    widths: Mapping[Any, str] | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A table of `data`: a header row, then one row per record.

    `data` can be:

    - a pandas or polars DataFrame (detected by its methods; neither is imported),
    - a list of dicts (records) or of namedtuples,
    - a dict of lists (one list per column),
    - a list of lists or tuples (a 2-D array works too): name the columns with `columns=`,
    - or a **callable returning any of these**, such as a signal: the table
      is made again when the signals it reads change, so
      `nsh.table(df)` with `df = nsh.signal(frame)` follows `df.set(new_frame)`.

    Arguments:

    - `columns`: which columns to show, in this order (default all). For a
      list of plain lists it names the columns instead.
    - `index`: show the index as leading columns. The default shows a
      pandas index only when it isn't a default `RangeIndex`. For other data,
      `index=True` shows row numbers from 0.
    - `header`: show the header row. `striped`: shade every second row.
    - `max_rows`: draw the first N rows, then a "… N more rows" footer.
      Use it for large data: every row shown is a handful of elements.
    - `format`: how cells print. A function from a value to a string, a
      format string (`"{:,.0f}"`), or a dict from column to either
      (`{"price": "${:,.2f}", "when": lambda d: d.strftime("%b %d")}`).
      Missing values (`None`, NaN, `pd.NA`) always show as "—" and aren't
      passed to it. The default prints ints as they are and floats with two
      decimals (`{:.2f}`, or three significant digits when closer to 0).
    - `widths`: a Tailwind width class per column (`{"name": "w-48"}`);
      the others share the remaining width equally (`flex-1`), except
      index columns, which are `w-16`.
    - `class_`: Tailwind classes added after the default look, so they win.
    - `test_id`: on the root; rows get `f"{test_id}-row-{i}"`, the header
      `f"{test_id}-header"` and the footer `f"{test_id}-more"`.

    Numbers are right-aligned (a column is numeric when all its values are).

        import pandas as pd

        df = pd.DataFrame({"city": ["Oslo", "Rome"], "temp": [4.5, 18.25]})
        nsh.table(df, format={"temp": "{:.1f}°"}, max_rows=100)
    """
    root_class = merge_class(ROOT_CLASS, class_)
    opts = _Options(columns, index, header, striped, max_rows, format, widths, test_id)

    if callable(data):
        # A region: made again when the signals `data()` reads change.
        return view(lambda: _parts(data(), opts), class_=root_class, test_id=test_id)
    return view(*_parts(data, opts), class_=root_class, test_id=test_id)


class _Options:
    """What `table` was called with, handed to the render function."""

    __slots__ = ("columns", "index", "header", "striped", "max_rows", "format", "widths", "test_id")

    def __init__(self, *values: Any) -> None:
        for name, value in zip(self.__slots__, values):
            setattr(self, name, value)

    def row_id(self, i: int) -> str | None:
        return None if self.test_id is None else f"{self.test_id}-row-{i}"

    def part_id(self, part: str) -> str | None:
        return None if self.test_id is None else f"{self.test_id}-{part}"


def _parts(data: Any, o: _Options) -> list[Child]:
    """The root's children: header, body rows and a footer."""
    labels, rows, total, n_index = _read(data, o.columns, o.index, o.max_rows)
    names = [str(label) for label in labels]
    numeric = [_is_numeric_column(col) for col in zip(*rows)] if rows else [False] * len(labels)
    formats = [_formatter(o.format, label) for label in labels]
    given = o.widths or {}
    widths = [
        given.get(label, given.get(name, INDEX_WIDTH if c < n_index else DEFAULT_WIDTH))
        for c, (label, name) in enumerate(zip(labels, names))
    ]

    def cell_class(base: str, c: int, index_class: str = "") -> str:
        parts = [base, widths[c]]
        if c < n_index and index_class:
            parts.append(index_class)
        if numeric[c]:
            parts.append(NUMBER_CLASS)
        return " ".join(parts)

    out: list[Child] = []
    if o.header and labels:
        out.append(
            view(
                *(text(name, class_=cell_class(HEADER_CELL_CLASS, c)) for c, name in enumerate(names)),
                class_=HEADER_ROW_CLASS,
                test_id=o.part_id("header"),
            )
        )
    for i, row in enumerate(rows):
        row_class = ROW_CLASS
        if o.striped and i % 2 == 1:
            row_class += f" {STRIPE_CLASS}"
        elif not o.striped and i > 0:
            row_class += f" {SEPARATOR_CLASS}"
        out.append(
            view(
                *(
                    text(_cell_text(value, formats[c]), class_=cell_class(CELL_CLASS, c, INDEX_CLASS))
                    for c, value in enumerate(row)
                ),
                class_=row_class,
                test_id=o.row_id(i),
            )
        )
    if total == 0:
        out.append(text(EMPTY_TEXT, class_=EMPTY_CLASS))
    elif total > len(rows):
        more = total - len(rows)
        out.append(
            text(
                f"… {more:,} more {'row' if more == 1 else 'rows'}",
                class_=FOOTER_CLASS,
                test_id=o.part_id("more"),
            )
        )
    return out


# --- reading the data -------------------------------------------------------


def _read(
    data: Any,
    columns: Sequence[Any] | None,
    index: bool | None,
    max_rows: int | None,
) -> tuple[list[Any], list[list[Any]], int, int]:
    """`(column labels, the rows to draw, total row count, index column count)`.

    Each row has one value per label. The first `n_index` columns are the index.
    """
    if hasattr(data, "columns") and hasattr(data, "iter_rows"):  # polars
        total = len(data)
        shown = data.head(max_rows) if max_rows is not None and total > max_rows else data
        labels = list(shown.columns)
        rows = [list(r) for r in shown.iter_rows()]
        n_index = 0
    elif hasattr(data, "columns") and hasattr(data, "itertuples"):  # pandas
        total = len(data)
        shown = data.head(max_rows) if max_rows is not None and total > max_rows else data
        labels = list(shown.columns)
        rows = [list(r) for r in shown.itertuples(index=False, name=None)]
        n_index = 0
        if index is None:
            index = not _is_default_index(shown.index)
        if index:
            levels = shown.index.nlevels
            names = [("" if n is None else n) for n in shown.index.names]
            keys = [k if levels > 1 else (k,) for k in shown.index.tolist()]
            labels = names + labels
            rows = [list(k) + r for k, r in zip(keys, rows)]
            n_index = levels
    else:
        labels, rows, named = _read_python(data, columns)
        total = len(rows)
        rows = rows[:max_rows] if max_rows is not None else rows
        n_index = 0
        if index:
            labels = [""] + labels
            rows = [[i, *r] for i, r in enumerate(rows)]
            n_index = 1
        if not named:
            columns = None  # `columns` named the labels; nothing left to select
    if columns is not None:
        labels, rows = _select(labels, rows, columns, n_index)
    return labels, rows, total, n_index


def _read_python(data: Any, columns: Sequence[Any] | None) -> tuple[list[Any], list[list[Any]], bool]:
    """Labels and rows of plain Python data. The last item is False when
    `columns` was used to name plain-list columns (so not to select again)."""
    if isinstance(data, (str, bytes)):
        raise TypeError(f"nsh.table can't show a {type(data).__name__}; give it rows or a DataFrame")
    if isinstance(data, Mapping):  # a dict of lists
        try:
            cols = [list(v) for v in data.values()]
        except TypeError:
            raise TypeError("nsh.table: a dict must map each column name to a list of values") from None
        if len({len(c) for c in cols}) > 1:
            raise ValueError("nsh.table: the lists of a dict must have the same length")
        return list(data.keys()), [list(r) for r in zip(*cols)], True
    if not isinstance(data, Iterable):
        raise TypeError(f"nsh.table can't show a {type(data).__name__}")
    records = list(data)
    if not records:
        return list(columns or []), [], True
    first = records[0]
    if isinstance(first, Mapping):
        labels: list[Any] = []
        seen = set()
        for rec in records:  # the union of keys, in first-seen order
            for key in rec:
                if key not in seen:
                    seen.add(key)
                    labels.append(key)
        return labels, [[rec.get(k) for k in labels] for rec in records], True
    rows = [list(r) for r in records]
    width = max(len(r) for r in rows)
    rows = [r + [None] * (width - len(r)) for r in rows]
    fields = getattr(first, "_fields", None)  # namedtuples name their columns
    if fields is not None:
        return list(fields), rows, True
    if columns is not None:
        if len(columns) != width:
            raise ValueError(f"nsh.table: {len(columns)} column names for rows of {width} values")
        return list(columns), rows, False
    return list(range(width)), rows, True


def _select(labels: list[Any], rows: list[list[Any]], columns: Sequence[Any], n_index: int):
    """The columns named in `columns`, in that order (the index stays first)."""
    pos = {}
    for i, label in enumerate(labels):
        if i >= n_index:
            pos.setdefault(label, i)
    picked = []
    for c in columns:
        if c not in pos:
            raise ValueError(f"nsh.table: no column {c!r} (columns: {[l for l in labels[n_index:]]})")
        picked.append(pos[c])
    keep = list(range(n_index)) + picked
    return [labels[i] for i in keep], [[r[i] for i in keep] for r in rows]


def _is_default_index(idx: Any) -> bool:
    """A `RangeIndex` from 0 by 1: what a fresh DataFrame has (checked without pandas)."""
    return type(idx).__name__ == "RangeIndex" and getattr(idx, "start", None) == 0 and getattr(idx, "step", None) == 1


# --- formatting -------------------------------------------------------------


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, numbers.Real) and not isinstance(value, numbers.Integral):  # np.float32 and the like
        return bool(value != value)
    return type(value).__name__ in _MISSING_TYPES


def _is_number(value: Any) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _is_numeric_column(values: Iterable[Any]) -> bool:
    present = [v for v in values if not _is_missing(v)]
    return bool(present) and all(_is_number(v) for v in present)


def _default_format(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        return str(value)
    if isinstance(value, numbers.Integral):
        return str(int(value))
    number = float(value)
    if number != 0 and abs(number) < 0.005:  # {:.2f} would show 0.00
        return f"{number:.3g}"
    return f"{number:.2f}"


def _formatter(fmt: Any, label: Any) -> Callable[[Any], str]:
    if isinstance(fmt, Mapping):
        fmt = fmt.get(label, fmt.get(str(label)))
    if fmt is None:
        return _default_format
    if isinstance(fmt, str):
        return fmt.format
    return lambda value: str(fmt(value))


def _cell_text(value: Any, fmt: Callable[[Any], str]) -> str:
    return NA_TEXT if _is_missing(value) else fmt(value)
