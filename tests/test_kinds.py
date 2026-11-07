"""Python's primitives and Rust's element kinds must match one to one."""

from nsh import _core, primitives


def test_python_primitives_match_rust_kinds():
    rust = set(_core.element_kinds())
    python = set(primitives.KINDS)
    assert python - rust == set(), (
        "Python primitives with no Rust builder (add src/elements/<kind>.rs)"
    )
    assert rust - python == set(), (
        "Rust kinds with no Python primitive (add python/nsh/primitives/<kind>.py)"
    )


def test_unknown_kind_is_reported(caplog):
    import nsh
    from nsh.testing import open

    with open(lambda: nsh.Element("nope", {}, [])) as app:
        assert app.shows("The app's root raised an exception")
    assert 'unknown element kind "nope"' in caplog.text
