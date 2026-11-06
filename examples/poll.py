"""The README's poll: a signal of votes, a computed, a table that re-sorts."""

import nsh


def Poll():
    votes = nsh.signal({"Python": 8, "Rust": 3, "Both": 5})

    @nsh.computed
    def rows():
        ranked = sorted(votes().items(), key=lambda kv: -kv[1])
        return [{"language": k, "votes": n} for k, n in ranked]

    def vote(choice):
        return lambda: votes.update(lambda v: {**v, choice: v[choice] + 1})

    buttons = [nsh.button(k, on_press=vote(k)) for k in votes.value]
    return nsh.card(
        nsh.table(rows),
        nsh.view(*buttons, class_="flex-row gap-2"),
        title="Favourite language",
        description=lambda: f"{sum(votes().values())} votes so far",
        class_="m-6",
    )


if __name__ == "__main__":
    nsh.run(Poll, title="Poll")
