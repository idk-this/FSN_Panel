import customtkinter

from Managers.AccountsManager import AccountManager
from Managers.LobbyManager import LobbyManager
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager
from Modules.AutoAcceptModule import AutoAcceptModule


class MainMenu(customtkinter.CTkTabview):
    def __init__(self, parent):
        super().__init__(parent, width=250)
        self.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create main tab
        self._create_main_tab()

        self._logManager = LogManager()
        self._accountManager = AccountManager()
        self._lobbyManager = LobbyManager()
        self._settingsManager = SettingsManager()
        self.auto_accept_module = AutoAcceptModule()
        # create buttons
        self._create_buttons([
            ("Make lobbies", "darkgreen", self.make_lobbies),
            ("Disband lobbies", "darkblue", self.disband_lobbies),
            ("Shuffle lobbies", "darkblue", self.shuffle_lobbies),
        ])

        # create toggle for Auto Accept Game
        self._create_toggle("Auto Accept Game", self.toggle_auto_accept)

    def _create_main_tab(self):
        """Create 'Main Menu' tab."""
        self.add("Main Menu")
        self.tab("Main Menu").grid_columnconfigure(0, weight=1)

    def _create_buttons(self, buttons_data):
        """Create buttons and store references by text"""
        self.buttons = {}
        for i, (text, color, command) in enumerate(buttons_data):
            button = customtkinter.CTkButton(
                self.tab("Main Menu"),
                text=text,
                fg_color=color,
                command=command
            )
            button.grid(row=i, column=0, padx=20, pady=10, sticky="ew")
            self.buttons[text] = button

    def _create_toggle(self, text, command, default_value=False):
        """Create a toggle switch in the main tab with default value"""
        self.toggles = getattr(self, "toggles", {})
        toggle = customtkinter.CTkSwitch(
            self.tab("Main Menu"),
            text=text,
            command=command
        )
        toggle.grid(row=len(self.buttons) + len(self.toggles), column=0, padx=20, pady=10)
        if default_value:
            toggle.select()
        else:
            toggle.deselect()
        self.toggles[text] = toggle

    # -----------------------------
    # Toggle actions
    # -----------------------------
    def toggle_auto_accept(self):
        self.auto_accept_module.toggle()
        print(f"Auto Accept Game is now {'ON' if self.auto_accept_module._running else 'OFF'}")
        self._lobbyManager.auto_accept = self.auto_accept_module._running


    # -----------------------------
    # Universal countdown runner on button
    # -----------------------------
    def run_with_countdown_on_button(self, button_text, action, message="Completed", message_in_run="Running...", countdown=3, message_time=1):
        button = self.buttons.get(button_text)
        if not button:
            return

        original_text = button.cget("text")
        button.configure(state="disabled")
        self._countdown_step(button, action, original_text, countdown, message, message_in_run, message_time)

    def _countdown_step(self, button, action, original_text, seconds, message, message_in_run, message_time):
        if seconds > 0:
            button.configure(text=f"{seconds}...")
            self.after(1000, lambda: self._countdown_step(button, action, original_text, seconds - 1, message, message_in_run, message_time))
        else:
            button.configure(text=message_in_run)
            self.after(100, lambda: self._run_action_on_button(button, action, original_text, message, message_time))

    def _run_action_on_button(self, button, action, original_text, message, message_time):
        action()
        button.configure(text=message)
        self.after(message_time * 1000, lambda: self._reset_button_text(button, original_text))

    def _reset_button_text(self, button, original_text):
        button.configure(text=original_text, state="normal")

    # -----------------------------
    # Button actions
    # -----------------------------
    def make_lobbies(self):
        self.run_with_countdown_on_button(
            button_text="Make lobbies",
            action=self._lobbyManager.CollectLobby,
            message="Completed",
            message_in_run="Collecting lobbies...",
            countdown=3,
            message_time=1
        )

    def disband_lobbies(self):
        self.run_with_countdown_on_button(
            button_text="Disband lobbies",
            action=self._lobbyManager.DisbandLobbies,
            message="Completed",
            message_in_run="Disbanding lobbies...",
            countdown=1,
            message_time=1
        )

    def shuffle_lobbies(self):
        print("Shuffling lobbies...")
        self._lobbyManager.Shuffle()
