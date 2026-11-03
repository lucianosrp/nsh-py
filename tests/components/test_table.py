"""The table component."""

from collections import namedtuple

import pytest

import nsh
from nsh.components.table import (
    CELL_CLASS,
    HEADER_CELL_CLASS,
    INDEX_WIDTH,
    NA_TEXT,
    NUMBER_CLASS,
    ROOT_CLASS,
    STRIPE_CLASS,
)
from nsh.testing import open


def header_of(t):
    return [c.props["content"] for c in t.children[0].children]


def body_of(t):
    """The cell texts of every body row (rows are the views after the header)."""
    return [[c.props["content"] for c in row.children] for row in t.children[1:] if row.kind == "view"]


def has_class(el, name):
    return name in el.props["class_"].split()


# --- props: each input shape ------------------------------------------------


def test_records():
    t = nsh.table([{"name": "Ada", "age": 36}, {"name": "Bo", "age": 41, "extra": True}], test_id="t")
    assert t.kind == "view"
    assert t.props == {"class_": ROOT_CLASS, "test_id": "t"}
    assert header_of(t) == ["name", "age", "extra"]
    assert body_of(t) == [["Ada", "36", NA_TEXT], ["Bo", "41", "True"]]


def test_dict_of_lists():
    t = nsh.table({"a": [1, 2], "b": ["x", "y"]})
    assert header_of(t) == ["a", "b"]
    assert body_of(t) == [["1", "x"], ["2", "y"]]


def test_dict_of_lists_must_be_rectangular():
    with pytest.raises(ValueError, match="same length"):
        nsh.table({"a": [1, 2], "b": [1]})


def test_list_of_lists_with_columns():
    t = nsh.table([[1, 2.5], [3, 4.0]], columns=["n", "x"])
    assert header_of(t) == ["n", "x"]
    assert body_of(t) == [["1", "2.50"], ["3", "4.00"]]


def test_list_of_lists_without_columns_numbers_them():
    t = nsh.table([("a", 1), ("b", 2)])
    assert header_of(t) == ["0", "1"]


def test_list_of_lists_wrong_number_of_columns():
    with pytest.raises(ValueError, match="column names"):
        nsh.table([[1, 2]], columns=["only"])


def test_namedtuples_name_the_columns():
    P = namedtuple("P", "x y")
    t = nsh.table([P(1, 2), P(3, 4)])
    assert header_of(t) == ["x", "y"]


def test_columns_select_and_order():
    t = nsh.table([{"a": 1, "b": 2, "c": 3}], columns=["c", "a"])
    assert header_of(t) == ["c", "a"]
    assert body_of(t) == [["3", "1"]]


def test_unknown_column():
    with pytest.raises(ValueError, match="no column 'zz'"):
        nsh.table([{"a": 1}], columns=["zz"])


def test_rejects_a_string():
    with pytest.raises(TypeError):
        nsh.table("hello")


def test_empty_data():
    t = nsh.table([], columns=["a", "b"])
    assert header_of(t) == ["a", "b"]
    assert t.children[1].props["content"] == "No rows"


def test_row_numbers_with_index_true():
    t = nsh.table([{"a": "x"}, {"a": "y"}], index=True)
    assert header_of(t) == ["", "a"]
    assert body_of(t) == [["0", "x"], ["1", "y"]]
    assert INDEX_WIDTH in t.children[1].children[0].props["class_"].split()


def test_numpy_2d_array():
    np = pytest.importorskip("numpy")
    t = nsh.table(np.array([[1, 2], [3, 4]]), columns=["a", "b"])
    assert body_of(t) == [["1", "2"], ["3", "4"]]


# --- props: layout and formatting -------------------------------------------


def test_class_and_header_options():
    t = nsh.table([{"a": 1}], header=False, class_="w-80")
    assert t.props["class_"] == f"{ROOT_CLASS} w-80"
    assert len(t.children) == 1  # no header row, one body row
    assert callable(nsh.table([{"a": 1}], class_=lambda: "w-80").props["class_"])


def test_striped_rows():
    t = nsh.table([{"a": i} for i in range(4)])
    rows = t.children[1:]
    assert [STRIPE_CLASS in r.props["class_"] for r in rows] == [False, True, False, True]
    plain = nsh.table([{"a": i} for i in range(3)], striped=False).children[1:]
    assert not any(STRIPE_CLASS in r.props["class_"] for r in plain)
    assert [("border-t" in r.props["class_"].split()) for r in plain] == [False, True, True]


def test_numbers_right_aligned_per_column():
    t = nsh.table([{"n": 1, "s": "a", "mixed": 1}, {"n": 2.5, "s": "b", "mixed": "x"}])
    header = t.children[0].children
    assert [has_class(c, NUMBER_CLASS) for c in header] == [True, False, False]
    row = t.children[1].children
    assert [has_class(c, NUMBER_CLASS) for c in row] == [True, False, False]
    assert HEADER_CELL_CLASS in header[0].props["class_"]
    assert CELL_CLASS in row[0].props["class_"]


