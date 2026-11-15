"""A video player with its props, events and seek.

Ported from NSH's live demo of the video element (shown at
https://nsh.dev/elements/video/):
https://github.com/longbridge/nsh/blob/v0.5.1/website/demos/el-video.tsx
Copyright 2026 Longbridge, Apache-2.0. Rewritten in Python with nsh.video,
switches for its toggles, and a breakpoint class for its wide layout.
"""

import nsh

# A short CC0 clip from MDN's examples.
FLOWER = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"

# The demo's `wide()` (a window 700 points wide or more) as a breakpoint.
WIDE = "min-[700px]"


def App():
    paused = nsh.signal(True)
    muted = nsh.signal(True)
    repeat = nsh.signal(True)
    controls = nsh.signal(False)
    fast = nsh.signal(False)
    time = nsh.signal(0.0)
    duration = nsh.signal(0.0)
    ratio = nsh.signal(16 / 9)
    status = nsh.signal("loading")
    ends = nsh.signal(0)

    def loaded(info):
        duration.set(info.duration)
        if info.height:
            ratio.set(info.width / info.height)
        status.set(f"on_load {info.width} × {info.height}")

    player = nsh.video(
        FLOWER,
        paused=paused,
        muted=muted,
        repeat=repeat,
        controls=controls,
        rate=lambda: 2 if fast() else 1,
        progress_interval=0.1,
        class_=lambda: f"w-full aspect-[{ratio()}] rounded-[14px] overflow-hidden bg-black",
        on_load_start=lambda: status.set("on_load_start"),
        on_load=loaded,
        on_progress=lambda p: time.set(p.current_time),
        on_buffer=lambda buffering: status.set("buffering" if buffering else "playing"),
        on_end=lambda: ends.update(lambda n: n + 1),
        on_error=lambda message: status.set(f"on_error {message}"),
        test_id="player",
    )

    return nsh.view(
        nsh.text("video", class_="text-2xl font-bold"),
        nsh.view(
            nsh.view(player, class_=f"justify-center {WIDE}:flex-1"),
            nsh.view(
                nsh.progress(lambda: time() / duration() * 100 if duration() else 0),
                nsh.text(
                    lambda: f"on_progress {time():.1f} / {duration():.1f} s", class_="font-mono"
                ),
                nsh.text(
                    lambda: f"{status()} · on_end {ends()}×",
                    class_="font-mono text-sm text-muted-foreground",
                ),
                nsh.view(
                    nsh.button(
                        lambda: "Play" if paused() else "Pause",
                        on_press=lambda: paused.update(lambda p: not p),
                    ),
                    nsh.button("seek(0)", on_press=lambda: player.seek(0)),
                    class_="flex-row flex-wrap gap-2",
                ),
                nsh.view(
                    nsh.switch("muted", checked=muted),
                    nsh.switch("repeat", checked=repeat),
                    nsh.switch("rate 2", checked=fast),
                    nsh.switch("controls", checked=controls),
                    class_="flex-row flex-wrap gap-4",
                ),
                class_=f"gap-3 justify-center {WIDE}:w-[300px]",
            ),
            class_=f"flex-1 gap-4 {WIDE}:flex-row",
        ),
        class_="flex-1 p-5 pt-6 gap-3.5",
    )


if __name__ == "__main__":
    nsh.run(App, title="Video", size=(960, 600))
