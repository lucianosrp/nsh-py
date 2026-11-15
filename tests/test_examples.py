"""Checks on the example scripts themselves."""

import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_no_example_shadows_a_stdlib_module():
    # `python examples/x.py` puts examples/ first on sys.path, so an
    # examples/select.py would replace the stdlib `select` for every example.
    clashes = sorted(
        p.name
        for p in EXAMPLES.iterdir()
        if p.stem in sys.stdlib_module_names and (p.suffix == ".py" or p.is_dir())
    )
    assert not clashes, f"rename these examples, they shadow stdlib modules: {clashes}"
