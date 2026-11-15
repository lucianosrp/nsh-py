"""A row of avatars: initials, sizes, and a picture."""

import nsh


def App():
    return nsh.view(
        nsh.avatar("Ada Lovelace", size="sm"),
        nsh.avatar("Ada Lovelace"),
        nsh.avatar("Ada Lovelace", size="lg"),
        nsh.avatar("Ada Lovelace", src="examples/assets/dot.png", size="lg"),
        nsh.avatar(""),
        class_="flex-1 items-center justify-center gap-4 p-8",
    )


if __name__ == "__main__":
    nsh.run(App, title="Avatar")