def test_default_formatting():
    t = nsh.table([{"i": 7, "f": 3.14159, "tiny": 0.0001234, "zero": 0.0, "big": 1234567.891, "b": True}])
    assert body_of(t) == [["7", "3.14", "0.000123", "0.00", "1234567.89", "True"]]


def test_missing_values():
    t = nsh.table([{"a": None, "b": float("nan"), "c": 1.0}, {"a": 1, "b": 2.0, "c": None}])
    assert body_of(t) == [[NA_TEXT, NA_TEXT, "1.00"], ["1", "2.00", NA_TEXT]]
    # A column of numbers with gaps is still numeric.
    assert has_class(t.children[1].children[0], NUMBER_CLASS)


def test_format_callable_string_and_dict():
    data = [{"price": 9.5, "qty": 3, "name": "pen"}]
    assert body_of(nsh.table(data, format=lambda v: f"<{v}>")) == [["<9.5>", "<3>", "<pen>"]]
    assert body_of(nsh.table(data, format={"price": "${:,.1f}", "qty": lambda n: f"{n}x"})) == [
        ["$9.5", "3x", "pen"]
    ]
    # Missing values skip the hook.
    assert body_of(nsh.table([{"a": None}], format=lambda v: "!")) == [[NA_TEXT]]


def test_widths():
    t = nsh.table([{"a": 1, "b": 2}], widths={"a": "w-48"})
    a, b = t.children[1].children
    assert "w-48" in a.props["class_"].split() and "flex-1" not in a.props["class_"].split()
    assert "flex-1" in b.props["class_"].split()


def test_test_ids():
    t = nsh.table([{"a": 1}, {"a": 2}, {"a": 3}], max_rows=2, test_id="tbl")
    assert t.children[0].props["test_id"] == "tbl-header"
    assert [r.props["test_id"] for r in t.children[1:3]] == ["tbl-row-0", "tbl-row-1"]
    assert t.children[3].props["test_id"] == "tbl-more"
    assert "test_id" not in nsh.table([{"a": 1}]).children[1].props


def test_max_rows_footer():
    t = nsh.table([{"a": i} for i in range(10)], max_rows=3)
    assert len(body_of(t)) == 3
    assert t.children[-1].props["content"] == "… 7 more rows"
    t = nsh.table([{"a": i} for i in range(4)], max_rows=3)
    assert t.children[-1].props["content"] == "… 1 more row"
    assert nsh.table([{"a": 1}], max_rows=3).children[-1].kind == "view"  # no footer


def test_callable_data_is_a_region():
    t = nsh.table(lambda: [{"a": 1}], test_id="t")
    (region,) = t.children
    assert callable(region)
    assert region()[0].props["test_id"] == "t-header"


# --- pandas / polars (duck typed) -------------------------------------------


def test_pandas_dataframe():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"city": ["Oslo", "Rome", None], "temp": [4.5, 18.25, float("nan")], "n": [1, 2, 3]})
    t = nsh.table(df)
    assert header_of(t) == ["city", "temp", "n"]  # the default RangeIndex is hidden
    assert body_of(t) == [["Oslo", "4.50", "1"], ["Rome", "18.25", "2"], [NA_TEXT, NA_TEXT, "3"]]
    assert [has_class(c, NUMBER_CLASS) for c in t.children[1].children] == [False, True, True]


def test_pandas_missing_kinds():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-01-02", None]),
            "k": pd.array([1, None], dtype="Int64"),
            "ok": [True, False],
        }
    )
    assert body_of(nsh.table(df)) == [["2024-01-02 00:00:00", "1", "True"], [NA_TEXT, NA_TEXT, "False"]]


def test_pandas_non_default_index_is_shown():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"x": [3, 1, 2]}, index=pd.Index(["a", "b", "c"], name="key"))
    t = nsh.table(df)
    assert header_of(t) == ["key", "x"]
    assert body_of(t) == [["a", "3"], ["b", "1"], ["c", "2"]]
    assert header_of(nsh.table(df, index=False)) == ["x"]
    # A sorted frame keeps its old index, so it shows (like pandas does)...
    sorted_df = pd.DataFrame({"x": [3, 1, 2]}).sort_values("x")
    assert body_of(nsh.table(sorted_df)) == [["1", "1"], ["2", "2"], ["0", "3"]]
    # ... and a reset one doesn't.
    assert header_of(nsh.table(sorted_df.reset_index(drop=True))) == ["x"]


