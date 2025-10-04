import customtkinter
from Managers.AccountsManager import AccountManager

class AccountsListFrame(customtkinter.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.accountsManager = AccountManager()

        # Фрейм для метки (фиксированный, не скроллится)
        self.top_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.top_frame.grid_columnconfigure(0, weight=1)

        self.label_text = customtkinter.CTkLabel(
            self.top_frame,
            text=self._get_label_text(),
            font=customtkinter.CTkFont(size=14),
            fg_color="#3c3f41",
            corner_radius=8,
            height=30
        )
        self.label_text.grid(row=0, column=0, sticky="ew")

        # Scrollable content для переключателей
        self.scrollable_content = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.scrollable_content.grid_columnconfigure(0, weight=1)

        self.switches = []
        for i, account in enumerate(self.accountsManager.accounts):
            sw = customtkinter.CTkSwitch(
                self.scrollable_content,
                text=account.login,
                command=lambda acc=account: self._toggle_account(acc),
                text_color=account._color,
            )

            account.setColorCallback(lambda color, s=sw, obj=self: (s.configure(text_color=color), obj.update_label()))
            sw.grid(row=i, column=0, pady=2)
            self.switches.append(sw)

    def _toggle_account(self, account):
        if account in self.accountsManager.selected_accounts:
            self.accountsManager.selected_accounts.remove(account)
        else:
            self.accountsManager.selected_accounts.append(account)
        self.update_label()

    def update_label(self):
        self.label_text.configure(text=self._get_label_text())
        for sw, account in zip(self.switches, self.accountsManager.accounts):
            if account in self.accountsManager.selected_accounts:
                sw.select()
            else:
                sw.deselect()

    def _get_label_text(self):
        return f"Accs: {len(self.accountsManager.accounts)} | Selected: {len(self.accountsManager.selected_accounts)} | Launched: {self.accountsManager.count_launched_accounts()}"
