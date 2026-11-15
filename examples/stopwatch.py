"""Two stopwatches from one class: state, a prop, a timer and a property."""

import nsh


class Stopwatch(nsh.Component):
    label: str = "Stopwatch"  # a prop: Stopwatch(label="Tea")
    seconds: int = 0
    running: bool = False

    def setup(self):  # runs once, before view()
        nsh.set_interval(1, self.tick)

    def tick(self):
        if self.running:
            self.seconds += 1

    def toggle(self):
        self.running = not self.running

    def reset(self):
        self.seconds = 0

    @property
    def clock(self):  # follows seconds, like a computed
        return f"{self.seconds // 60:02}:{self.seconds % 60:02}"

    def view(self):
        return nsh.card(
            nsh.text(lambda: self.clock, class_="text-4xl font-bold"),
            nsh.view(
                nsh.button(lambda: "Pause" if self.running else "Start", on_press=self.toggle),
                nsh.button("Reset", on_press=self.reset),
                class_="flex-row gap-2",
            ),
            title=self.label,
        )


def App():
    return nsh.view(Stopwatch(label="Tea"), Stopwatch(label="Eggs"), class_="p-4 gap-4")


if __name__ == "__main__":
    nsh.run(App, title="Stopwatches")
