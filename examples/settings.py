""" A mock settings page, showcasing a small selection of inputs and styles"""
import nsh

FIELD = "border border-border rounded-md px-3 py-2 text-foreground"
# FIELD = ""

class SettingsPage(nsh.Component):
    BUTTON_ENABLE = "Enable dangerous setting"
    BUTTON_DISABLE = "Disable dangerous setting"

    email = nsh.signal("")
    username = nsh.signal("")
    is_checkbox_disabled = nsh.signal(True)
    checkbox_enable_button_text = nsh.Signal("")
    difficulty = nsh.signal("Easy")
    options = nsh.signal(["Easy", "Normal", "Hard"])

    def setup(self):
        self.update_button()

    def toggle_disable(self):
        self.is_checkbox_disabled.set(not self.is_checkbox_disabled.peek())
        self.update_button()

    def update_button(self):
        if self.is_checkbox_disabled.peek() == True:
            self.checkbox_enable_button_text.set(self.BUTTON_ENABLE)
        else:
            self.checkbox_enable_button_text.set(self.BUTTON_DISABLE)

    def view(self):
        profile_section = nsh.card(
            nsh.text("Account details: ", class_="text-sm font-semibold"),
            nsh.input(
                self.email, 
                placeholder="Email", 
                class_=FIELD, 
                test_id="email",
            ),
            nsh.input(
                self.username, 
                placeholder="Username", 
                class_= FIELD, 
                test_id="username",
            ),
            class_="mb-3",
        )
        toggle_section = nsh.card(
            nsh.text("Random toggles: ", class_="text-sm font-semibold"),
            nsh.switch("Setting 1", test_id="toggle1"),
            nsh.switch("Setting 2", test_id="toggle2"),
            nsh.switch("Setting 3", test_id="toggle3"),
            class_="mb-3",
        )
        checkboxes_section = nsh.card(
            nsh.text("Optional settings: ", class_="text-sm font-semibold"),
            nsh.checkbox(
                "Optional Setting 1 (default unchecked)", 
                test_id="checkbox1"
            ),
            nsh.checkbox(
                "Optional Setting 2 (default checked)", 
                checked=True, 
                test_id="checkbox2"
            ),
            nsh.checkbox(
                "Dangerous Setting (enable below)", 
                disabled=self.is_checkbox_disabled,
                test_id="checkbox3"
            ),
            class_="mb-3",
        )

        difficulty_section = nsh.card(
            nsh.text("Select a difficulty: ", class_="text-sm font-semibold"),
            nsh.select(
                self.difficulty, 
                options=self.options,
                placeholder="Select a difficulty"
            ),
            class_="mb-3",
        )

        danger_zone = nsh.card(
            nsh.text(
                "Don't touch unless you know what you're doing!", 
                class_="text-sm"
            ),
            nsh.button(
                "Delete Account (dangerous!)", 
                class_="bg-red-500", 
                test_id="deletebutton"
            ),
            nsh.button(
                self.checkbox_enable_button_text,
                class_="bg-red-500", 
                on_press=self.toggle_disable,
                test_id="togglebutton"
            ),
            class_="mb-3",
        )
        save_button_cluster = nsh.card(
            nsh.button("Save", test_id="savebutton"),
            nsh.button(
                "Exit without saving", 
                on_press=nsh.quit, 
                test_id="quitbutton"
            ),
            class_="mb-3",
        )

        return nsh.scroll(
            *[
                profile_section, 
                toggle_section, 
                checkboxes_section, 
                difficulty_section, 
                danger_zone, 
                save_button_cluster,
            ],
            class_="flex-1 p-6"
        )


def app():
    return nsh.view(SettingsPage(), class_="flex-1")

if __name__ == "__main__":
    nsh.run(app, title="Settings")
