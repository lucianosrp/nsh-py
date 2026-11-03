## What and why

<!-- One or two plain sentences. Link the issue: "Closes #123". -->

## Screenshot

<!-- If this changes what you see, add a screenshot. Otherwise delete this section. -->

## Checklist

- [ ] `uv run pytest -q tests` passes.
- [ ] `ruff check` and `ruff format --check` pass (CI runs them).
- [ ] New components or primitives have a test, and a docstring with an example.
- [ ] Public names are exported from `nsh/__init__.py`.
- [ ] Rust changes pass `cargo fmt` and `cargo clippy -- -D warnings`.
- [ ] One topic per PR, and commits that each make sense on their own.
