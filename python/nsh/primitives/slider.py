"""`slider`: nsh-base's Slider. Rust: src/elements/slider.rs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nsh._element import BoolProp, Child, Element, NumProp, StrProp, props
from nsh._signals import Signal
from nsh.primitives.text import text

KIND = "slider"

TRACK_CLASS = "h-6 w-full justify-center"
"""The track: tall enough for a finger; presses and drags land here."""

INDICATOR_CLASS = "h-1.5 w-full rounded-full bg-muted"
"""The rail the value maps onto, inside the track."""

RANGE_CLASS = "rounded-full bg-primary"
"""The filled stretch from `min` to the thumb."""

THUMB_CLASS = (
    "size-4 rounded-full border border-primary/50 bg-background shadow "
    "transition-colors focus-visible:ring-2 focus-visible:ring-ring "
    "disabled:opacity-50"
)
"""The thumb on the indicator; `focus-visible:` after a key focus."""

LABEL_CLASS = "mt-1 text-sm text-muted-foreground"
"""The label, under the track."""


def slider(
    value: NumProp | None = None,
    *,
    min: float = 0,  # noqa: A002
    max: float = 100,  # noqa: A002
    step: float = 1,
    on_change: Callable[[float], Any] | None = None,
    disabled: BoolProp | None = None,
    accessibility_label: StrProp | None = None,
    label: StrProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A slider: pick a number along a track between `min` and `max`
    (defaults 0 and 100), snapped to `step` (1 by default).

    `value` is what the thumb shows:

    - a **signal**: two-way. The slider shows it, and a drag or key sets
      it, then calls `on_change(n)` if given;
    - a **callable** (lambda, computed): one-way and read-only. The slider
      shows what it returns; a change only calls `on_change(n)`;
    - a **number** (or nothing: 0): the first value of a slider that keeps
      its own value.

    `on_change(n)` runs on every step of a drag and on each key. An
    exception it raises is logged and the app keeps running. `disabled`
    (a bool or a callable) ignores input and dims it. `class_` styles
    where it sits (`"w-64"`): they go on a view around it.
    `accessibility_label` names the thumb for screen readers. `label` is
    text under the track.

        volume = nsh.signal(40.0)
        nsh.slider(volume, min=0, max=100, step=5, test_id="vol")
    """
    if isinstance(value, Signal):
        on_change = _set_then(value, on_change)
    children: list[Child] = []
    if label is not None:
        children.append(text(label, class_=LABEL_CLASS))
    return Element(
        KIND,
        props(
            value=value,
            min=min,
            max=max,
            step=step,
            on_change=on_change,
            disabled=disabled,
            accessibility_label=accessibility_label,
            track_class=TRACK_CLASS,
            indicator_class=INDICATOR_CLASS,
            range_class=RANGE_CLASS,
            thumb_class=THUMB_CLASS,
            class_=class_,
            test_id=test_id,
        ),
        children,
    )


def _set_then(value: Signal, on_change: Callable[[float], Any] | None) -> Callable[[float], Any]:
    """A drag's handler for a bound signal: set it, then call `on_change`."""
    if on_change is None:
        return value.set

    def changed(n: float) -> None:
        value.set(n)
        on_change(n)

    return changed
