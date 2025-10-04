import os

import customtkinter
from Managers.AccountsManager import AccountManager
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager


class AccountsControl(customtkinter.CTkTabview):
    def __init__(self, parent, update_label):
        super().__init__(parent, width=250)

        self._settingsManager = SettingsManager()
        self._logManager = LogManager()
        self.accountsManager = AccountManager()
        self.update_label = update_label

        self.grid(row=1, column=2, padx=(20,0), pady=(20,0), sticky="nsew")
        self.add("Accounts Control")
        self.tab("Accounts Control").grid_columnconfigure(0, weight=1)

        self.create_buttons()

    def create_buttons(self):
        data = [
            ("Start selected accounts","darkgreen", self.start_selected),
            ("Kill selected accounts","red", self.kill_selected),
            ("Select first 10 accounts", None, self.select_first_10),
            ("Select first 4 accounts", None, self.select_first_4)
        ]
        for i,(text,color,cmd) in enumerate(data):
            b = customtkinter.CTkButton(self.tab("Accounts Control"), text=text, fg_color=color, command=cmd)
            b.grid(row=i, column=0, padx=20, pady=10)

    def start_selected(self):
        steam_path = self._settingsManager.get("SteamPath", r"C:\Program Files (x86)\Steam\steam.exe")
        cs2_path = self._settingsManager.get("CS2Path",
                                             r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive")
        cs2_exe_path = os.path.join(cs2_path, r"game\bin\win64\cs2.exe")
        if not os.path.isfile(steam_path) or not steam_path.lower().endswith('.exe'):
            self._logManager.add_log("Steam path incorrect")
            return
        if not os.path.isfile(cs2_exe_path):
            self._logManager.add_log("CS2 path incorrect")
            return
        for a in list(self.accountsManager.selected_accounts):
            self.accountsManager.add_to_start_queue(a)
            print("Starting:", a.login)

        self.accountsManager.selected_accounts.clear()
        self.update_label()

    def kill_selected(self):
        for a in self.accountsManager.selected_accounts:
            a.KillSteamAndCS()

    def select_first_10(self):
        for a in self.accountsManager.accounts[:10]:
            if a not in self.accountsManager.selected_accounts:
                self.accountsManager.selected_accounts.append(a)
        self.update_label()

    def select_first_4(self):
        for a in self.accountsManager.accounts[:4]:
            if a not in self.accountsManager.selected_accounts:
                self.accountsManager.selected_accounts.append(a)
        self.update_label()
