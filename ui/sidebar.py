import customtkinter

class Sidebar(customtkinter.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, width=140, corner_radius=0)
        self.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(self, text="FSN Panel", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.version_label = customtkinter.CTkLabel(self, text="Free manual farm", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.version_label.grid(row=1, column=0, padx=20, pady=(20, 10))

        self.appearance_mode_label = customtkinter.CTkLabel(self, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self, values=["Light","Dark","System"], command=self.change_appearance_mode)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        self.scaling_label = customtkinter.CTkLabel(self, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))

        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self, values=["80%","90%","100%","110%","120%"], command=self.change_scaling)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

    def set_defaults(self):
        self.appearance_mode_optionemenu.set("Dark")
        self.scaling_optionemenu.set("100%")

    def change_appearance_mode(self, mode):
        customtkinter.set_appearance_mode(mode)

    def change_scaling(self, value):
        customtkinter.set_widget_scaling(int(value.replace("%",""))/100)
