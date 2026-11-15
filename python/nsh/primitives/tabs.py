"""`tabs`: nsh-base's Tabs, a tab list. Rust: src/elements/tabs.rs."""

from __future__ import annotations

from nsh._element import Child, Element, StrProp, merge_class, props

KIND = "tabs"

LIST_CLASS = "flex-row gap-0 border-b border-border"
"""The tab list: a row with a bottom edge the indicator rides on."""

INDICATOR_CLASS = "bottom-0 h-0.5 bg-primary"
"""The underline under the selected tab; travels with a spring."""


def tabs(
    *children: Child,
    class_: StrProp | None = None,
    indicator_class: StrProp | None = INDICATOR_CLASS,
    test_id: str | None = None,
) -> Element:
    """A tab list: its children are `nsh.tab`s (and any views between them).

    The list holds no value: each tab is told whether it is selected and
    reports a press; the app keeps which one is and shows that tab's
    content next to the list. `class_` styles the list, after its defaults
    (later utilities win: a sidebar passes `"flex-col gap-1"`). nsh-base
    still forces a row in a terminal. `indicator_class` is the underline /
    pill that follows the selected tab; pass `None` for none.

        page = nsh.signal("Overview")
        nsh.view(
            nsh.tabs(
                nsh.tab(
                    "Overview",
                    selected=lambda: page() == "Overview",
                    on_press=page.setter("Overview"),
                ),
                nsh.tab(
                    "Orders",
                    selected=lambda: page() == "Orders",
                    on_press=page.setter("Orders"),
                ),
                test_id="sections",
            ),
            lambda: overview() if page() == "Overview" else orders(),
            class_="gap-4",
        )
    """
    return Element(
        KIND,
        props(
            indicator_class=indicator_class,
            class_=merge_class(LIST_CLASS, class_),
            test_id=test_id,
        ),
        list(children),
    )
