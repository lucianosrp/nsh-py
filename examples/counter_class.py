"""The counter as a class: annotated attributes are state."""

import nsh


class Counter(nsh.Component):
    count: int = 0

    def update(self):
        self.count += 1

    def view(self):
        return nsh.view(
            nsh.text(lambda: f"Count: {self.count}", class_="text-xl"),
            nsh.button("Increment", on_press=self.update),
            class_="p-4 gap-2",
        )


if __name__ == "__main__":
    nsh.run(Counter, title="Counter")
