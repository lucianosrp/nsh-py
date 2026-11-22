"""Slider: a value along a track, bound to a signal."""

import nsh


def App():
    volume = nsh.signal(40.0)
    brightness = nsh.signal(0.7)

    return nsh.view(
        nsh.text("Volume", class_="text-lg font-semibold"),
        nsh.slider(
            volume,
            min=0,
            max=100,
            step=5,
            label=lambda: f"{volume():.0f}%",
            accessibility_label="Volume",
            class_="w-72",
            test_id="volume",
        ),
        nsh.view(
            nsh.button("-5", on_press=volume.updater(lambda n: max(0.0, n - 5))),
            nsh.button("+5", on_press=volume.updater(lambda n: min(100.0, n + 5))),
            nsh.button("Mute", on_press=volume.setter(0.0)),
            class_="flex-row gap-2",
        ),
        nsh.text("Brightness", class_="text-lg font-semibold pt-2"),
        nsh.slider(
            brightness,
            min=0,
            max=1,
            step=0.05,
            label=lambda: f"{brightness():.0%}",
            accessibility_label="Brightness",
            class_="w-72",
            test_id="brightness",
        ),
        class_="p-6 gap-3",
    )


if __name__ == "__main__":
    nsh.run(App, title="Slider")
