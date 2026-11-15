"""The tab primitive: nsh-base's Tab."""

import nsh
from nsh.primitives.tab import TAB_CLASS
from nsh.testing import open


def test_tab_props():
    t = nsh.tab("Overview", selected=True, class_="gap-1", test_id="overview")
    assert t.kind == "tab"
    assert t.props["selected"] is True
    assert t.props["class_"] == f"{TAB_CLASS} gap-1"
    assert nsh.tab("Overview").props["class_"] == TAB_CLASS
    assert t.props["test_id"] == "overview"
    assert t.children == ["Overview"]


def test_pressing_a_tab_runs_on_press():
    seen = []

    def App():
        return nsh.view(
            nsh.Element(
                "tabs",
                {"class_": "flex-row"},
                [
                    nsh.tab(
                        "One", selected=True, on_press=lambda: seen.append("One"), test_id="one"
                    ),
                    nsh.tab("Two", on_press=lambda: seen.append("Two"), test_id="two"),
                ],
            )
        )

    with open(App) as app:
        assert app.shows("One")
        app.press("id:two")
        assert seen == ["Two"]
        app.press("text:One")
        assert seen == ["Two", "One"]
