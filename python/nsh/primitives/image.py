"""`image`: a picture. Rust: src/elements/image.rs."""

from __future__ import annotations

from collections.abc import Callable
from os import PathLike
from typing import Any

from nsh._element import Element, StrProp, props

KIND = "image"

FITS = frozenset({"contain", "cover", "fill", "none", "scale-down", "stretch", "center"})
"""How the picture fits its box. CSS names (`contain`, `cover`, `fill`,
`none`, `scale-down`) and NSH's `stretch` (`fill`) and `center` (`none`)."""

Src = str | PathLike[str] | bytes | bytearray | Callable[[], Any]
"""A path, URL, image bytes, or a callable returning one (a binding)."""


def image(
    src: Src,
    *,
    alt: StrProp | None = None,
    fit: StrProp | None = None,
    class_: StrProp | None = None,
    test_id: str | None = None,
) -> Element:
    """A picture.

    `src` is what it shows:

    - a **path** (`str` or `os.PathLike`): a file. A relative path is made
      absolute from the process current working directory (NSH only loads
      absolute paths);
    - an **`http(s)://` URL**, or a `data:`, `file:` or `asset:` URI;
    - **bytes** (PNG, JPEG, GIF, WebP, …): shown from memory;
    - a **callable** (lambda, signal, computed): bound. It may return any
      of the above, again whenever the signals it reads change.

    `fit` is how it fills its box (`contain`, `cover`, `fill`, `none`,
    `scale-down`). The default is cover. Size it with `class_`
    (`"w-32 h-32"`). `alt` is the screen-reader label.

        nsh.image("examples/assets/dot.png", alt="A blue square", class_="w-32 h-32")
        nsh.image(png_bytes, fit="contain", class_="w-16 h-16")
        nsh.image(lambda: url(), class_="w-32 h-32")
    """
    if fit is not None and not callable(fit) and fit not in FITS:
        raise ValueError(f"unknown fit {fit!r}; use contain, cover, fill, none or scale-down")
    return Element(
        KIND,
        props(src=src, alt=alt, fit=fit, class_=class_, test_id=test_id),
        [],
    )
