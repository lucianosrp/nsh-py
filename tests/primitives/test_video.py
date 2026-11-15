"""The video primitive."""

import threading

import pytest

import nsh
from nsh.primitives.video import KIND
from nsh.testing import open

CLIP = "https://example.com/clip.mp4"


def test_video_props():
    paused = nsh.signal(True)
    el = nsh.video(CLIP, paused=paused, repeat=True, rate=2, fit="cover", test_id="player")
    assert isinstance(el, nsh.Video)
    assert el.kind == KIND
    assert el.children == []
    assert el.props["src"] == CLIP
    assert el.props["paused"] is paused
    assert el.props["repeat"] is True
    assert el.props["rate"] == 2
    assert el.props["fit"] == "cover"
    assert el.props["test_id"] == "player"
    assert set(nsh.video("clip.mp4").props) == {"src", "ref"}


def test_unknown_fit_raises():
    with pytest.raises(ValueError, match="unknown fit 'stretchy'"):
        nsh.video(CLIP, fit="stretchy")


def test_events_reach_python():
    def App():
        log = nsh.signal("")

        def add(entry):
            log.update(lambda s: f"{s} {entry}".strip())

        return nsh.view(
            nsh.video(
                CLIP,
                class_="w-64 h-36",
                test_id="player",
                on_load_start=lambda: add("start"),
                on_load=lambda info: add(repr(info)),
                on_progress=lambda p: add(repr(p)),
                on_buffer=lambda buffering: add(f"buffer={buffering}"),
                on_end=lambda: add("end"),
                on_error=lambda message: add(f"error={message}"),
            ),
            nsh.text(lambda: f"log: {log()}"),
        )

    with open(App) as app:
        app.dispatch("player", "onLoadStart")
        app.dispatch("player", "onLoad", duration=5.5, width=640, height=360)
        app.dispatch("player", "onProgress", currentTime=1.5, duration=5.5)
        app.dispatch("player", "onBuffer", isBuffering=True)
        app.dispatch("player", "onEnd")
        app.dispatch("player", "onError", message="gone")
        info = nsh.VideoInfo(duration=5.5, width=640, height=360)
        progress = nsh.VideoProgress(current_time=1.5, duration=5.5)
        app.wait_for(f"text:log: start {info!r} {progress!r} buffer=True end error=gone")


def test_seek():
    def App():
        player = nsh.video(CLIP, class_="w-64 h-36", test_id="player")
        done = nsh.signal(False)

        def from_a_thread():
            player.seek(1)
            nsh.call_soon(done.set, True)  # posted after the seek: runs after it

        return nsh.view(
            player,
            nsh.button("restart", on_press=lambda: player.seek(0), test_id="restart"),
            nsh.button("thread", on_press=lambda: threading.Thread(target=from_a_thread).start()),
            nsh.text(lambda: "done" if done() else "waiting"),
        )

    with open(App) as app:
        assert app.seeks("player") == []
        app.press("id:restart")
        assert app.seeks("player") == [0.0]
        app.press("thread")
        app.wait_for("done")
        assert app.seeks("player") == [0.0, 1.0]


def test_seek_reaches_a_rebuilt_video():
    def App():
        show = nsh.signal(True)
        player = nsh.video(CLIP, class_="w-64 h-36", test_id="player")
        return nsh.view(
            lambda: player if show() else None,
            nsh.button("toggle", on_press=lambda: show.update(lambda s: not s), test_id="toggle"),
            nsh.button("seek", on_press=lambda: player.seek(3), test_id="seek"),
        )

    with open(App) as app:
        app.press("id:toggle")
        app.press("id:toggle")
        app.press("id:seek")
        assert app.seeks("id:player") == [3.0]


def test_seek_before_the_video_is_shown_does_nothing():
    nsh.video(CLIP).seek(3)


def test_bound_props_build():
    def App():
        on = nsh.signal(False)
        return nsh.view(
            nsh.video(
                lambda: CLIP if on() else "clip.mp4",
                paused=on,
                muted=lambda: not on(),
                volume=lambda: 0.5 if on() else 1,
                rate=lambda: 2 if on() else 1,
                controls=on,
                fit=lambda: "cover" if on() else "contain",
                progress_interval=0.1,
                class_=lambda: f"w-full aspect-[{1.5 if on() else 1.25}]",
            ),
            nsh.button("flip", on_press=on.setter(True), test_id="flip"),
            nsh.text(lambda: "on" if on() else "off"),
        )

    with open(App) as app:
        assert app.shows("off")
        app.press("id:flip")
        app.wait_for("on")


def test_unknown_fit_on_the_element_is_reported(caplog):
    with open(lambda: nsh.Element("video", {"src": CLIP, "fit": "nope"}, [])) as app:
        assert app.shows("The app's root raised an exception")
    assert "unknown fit" in caplog.text
