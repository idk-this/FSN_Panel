import sys

import customtkinter

import customtkinter
import subprocess
import os
import psutil
import ctypes

import pygetwindow
import pygetwindow as gw
import win32gui
import win32process

from Managers.AccountsManager import AccountManager
from Managers.LobbyManager import LobbyManager
from Managers.LogManager import LogManager



class ControlFrame(customtkinter.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, width=250)
        self.logManager = LogManager()

        self.grid(row=1, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")

        # список кнопок: (текст, цвет, функция)
        data = [
            ("Move all CS windows", None, self.move_all_cs_windows),
            ("Kill ALL CS & Steam processes", "red", self.kill_all_cs_and_steam),
            ("Launch BES", "darkgreen", self.launch_bes),
            ("Launch SRT", "darkgreen", self.launch_srt),
            ("Support Developer", "darkgreen", self.sendCasesMe)
        ]

        for text, color, func in data:
            b = customtkinter.CTkButton(self, text=text, fg_color=color, command=func)
            b.pack(pady=10)

    # ---------- функции кнопок ----------
    def move_all_cs_windows(self):
        print("Перемещаю все окна CS...")
        lobbyManager = LobbyManager()

        if lobbyManager.isValid():
            lobbyManager.MoveWindows()
            return
        # --- 1. DPI-aware и размеры экрана ---
        ctypes.windll.user32.SetProcessDPIAware()
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        # --- 2. Находим окна по PID ---
        hwnd_list = []

        def enum_windows_callback(hwnd, _):
            # Проверяем, что окно видимо и включено
            if not win32gui.IsWindowVisible(hwnd) or not win32gui.IsWindowEnabled(hwnd):
                return True

            # Проверяем, что у окна нет родителя (значит, это верхнеуровневое окно)
            if win32gui.GetParent(hwnd) != 0:
                return True

            # Проверяем, что у окна есть заголовок
            title = win32gui.GetWindowText(hwnd)
            if not title.strip():
                return True

            # Получаем PID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            accountManager = AccountManager()
            for acc in accountManager.accounts:
                if not acc.isCSValid():
                    continue
                if acc.CS2Process and acc.CS2Process.pid == pid:
                    hwnd_list.append(hwnd)
                    break

            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if not hwnd_list:
            print("Не найдено ни одного окна CS2")
            return

        # --- 3. Расставляем окна друг за другом ---
        x = 0
        y = 0
        max_row_height = 0

        for hwnd in hwnd_list:
            rect = win32gui.GetWindowRect(hwnd)
            win_width = rect[2] - rect[0]
            win_height = rect[3] - rect[1]

            # Если не помещается по ширине — перенос на новую строку
            if x + win_width > screen_width:
                x = 0
                y += max_row_height
                max_row_height = 0

            # Переместить окно в нужное место
            win32gui.MoveWindow(hwnd, x, y, win_width, win_height, True)

            x += win_width
            max_row_height = max(max_row_height, win_height)

    def sendCasesMe(self):
        os.system(f"start https://steamcommunity.com/tradeoffer/new/?partner=998469634&token=VjICDrcw")

    def kill_all_cs_and_steam(self):
        print("Завершаю все процессы CS и Steam...")
        accountManager = AccountManager()
        for acc in accountManager.accounts:
            acc.KillSteamAndCS()
        while not accountManager.accounts_start_queue.empty():
            accountManager.accounts_start_queue.get()

        for proc in psutil.process_iter(['name']):
            name = proc.info['name']
            if name and ('cs2' in name.lower() or 'steam' in name.lower()):
                try:
                    proc.kill()
                    print(f"Убит процесс: {name}")
                except Exception as e:
                    print(f"Ошибка при завершении {name}: {e}")

    def launch_bes(self):
        if getattr(sys, 'frozen', False):
            # Если программа собрана в .exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Если запущено через python main.py
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        bes_path = os.path.join(base_path, "BES", "BES.exe")
        if os.path.exists(bes_path):
            subprocess.Popen(bes_path)
        else:
            self.logManager.add_log("BES/BES.exe not found!")
    def launch_srt(self):
        if getattr(sys, 'frozen', False):
            # Если программа собрана в .exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Если запущено через python main.py
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        srt_path = os.path.join(base_path, "SteamRouteTool", "SteamRouteTool.exe")
        if os.path.exists(srt_path):
            subprocess.Popen(srt_path)
        else:
            self.logManager.add_log("SteamRouteTool/SteamRouteTool.exe not found!")
