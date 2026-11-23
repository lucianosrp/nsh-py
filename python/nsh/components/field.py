"""`field`: label, input, and optional help and validation text."""

from __future__ import annotations

from nsh._element import Child, Element, Prop, merge_class
from nsh.primitives import text, view

LABEL_CLASS = "text-sm font-medium"
HELP_CLASS = "text-xs text-muted-foreground"
ERROR_CLASS = "text-xs text-destructive"


def field(
    label: Prop[str],
    control: Child,
    *,
    help: Prop[str] | None = None,  # noqa: A002
    error: Prop[str | None] = None,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Element:
    """Wrap an input control with a label and optional help and error text.

    Pass `error` as a string or a binding. `None` and empty strings hide the error.
    A binding can show or hide the error as the signals it reads change.

        nsh.field(
            "Email",
            nsh.input(email),
            help="Use an address you check regularly.",
            error=lambda: "Include an @ sign." if email() and "@" not in email() else None,
        )
    """
    children: list[Child] = [text(label, class_=LABEL_CLASS), control]
    if help is not None:
        children.append(text(help, class_=HELP_CLASS))
    if callable(error):

        def error_text() -> Element | None:
            message = error()
            return text(message, class_=ERROR_CLASS) if message else None

        children.append(error_text)
    elif error:
        children.append(text(error, class_=ERROR_CLASS))

    return view(*children, class_=merge_class("gap-1", class_), test_id=test_id)
