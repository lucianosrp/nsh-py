"""A sign-up form with labelled inputs, live validation, and Enter to submit."""

import nsh

FIELD = "border border-border rounded-md px-3 py-2 text-foreground"


def Form():
    name = nsh.signal("")
    email = nsh.signal("")
    password = nsh.signal("")
    sent = nsh.signal("Nothing sent yet")

    @nsh.computed
    def valid():
        return bool(name().strip()) and "@" in email() and bool(password())

    def email_error():
        address = email()
        if address and "@" not in address:
            return "Include an @ sign in your email address."
        return None

    def send():
        if valid():
            sent.set(f"Welcome, {name().strip()}! We'll write to {email().strip()}.")
            name.set("")
            email.set("")
            password.set("")

    return nsh.view(
        nsh.text("Sign up", class_="text-xl font-semibold text-foreground"),
        nsh.field(
            "Name",
            nsh.input(name, class_=FIELD, test_id="name"),
        ),
        nsh.field(
            "Email",
            nsh.input(
                email,
                placeholder="you@example.com",
                on_submit=lambda _: send(),  # Enter in the field
                class_=FIELD,
                test_id="email",
            ),
            help="Use an address you check regularly.",
            error=email_error,
        ),
        nsh.field(
            "Password",
            nsh.input(password, masked=True, class_=FIELD, test_id="password"),
        ),
        nsh.text(lambda: f"Hello, {name() or 'stranger'}", class_="text-sm text-foreground"),
        nsh.button("Send", on_press=send, test_id="send"),
        nsh.text(sent, class_="text-sm text-muted-foreground", test_id="status"),
        class_="p-4 gap-3",
    )


if __name__ == "__main__":
    nsh.run(Form, title="Form")
