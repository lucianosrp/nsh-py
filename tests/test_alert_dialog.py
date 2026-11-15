"""The native alert-dialog binding."""

from types import SimpleNamespace

import pytest

import nsh
from nsh import _dialog
from nsh.testing import open


def test_actions_normalize_with_the_default_role():
    actions = _dialog._normalize_actions([{"id": "ok", "label": "OK"}])
    assert actions == [("ok", "OK", "default")]


@pytest.mark.parametrize(
    ("actions", "error", "message"),
    [
        ([], ValueError, "at least one action"),
        (
            [
                {"id": "one", "label": "One"},
                {"id": "two", "label": "Two"},
                {"id": "three", "label": "Three"},
                {"id": "four", "label": "Four"},
            ],
            ValueError,
            "at most 3 actions",
        ),
        (["not a mapping"], TypeError, "must be a mapping"),
        (
            [{"id": "ok", "label": "OK", "colour": "red"}],
            ValueError,
            "unknown fields: colour",
        ),
        ([{"label": "OK"}], ValueError, "needs an id"),
        ([{"id": "", "label": "OK"}], ValueError, "id must not be empty"),
        ([{"id": 1, "label": "OK"}], TypeError, "id must be a string"),
        ([{"id": "ok"}], ValueError, "needs a label"),
        ([{"id": "ok", "label": ""}], ValueError, "label must not be empty"),
        ([{"id": "ok", "label": 1}], TypeError, "label must be a string"),
        ([{"id": "ok", "label": "OK", "role": 1}], TypeError, "role must be a string"),
        ([{"id": "ok", "label": "OK", "role": "warning"}], ValueError, "role must be one of"),
        (
            [{"id": "same", "label": "One"}, {"id": "same", "label": "Two"}],
            ValueError,
            "is duplicated",
        ),
    ],
)
def test_rejects_invalid_actions(actions, error, message):
    with pytest.raises(error, match=message):
        _dialog._normalize_actions(actions)


def test_rejects_invalid_top_level_arguments():
    with pytest.raises(TypeError, match="title must be a string"):
        nsh.alert_dialog(1, actions=[{"id": "ok", "label": "OK"}])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="title must not be empty"):
        nsh.alert_dialog("", actions=[{"id": "ok", "label": "OK"}])
    with pytest.raises(TypeError, match="description"):
        nsh.alert_dialog(
            "Title",
            description=1,  # type: ignore[arg-type]
            actions=[{"id": "ok", "label": "OK"}],
        )
    with pytest.raises(TypeError, match="on_result"):
        nsh.alert_dialog(
            "Title",
            actions=[{"id": "ok", "label": "OK"}],
            on_result=1,  # type: ignore[arg-type]
        )


def test_forwards_the_normalized_native_call(monkeypatch):
    calls = []

    def native(*args):
        calls.append(args)

    monkeypatch.setattr(_dialog, "_native", SimpleNamespace(alert_dialog=native))
    result = lambda action: None  # noqa: E731

    nsh.alert_dialog(
        "Delete?",
        description="This cannot be undone.",
        actions=[
            {"id": "cancel", "label": "Cancel", "role": "cancel"},
            {"id": "delete", "label": "Delete", "role": "destructive"},
        ],
        on_result=result,
    )

    assert calls == [
        (
            "Delete?",
            "This cannot be undone.",
            [("cancel", "Cancel", "cancel"), ("delete", "Delete", "destructive")],
            result,
        )
    ]


def test_native_calls_require_app_code():
    with pytest.raises(RuntimeError, match="app code"):
        nsh.alert_dialog("Title", actions=[{"id": "ok", "label": "OK"}])


def test_cancel_result_reaches_python():
    def App():
        answer = nsh.signal("none")
        return nsh.view(
            nsh.text(answer, test_id="answer"),
            nsh.button(
                "Ask",
                on_press=lambda: nsh.alert_dialog(
                    "Delete?",
                    description="This cannot be undone.",
                    actions=[
                        {"id": "cancel", "label": "Cancel", "role": "cancel"},
                        {"id": "delete", "label": "Delete", "role": "destructive"},
                    ],
                    on_result=answer.set,
                ),
                test_id="ask",
            ),
        )

    with open(App) as app:
        app.press("id:ask")
        app.wait_for("cancel")
