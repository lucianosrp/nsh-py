"""`input`: a text field. Rust: src/elements/input.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import BoolProp, Element, IntProp, StrProp, props
from nsh._signals import Signal

KIND = "input"


def input(  # noqa: A001
    value: StrProp | None = None,
    *,
    placeholder: StrProp | None = None,
    on_change: Callable[[str], Any] | None = None,
    on_submit: Callable[[str], Any] | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
    disabled: BoolProp | None = None,
    readonly: BoolProp | None = None,
    masked: BoolProp | None = None,
    max_length: IntProp | None = None,
    multiline: BoolProp | None = None,
) -> Element:
    """A text field.

    `value` is what the field shows:

    - a **signal**: two-way. The field shows it, and typing sets it, then
      calls `on_change(text)` if given (which may set it again, to
      transform what was typed);
    - a **callable** (lambda, computed): one-way and read-only. The field
      shows what it returns, again whenever the signals it reads change;
      typing only calls `on_change(text)`;
    - a **string**: the first text, which the user then edits.

    `on_change(text)` runs on every edit and `on_submit(text)` when the user
    presses Enter (in a one-line field; in a `multiline` field Enter adds
    a line). An exception they raise is logged and the app keeps running.

    `disabled` greys the field out (`disabled:` styles) and blocks edits.
    `readonly` also blocks edits, but the field keeps its ordinary look:
    the text can be selected and copied. `masked` hides the characters
    (a password). `max_length` caps how many can be typed. `multiline`
    is a text area that grows with the text. Each of these takes a value
    or a callable, except `max_length` which takes an int or a callable.

        name = nsh.signal("")
        password = nsh.signal("")
        nsh.view(
            nsh.input(name, placeholder="Your name", test_id="name"),
            nsh.input(password, masked=True, placeholder="Password"),
            nsh.text(lambda: f"Hello, {name()}"),
        )
    """
    if isinstance(value, Signal):
        on_change = _set_then(value, on_change)
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
            readonly=readonly,
            masked=masked,
            max_length=max_length,
            multiline=multiline,
        ),
        [],
    )


def _set_then(value: Signal, on_change: Callable[[str], Any] | None) -> Callable[[str], Any]:
    """Typing's handler for a bound signal: set it, then call `on_change`."""
    if on_change is None:
        return value.set

    def changed(text: str) -> None:
        value.set(text)
        on_change(text)

    return changed
