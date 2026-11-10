"""A focus timer: one signal for the time left, one for running or not."""

import nsh


def Focus(minutes=25):
    left = nsh.signal(minutes * 60)
    running = nsh.signal(False)

    def tick():
        if running.value and left.value > 0:
            left.update(lambda s: s - 1)

    nsh.set_interval(1, tick)

    return nsh.card(
        nsh.text(
            lambda: f"{left() // 60:02}:{left() % 60:02}", class_="text-6xl font-bold self-center"
        ),
        nsh.progress(lambda: minutes * 60 - left(), max=minutes * 60),
        nsh.view(
            nsh.button(
                lambda: "Pause" if running() else "Start",
                on_press=lambda: running.update(lambda r: not r),
                class_="flex-1",
            ),
            nsh.button("Reset", on_press=lambda: left.set(minutes * 60), class_="flex-1"),
            class_="flex-row gap-2",
        ),
        title="Focus",
        description=lambda: "Heads down." if running() else "Ready when you are.",
        class_="m-6 w-80",
    )


if __name__ == "__main__":
    nsh.run(Focus, title="Focus")
