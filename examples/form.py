"""A sign-up form: text inputs, a signal per field, and Enter to submit."""

import nsh


def Form():
    name = nsh.signal("")
    email = nsh.signal("")
    sent = nsh.signal("Nothing sent yet")

    @nsh.computed
    def valid():
        return bool(name().strip()) and "@" in email()

    def send():
        if valid():
            sent.set(f"Welcome, {name().strip()}! We'll write to {email().strip()}.")
            name.set("")
            email.set("")

    return nsh.view(
        nsh.text("Sign up", class_="text-xl font-semibold"),
        nsh.input(
            name,
            placeholder="Your name",
            class_="border rounded-md px-3 py-2",
            test_id="name",
        ),
        nsh.input(
            email,
            placeholder="Email",
            on_submit=lambda _: send(),  # Enter in the field
            class_="border rounded-md px-3 py-2",
            test_id="email",
        ),
        nsh.text(lambda: f"Hello, {name() or 'stranger'}", class_="text-sm"),
        nsh.button("Send", on_press=send, test_id="send"),
        nsh.text(sent, class_="text-sm text-muted-foreground", test_id="status"),
        class_="p-4 gap-3",
    )


if __name__ == "__main__":
    nsh.run(Form, title="Form")
