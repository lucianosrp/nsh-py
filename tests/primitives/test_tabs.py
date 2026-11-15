"""The tabs primitive: nsh-base's Tabs (the tab list)."""

import nsh
from nsh.primitives.tabs import INDICATOR_CLASS, LIST_CLASS
from nsh.testing import open


def test_tabs_props():
    el = nsh.tabs(
        nsh.tab("Overview", selected=True),
        nsh.tab("Orders"),
        class_="flex-col gap-1",
        indicator_class=None,
        test_id="sections",
    )
    assert el.kind == "tabs"
    assert el.props["class_"] == f"{LIST_CLASS} flex-col gap-1"
    assert "indicator_class" not in el.props
    assert el.props["test_id"] == "sections"
    assert len(el.children) == 2
    assert el.children[0].kind == "tab"


def test_tabs_defaults():
    el = nsh.tabs(nsh.tab("A"), nsh.tab("B"))
    assert el.props["class_"] == LIST_CLASS
    assert el.props["indicator_class"] == INDICATOR_CLASS


def test_pressing_a_tab_shows_its_panel():
    panels = {
        "Overview": "Visitors this week",
        "Orders": "Shipments on the way",
        "Billing": "Invoices and plans",
    }

    def App():
        page = nsh.signal("Overview")

        def section(label: str):
            return nsh.tab(
                label,
                selected=lambda: page() == label,
                on_press=page.setter(label),
                test_id=f"sections-{label}",
            )

        return nsh.view(
            nsh.tabs(*[section(label) for label in panels], test_id="sections"),
            lambda: nsh.text(panels[page()]),
            class_="gap-4",
        )

    with open(App) as app:
        assert app.shows("Visitors this week")
        assert not app.shows("Shipments on the way")
        app.press("id:sections-Orders")
        app.wait_for("Shipments on the way")
        assert not app.shows("Visitors this week")
        app.press("text:Billing")
        app.wait_for("Invoices and plans")
        app.press("role:tab[Overview]")
        app.wait_for("Visitors this week")
