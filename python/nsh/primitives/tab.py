"""`tab`: nsh-base's Tab. Rust: src/elements/tab.rs."""

from __future__ import annotations

from nsh._element import Child, Element, Handler, Prop, merge_class, props

KIND = "tab"

TAB_CLASS = "px-3 py-2 text-sm text-muted-foreground selected:text-foreground disabled:opacity-50"
"""The tab. `selected:` and `disabled:` follow the tab."""


def tab(
    *children: Child,
    selected: Prop[bool] | None = None,
    on_press: Handler | None = None,
    disabled: Prop[bool] | None = None,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """One tab of a [`tabs`] list: its label is `children`.

    `selected` (a bool or a callable) marks it for screen readers and
    `selected:` styles; the app owns the value. `on_press` runs when it is
    pressed or when an arrow key of its list moves focus to it. `disabled`
    ignores presses and dims it. `class_` styles the tab, after its
    defaults. Put tabs in `nsh.tabs` (or an `Element("tabs", ...)` list).

        page = nsh.signal("Overview")
        nsh.tab(
            "Overview",
            selected=lambda: page() == "Overview",
            on_press=page.setter("Overview"),
            test_id="overview",
        )
    """
    return Element(
        KIND,
        props(
            selected=selected,
            on_press=on_press,
            disabled=disabled,
            class_=merge_class(TAB_CLASS, class_),
            test_id=test_id,
        ),
        list(children),
    )
