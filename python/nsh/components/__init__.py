"""Components: styled building blocks written in Python only.

Each module composes primitives (`nsh.primitives`) and Tailwind classes;
no Rust needed. To add one: `components/<name>.py`, export it here and in
`nsh/__init__.py`, and test it in `tests/components/test_<name>.py`.
See CONTRIBUTING.md ("Add a component").
"""

from nsh.components.avatar import avatar
from nsh.components.button import button
from nsh.components.card import card
from nsh.components.separator import separator
from nsh.components.table import table

__all__ = ["avatar", "button", "card", "separator", "table"]
