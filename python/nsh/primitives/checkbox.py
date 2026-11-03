"""`checkbox`: nsh-base's Checkbox. Rust: src/elements/checkbox.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import BoolProp, Child, Element, StrProp, props
from nsh.primitives import _toggle
from nsh.primitives.text import text

KIND = "checkbox"

INDICATOR_CLASS = (
    "h-4 w-4 items-center justify-center rounded-sm border border-primary "
    "transition-colors checked:bg-primary indeterminate:bg-primary disabled:opacity-50"
)
"""The box. `checked:`, `indeterminate:` and `disabled:` follow the checkbox."""

MARK_CLASS = "text-xs font-bold text-primary-foreground"
"""The mark in the box."""

LABEL_CLASS = "ml-2 text-sm"
"""The label, after the box (the checkbox lays them out in a row)."""

CHECK = "✓"
DASH = "–"
"""The marks: checked, and indeterminate."""


def checkbox(
    checked: BoolProp | None = None,
    label: StrProp | None = None,
    *,
    on_change: Callable[[bool], Any] | None = None,
    disabled: BoolProp | None = None,
    indeterminate: BoolProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A checkbox: a box with a check mark, then `label`.

    `checked` is its value:

    - a **signal**: two-way. The box shows it, and a press sets it (unless
      `on_change` is given: then `on_change(value)` runs instead and it's
      up to you to set the signal);
    - a **callable** (lambda, computed): one-way. The box shows what it
      returns; a press only calls `on_change`;
    - a **bool** (or nothing: unchecked): the first value. The checkbox
      keeps its own value and toggles by itself; `on_change(value)` runs
      after each press.

    `indeterminate` (a bool or a callable) shows a dash instead, for a
    "select all" over a partial selection; a press then asks for checked.
    `disabled` (a bool or a callable) ignores presses and dims it.
    `class_` takes Tailwind classes for where it sits (`"pl-6"`, `"w-64"`):
    they go on a view around it (NSH 0.3.0 doesn't style a component's
    root by classes).

        agree = nsh.signal(False)
        nsh.view(
            nsh.checkbox(agree, "I agree", test_id="agree"),
            nsh.button("Continue", on_press=..., class_=lambda: "" if agree() else "opacity-50"),
        )
    """
    value, handler = _toggle.state(checked, on_change)
    is_checked = _toggle.reader(value)
    is_mixed = _toggle.reader(indeterminate)
    mark = text(
        lambda: DASH if is_mixed() else CHECK if is_checked() else "",
        class_=MARK_CLASS,
    )
    children: list[Child] = []
    if label is not None:
        children.append(text(label, class_=_toggle.label_class(LABEL_CLASS, disabled)))
    return Element(
        KIND,
        props(
            checked=value,
            indeterminate=indeterminate,
            disabled=disabled,
            on_change=handler,
            indicator=mark,
            indicator_class=INDICATOR_CLASS,
            class_=class_,
            test_id=test_id,
        ),
        children,
    )
