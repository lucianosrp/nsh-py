"""`alert_dialog`: show a native alert dialog. Rust: src/alert_dialog.rs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from nsh import _core as _native

ActionResult = Callable[[str | None], Any]
"""Called with the chosen action's id, or `None` if the dialog was dismissed."""

ROLES = frozenset({"default", "cancel", "destructive"})
"""The roles a native alert-dialog action can have."""

MAX_ACTIONS = 3
"""Android alerts show at most three actions."""


def alert_dialog(
    title: str,
    *,
    description: str | None = None,
    actions: Sequence[Mapping[str, str]],
    on_result: ActionResult | None = None,
) -> None:
    """Show a native alert dialog with `title`, `description` and `actions`.

    Each action is a mapping with a stable `id`, a display `label`, and an
    optional `role`: `"default"`, `"cancel"` or `"destructive"`. `on_result`
    runs after the dialog closes with the chosen action's id, or `None` when
    it was dismissed without choosing one.

    This must be called from app code, such as an `on_press` handler.

        nsh.alert_dialog(
            "Delete the photo?",
            description="This cannot be undone.",
            actions=[
                {"id": "cancel", "label": "Cancel", "role": "cancel"},
                {"id": "delete", "label": "Delete", "role": "destructive"},
            ],
            on_result=handle_result,
        )
    """
    if not isinstance(title, str):
        raise TypeError("alert_dialog title must be a string")
    if not title:
        raise ValueError("alert_dialog title must not be empty")
    if description is not None and not isinstance(description, str):
        raise TypeError("alert_dialog description must be a string or None")
    if on_result is not None and not callable(on_result):
        raise TypeError("alert_dialog on_result must be callable or None")

    normalized = _normalize_actions(actions)
    _native.alert_dialog(title, description, normalized, on_result)


def _normalize_actions(
    actions: Sequence[Mapping[str, str]],
) -> list[tuple[str, str, str]]:
    """Validate action mappings and turn them into `(id, label, role)` tuples."""
    if isinstance(actions, (str, bytes)) or not isinstance(actions, Sequence):
        raise TypeError("alert_dialog actions must be a sequence of mappings")
    if not actions:
        raise ValueError("alert_dialog requires at least one action")
    if len(actions) > MAX_ACTIONS:
        raise ValueError(f"alert_dialog accepts at most {MAX_ACTIONS} actions")

    normalized: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for position, action in enumerate(actions, start=1):
        if not isinstance(action, Mapping):
            raise TypeError(f"alert_dialog action {position} must be a mapping")

        unexpected = set(action) - {"id", "label", "role"}
        if unexpected:
            names = ", ".join(sorted(str(name) for name in unexpected))
            raise ValueError(f"alert_dialog action {position} has unknown fields: {names}")

        if "id" not in action:
            raise ValueError(f"alert_dialog action {position} needs an id")
        if "label" not in action:
            raise ValueError(f"alert_dialog action {position} needs a label")

        action_id = action["id"]
        label = action["label"]
        role = action.get("role", "default")

        if not isinstance(action_id, str):
            raise TypeError(f"alert_dialog action {position} id must be a string")
        if not action_id:
            raise ValueError(f"alert_dialog action {position} id must not be empty")
        if not isinstance(label, str):
            raise TypeError(f"alert_dialog action {position} label must be a string")
        if not label:
            raise ValueError(f"alert_dialog action {position} label must not be empty")
        if not isinstance(role, str):
            raise TypeError(f"alert_dialog action {position} role must be a string")
        if role not in ROLES:
            choices = ", ".join(sorted(ROLES))
            raise ValueError(f"alert_dialog action {position} role must be one of: {choices}")
        if action_id in seen:
            raise ValueError(f"alert_dialog action id {action_id!r} is duplicated")

        seen.add(action_id)
        normalized.append((action_id, label, role))

    return normalized
