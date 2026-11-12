"""`progress`: nsh-base's Progress, a progress bar. Rust: src/elements/progress.rs."""

from __future__ import annotations

from nsh._element import BoolProp, Child, Element, NumProp, StrProp, props
from nsh.primitives.text import text

KIND = "progress"

TRACK_CLASS = "h-2 w-full rounded-full bg-primary/20 overflow-hidden"
"""The track, which the indicator fills."""

INDICATOR_CLASS = "h-full rounded-full bg-primary"
"""The indicator. Its width is the value's share of the track."""

INDETERMINATE_CLASS = "w-1/3"
"""The indicator's width while the extent is unknown."""

LABEL_CLASS = "mt-1 text-sm text-muted-foreground"
"""The label, under the track."""


def progress(
    value: NumProp | None = None,
    label: StrProp | None = None,
    *,
    max: float = 100,  # noqa: A002
    indeterminate: BoolProp | None = None,
    color: str | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A progress bar: how far `value` is out of `max` (100 by default, so
    a percentage; `max=1.0` takes a fraction), then `label`.

    `value` is a number, or a callable (a signal, a lambda) that it follows.
    It is held between 0 and `max`. `indeterminate` (a bool or a callable)
    shows that work is under way with no known end: no value, a short bar.
    `class_` takes Tailwind classes for where it sits (`"w-64"`): they go
    on a view around it, as `nsh.checkbox`'s do. `color` is a Tailwind
    colour for the bar instead of the theme's primary one (`"orange-500"`);
    the track is the same colour, faded.

        done = nsh.signal(0.0)
        nsh.progress(done, lambda: f"{done():.0%}", max=1.0)
    """
    if not max > 0:
        raise ValueError(f"progress max must be a positive number, not {max!r}")
    track, indicator = TRACK_CLASS, INDICATOR_CLASS
    if color is not None:
        track = track.replace("bg-primary/20", f"bg-{color}/20")
        indicator = indicator.replace("bg-primary", f"bg-{color}")
    if callable(indeterminate):
        indicator_class = lambda: (  # noqa: E731
            f"{indicator} {INDETERMINATE_CLASS}" if indeterminate() else indicator
        )
    elif indeterminate:
        indicator_class = f"{indicator} {INDETERMINATE_CLASS}"
    else:
        indicator_class = indicator
    children: list[Child] = []
    if label is not None:
        children.append(text(label, class_=LABEL_CLASS))
    return Element(
        KIND,
        props(
            value=value,
            max=max,
            indeterminate=indeterminate,
            track_class=track,
            indicator_class=indicator_class,
            class_=class_,
            test_id=test_id,
        ),
        children,
    )
