"""A live monitor: a timer moves the load, and every bar and label follows."""

import random

import nsh

SERVICES = ["api", "auth", "search", "billing", "email"]


def jiggle(load):
    return {s: min(98, max(2, n + random.randint(-15, 15))) for s, n in load.items()}


def Monitor():
    load = nsh.signal(dict.fromkeys(SERVICES, 40))
    nsh.set_interval(0.5, lambda: load.update(jiggle))
    busiest = nsh.computed(lambda: max(load(), key=load().get))

    def row(service):
        def pct():
            return load()[service]

        return nsh.view(
            nsh.text(service, class_="w-16"),
            nsh.progress(pct, class_="flex-1"),
            nsh.text(lambda: f"{pct()}%", class_="w-10"),
            class_="flex-row items-center gap-3",
        )

    return nsh.card(
        *[row(s) for s in SERVICES],
        title="Cluster load",
        description=lambda: f"Busiest: {busiest()}",
        class_="m-6 w-96",
    )


if __name__ == "__main__":
    nsh.run(Monitor, title="Monitor")
