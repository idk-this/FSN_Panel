import shutil

import customtkinter

from Managers.SettingsManager import SettingsManager



class ConfigTab(customtkinter.CTkTabview):
    def __init__(self, parent):
        super().__init__(parent, width=250)
        self._settingsManager = SettingsManager()

        self.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.add("Config")
        self.tab("Config").grid_columnconfigure(0, weight=1)

        # --- Buttons for path selection ---
        b1 = customtkinter.CTkButton(
            self.tab("Config"),
            text="Select Steam path",
            command=lambda: self.set_path("SteamPath", "Steam", "C:/Program Files (x86)/Steam/steam.exe")
        )
        b2 = customtkinter.CTkButton(
            self.tab("Config"),
            text="Select CS2 path",
            command=lambda: self.set_path("CS2Path", "CS2", "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive")
        )
        b1.grid(row=0, column=0, padx=20, pady=10)
        b2.grid(row=1, column=0, padx=20, pady=10)

        # --- Switches ---
        self.bg_switch = customtkinter.CTkSwitch(
            self.tab("Config"),
            text="Remove background",
            command=lambda: self._settingsManager.set("RemoveBackground", self.bg_switch.get())
        )
        self.bg_switch.grid(row=2, column=0, padx=10, pady=5)

        self.overlay_switch = customtkinter.CTkSwitch(
            self.tab("Config"),
            text="Disable Steam Overlay",
            command=lambda: self._settingsManager.set("DisableOverlay", self.overlay_switch.get())
        )
        self.overlay_switch.grid(row=3, column=0, padx=10, pady=5)

        # --- Load saved values ---
        self.load_settings()

    def set_path(self, key, name, placeholder):
        """Opens a path input window and saves result in settingsManager"""
        value = self.open_path_window(name, placeholder)
        if value:  # save only if user entered something
            self._settingsManager.set(key, value)

    def open_path_window(self, name, placeholder):
        """Opens a separate window for entering a path and returns the result"""

        result = {"value": None}

        win = customtkinter.CTkToplevel(self)
        win.title(f"Select {name} path")
        win.geometry("500x150")
        win.grab_set()

        label = customtkinter.CTkLabel(win, text=f"Enter {name} path:")
        label.pack(pady=(20, 5))

        entry = customtkinter.CTkEntry(win, placeholder_text=f"Example: {placeholder}", width=400)
        entry.pack(pady=5)

        def save_and_close():
            result["value"] = entry.get()
            win.destroy()

        btn = customtkinter.CTkButton(win, text="OK", command=save_and_close)
        btn.pack(pady=10)

        win.wait_window()
        return result["value"]

    def load_settings(self):
        """Load saved values from settingsManager and apply them"""

        # Switches
        bg_value = self._settingsManager.get("RemoveBackground", False)
        if bg_value is not None:
            self.bg_switch.select() if bg_value else self.bg_switch.deselect()

        overlay_value = self._settingsManager.get("DisableOverlay", False)
        if overlay_value is not None:
            self.overlay_switch.select() if overlay_value else self.overlay_switch.deselect()

        # Paths (just print for now, you can show them somewhere in UI if needed)
        steam_path = self._settingsManager.get("SteamPath", "C:/Program Files (x86)/Steam/steam.exe")
        if steam_path:
            print(f"Loaded SteamPath: {steam_path}")

        cs2_path = self._settingsManager.get("CS2Path", "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive")
        if cs2_path:
            print(f"Loaded CS2Path: {cs2_path}")