def test_pandas_index_true_and_multiindex():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"x": [1, 2]})
    assert body_of(nsh.table(df, index=True)) == [["0", "1"], ["1", "2"]]
    mi = pd.DataFrame({"x": [1, 2]}, index=pd.MultiIndex.from_tuples([("a", 1), ("a", 2)], names=["g", "i"]))
    t = nsh.table(mi)
    assert header_of(t) == ["g", "i", "x"]
    assert body_of(t) == [["a", "1", "1"], ["a", "2", "2"]]
    assert all(INDEX_WIDTH in c.props["class_"].split() for c in t.children[1].children[:2])


def test_pandas_columns_max_rows_and_format():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": range(100), "b": [i / 3 for i in range(100)], "c": ["x"] * 100})
    t = nsh.table(df, columns=["b", "a"], max_rows=2, format={"b": "{:.1f}"})
    assert header_of(t) == ["b", "a"]
    assert body_of(t) == [["0.0", "0"], ["0.3", "1"]]
    assert t.children[-1].props["content"] == "… 98 more rows"


def test_polars_like_frame():
    # A stand-in with polars' shape (`columns`, `iter_rows`, `head`, `len`): polars isn't a dependency.
    class Frame:
        columns = ["a", "b"]

        def __len__(self):
            return 3

        def head(self, n):
            return Frame2(n)

        def iter_rows(self):
            return iter([(1, "x"), (2, None), (3, "z")])

    class Frame2(Frame):
        def __init__(self, n):
            self.n = n

        def iter_rows(self):
            return iter([(1, "x"), (2, None), (3, "z")][: self.n])

    t = nsh.table(Frame(), max_rows=2)
    assert header_of(t) == ["a", "b"]
    assert body_of(t) == [["1", "x"], ["2", NA_TEXT]]
    assert t.children[-1].props["content"] == "… 1 more row"


def test_polars_dataframe():
    pl = pytest.importorskip("polars")
    t = nsh.table(pl.DataFrame({"a": [1, 2], "b": ["x", None]}))
    assert body_of(t) == [["1", "x"], ["2", NA_TEXT]]


# --- headless ---------------------------------------------------------------


def test_table_shows_cells():
    with open(lambda: nsh.table([{"name": "Ada", "score": 9.5}, {"name": "Bo", "score": 7}])) as app:
        for shown in ("name", "score", "Ada", "9.50", "Bo", "7"):
            assert app.shows(shown)


def test_table_max_rows_footer_shows():
    with open(lambda: nsh.table([{"n": i} for i in range(20)], max_rows=3)) as app:
        assert app.shows("… 17 more rows")
        assert app.shows("2")
        assert not app.shows("3")


def test_table_test_id_selects_rows():
    with open(lambda: nsh.table([{"n": "first"}, {"n": "second"}], test_id="t")) as app:
        app.wait_for("id:t-row-1")
        app.wait_for("id:t")


def test_table_follows_a_signal_of_records():
    def App():
        rows = nsh.signal([{"n": "old"}])
        return nsh.view(
            nsh.button("Swap", on_press=lambda: rows.set([{"n": "new"}, {"n": "newer"}]), test_id="swap"),
            nsh.table(rows),
        )

    with open(App) as app:
        assert app.shows("old")
        app.press("id:swap")
        app.wait_for("newer")
        assert app.shows("new")
        assert not app.shows("old")


def test_table_follows_a_lambda_over_a_signal():
    def App():
        n = nsh.signal(1)
        return nsh.view(
            nsh.button("More", on_press=lambda: n.update(lambda k: k + 1), test_id="more"),
            nsh.table(lambda: {"k": list(range(n()))}, max_rows=2),
        )

    with open(App) as app:
        assert not app.shows("… 1 more row")
        app.press("id:more")
        app.press("id:more")
        app.wait_for("… 1 more row")


def test_table_follows_a_dataframe_signal():
    pd = pytest.importorskip("pandas")

    def App():
        df = nsh.signal(pd.DataFrame({"city": ["Oslo"], "temp": [4.5]}))
        return nsh.view(
            nsh.button(
                "Swap",
                on_press=lambda: df.set(pd.DataFrame({"city": ["Rome", "Cairo"], "temp": [18.25, 30.0]})),
                test_id="swap",
            ),
            nsh.button("Add column", on_press=lambda: df.update(lambda d: d.assign(rain=1)), test_id="col"),
            nsh.table(df),
        )

    with open(App) as app:
        assert app.shows("Oslo")
        app.press("id:swap")
        app.wait_for("Cairo")
        assert app.shows("18.25")
        assert not app.shows("Oslo")
        app.press("id:col")
        app.wait_for("rain")


def test_signal_set_with_dataframes_counts_as_changed():
    # DataFrame == is element-wise and raises in bool(); `Signal.set` must treat that as "changed".
    pd = pytest.importorskip("pandas")
    s = nsh.signal(pd.DataFrame({"a": [1, 2]}))
    new = pd.DataFrame({"a": [1, 2]})  # equal, but not the same object
    s.set(new)
    assert s.peek() is new
