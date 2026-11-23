"""`video`: a video player. Rust: src/elements/video.rs."""

from __future__ import annotations

from collections.abc import Callable
from os import PathLike
from typing import Any, NamedTuple

from nsh import _core
from nsh._element import Element, Handler, Prop, props
from nsh.primitives.image import FITS

KIND = "video"

Src = str | PathLike[str] | Callable[[], Any]
"""A path or URL, or a callable returning one (a binding)."""


class VideoInfo(NamedTuple):
    """What `on_load` gets: the length in seconds and the frames' size in pixels."""

    duration: float
    width: int
    height: int


class VideoProgress(NamedTuple):
    """What `on_progress` gets, in seconds."""

    current_time: float
    duration: float


class Video(Element):
    """A video element: what `nsh.video` returns, with `seek`."""

    __slots__ = ()

    def seek(self, seconds: float) -> None:
        """Jump to `seconds`. Works from any thread; does nothing while the
        video isn't shown."""
        self.props["ref"].seek(seconds)


def video(
    src: Src,
    *,
    paused: Prop[bool] | None = None,
    muted: Prop[bool] | None = None,
    volume: Prop[float] | None = None,
    rate: Prop[float] | None = None,
    repeat: Prop[bool] | None = None,
    controls: Prop[bool] | None = None,
    fit: Prop[str] | None = None,
    progress_interval: Prop[float] | None = None,
    on_load_start: Handler | None = None,
    on_load: Callable[[VideoInfo], Any] | None = None,
    on_progress: Callable[[VideoProgress], Any] | None = None,
    on_buffer: Callable[[bool], Any] | None = None,
    on_end: Handler | None = None,
    on_error: Callable[[str], Any] | None = None,
    class_: Prop[str] | None = None,
    test_id: str | None = None,
) -> Video:
    """A video playing the file or stream at `src`.

    `src` is a **path** (`str` or `os.PathLike`; a relative one is made
    absolute from the current working directory), an **`http(s)://` URL**
    or a `file:` URI, or a **callable** (a signal, a lambda) that it
    follows: a new value plays the new video.

    It plays as soon as it loads unless `paused`. `muted`, `volume` (0 to
    1), `rate` (the speed, 1 by default), `repeat` (start over at the end)
    and `controls` (the platform's playback controls) each take a value
    or a callable. `fit` is how the picture fills its box, as
    `nsh.image`'s, and `contain` by default. Size the box with `class_`:
    the video takes the size its classes give it, not the clip's.

    Events, all optional:

    - `on_load_start()`: loading began;
    - `on_load(info)`: ready to play. `info.duration` is in seconds and
      `info.width` and `info.height` in pixels;
    - `on_progress(p)`: while playing, every `progress_interval` seconds
      (0.25 by default). `p.current_time` and `p.duration` are in seconds;
    - `on_buffer(buffering)`: playback stalled for data (`True`) or
      resumed (`False`);
    - `on_end()`: it played to the end (with `repeat`, at every loop);
    - `on_error(message)`: loading or playback failed.

    `seek(seconds)` on the returned element jumps to a time:

        paused = nsh.signal(True)
        player = nsh.video(
            "https://example.com/clip.mp4",
            paused=paused,
            repeat=True,
            class_="h-56 bg-black",
        )
        nsh.view(
            player,
            nsh.button(lambda: "Play" if paused() else "Pause",
                       on_press=lambda: paused.update(lambda p: not p)),
            nsh.button("Restart", on_press=lambda: player.seek(0)),
        )
    """
    if fit is not None and not callable(fit) and fit not in FITS:
        raise ValueError(f"unknown fit {fit!r}; use contain, cover, fill, none or scale-down")
    return Video(
        KIND,
        props(
            src=src,
            paused=paused,
            muted=muted,
            volume=volume,
            rate=rate,
            repeat=repeat,
            controls=controls,
            fit=fit,
            progress_interval=progress_interval,
            on_load_start=on_load_start,
            on_load=None if on_load is None else lambda d, w, h: on_load(VideoInfo(d, w, h)),
            on_progress=(
                None if on_progress is None else lambda t, d: on_progress(VideoProgress(t, d))
            ),
            on_buffer=on_buffer,
            on_end=on_end,
            on_error=on_error,
            class_=class_,
            test_id=test_id,
            ref=_core.VideoRef(),
        ),
        [],
    )
