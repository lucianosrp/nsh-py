"""`input`: a one-line text field. Rust: src/elements/input.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Union

from nsh._element import Element, StrProp, props
from nsh._signals import Signal

KIND = "input"

BoolProp = Union[bool, Callable[[], Any]]
"""A bool, or a callable returning one (a binding)."""


def input(  # noqa: A001
    value: StrProp | None = None,
    *,
    placeholder: StrProp | None = None,
    on_change: Callable[[str], Any] | None = None,
    on_submit: Callable[[str], Any] | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
    disabled: BoolProp | None = None,
) -> Element:
    """A one-line text field.

    `value` is what the field shows:

    - a **signal**: two-way. The field shows it, and typing sets it
      (unless `on_change` is given: then `on_change(text)` runs instead
      and it's up to you to set the signal);
    - a **callable** (lambda, computed): one-way. The field shows what it
      returns, again whenever the signals it reads change; typing changes
      nothing unless you pass `on_change`;
    - a **string**: the first text, which the user then edits.

    `on_change(text)` runs on every edit and `on_submit(text)` when the user
    presses Enter. An exception they raise is logged and the app keeps
    running. `disabled` takes a bool or a callable.

        name = nsh.signal("")
        nsh.view(
            nsh.input(name, placeholder="Your name", test_id="name"),
            nsh.text(lambda: f"Hello, {name()}"),
        )
    """
    if on_change is None and isinstance(value, Signal):
        on_change = value.set
    return Element(
        KIND,
        props(
            value=value,
            placeholder=placeholder,
            on_change=on_change,
            on_submit=on_submit,
            class_=class_,
            test_id=test_id,
            disabled=disabled,
        ),
        [],
    )
