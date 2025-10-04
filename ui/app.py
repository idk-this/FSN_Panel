import base64
import io
import os
import sys
from pathlib import Path

import customtkinter
from PIL import ImageTk, Image
import tkinter as tk

from Managers.AccountsManager import AccountManager
from Managers.LogManager import LogManager
from .sidebar import Sidebar
from .main_menu import MainMenu
from .config_tab import ConfigTab
from .accounts_list_frame import AccountsListFrame
from .accounts_tab import AccountsControl
from .control_frame import ControlFrame

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("FSN not Autofarm panel | v.0.1.0")
        self.geometry("1100x580")
        if hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent
        icon_path = Path(base_path) / "Icon1.ico"
        self.iconbitmap(icon_path)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        self.sidebar = Sidebar(self)
        self.textbox = customtkinter.CTkTextbox(self, width=50)
        self.textbox.grid(row=0, column=1, padx=(20,0), pady=(20,0), sticky="nsew")

        self.log_manager = LogManager(self.textbox)

        self.main_menu = MainMenu(self)
        self.config_tab = ConfigTab(self)
        self.accounts_list = AccountsListFrame(self)
        self.accounts_list.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.accounts_control = AccountsControl(self, self.accounts_list.update_label)
        self.control_frame = ControlFrame(self)

        self.sidebar.set_defaults()
