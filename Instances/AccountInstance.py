import ctypes
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import base64
import hashlib, hmac
import winreg
from ctypes import wintypes

import wmi


import pyautogui
import pyperclip
import json
from pathlib import Path
import psutil
import pygetwindow as gw
import win32con
import win32gui
import win32process
from pywinauto import Application, findwindows

from Helpers.MouseController import MouseHelper
from Helpers.WinregHelper import WinregHelper
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager


def bytes_to_int(bytes):
    result = 0
    for b in bytes:
        result = result * 256 + int(b)
    return result

def GetMainWindowByPID(pid: int) -> int:
    """
    Возвращает hwnd главного окна процесса по PID.
    Если окно не найдено, возвращает 0.
    """
    hwnds = []

    def enum_windows_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.IsWindowEnabled(hwnd):
            return True
        if win32gui.GetParent(hwnd) != 0:
            return True
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        if window_pid == pid:
            hwnds.append(hwnd)
            return False  # нашли, можно остановить
        return True

    win32gui.EnumWindows(enum_windows_callback, None)
    return hwnds[0] if hwnds else 0

def update_video_cfg(src_path, dst_path, updates: dict):
    """
    Копирует cfg-файл и обновляет указанные параметры.

    :param src_path: путь к исходному файлу
    :param dst_path: путь для сохранения нового файла
    :param updates: словарь параметров для изменения
    """
    # Создаем директорию назначения, если её нет
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    # Если файл уже есть — можно просто пересоздать
    shutil.copy(src_path, dst_path)

    # Читаем содержимое копии
    with open(dst_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Обновляем параметры
    with open(dst_path, "w", encoding="utf-8") as f:
        for line in lines:
            for key, value in updates.items():
                if f'"{key}"' in line:
                    prefix = line[:line.find('"'+key+'"')]
                    line = f'{prefix}"{key}"\t\t"{value}"\n'
                    break
            f.write(line)

user32 = ctypes.WinDLL('user32', use_last_error=True)

HWND = wintypes.HWND
RECT = wintypes.RECT
LPRECT = ctypes.POINTER(RECT)
BOOL = wintypes.BOOL
UINT = wintypes.UINT

# Функции Win32
SetProcessDPIAware = user32.SetProcessDPIAware
SetProcessDPIAware.restype = BOOL

GetWindowRect = user32.GetWindowRect
GetWindowRect.argtypes = [HWND, LPRECT]
GetWindowRect.restype = BOOL

GetClientRect = user32.GetClientRect
GetClientRect.argtypes = [HWND, LPRECT]
GetClientRect.restype = BOOL

SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, UINT]
SetWindowPos.restype = BOOL

SetWindowText = user32.SetWindowTextW
SetWindowText.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
SetWindowText.restype = wintypes.BOOL
# Константы
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004

def fix_window(hwnd):
    if not hwnd:
        return

    SetProcessDPIAware()

    wr = RECT()
    cr = RECT()

    if not GetWindowRect(hwnd, ctypes.byref(wr)) or not GetClientRect(hwnd, ctypes.byref(cr)):
        return

    current_client_width = cr.right - cr.left
    current_client_height = cr.bottom - cr.top
    current_window_width = wr.right - wr.left
    current_window_height = wr.bottom - wr.top

    # Если размеры client area не совпадают с target
    if current_client_width != current_window_width or current_client_height != current_window_height:
        # Вычисляем рамки окна
        dx = (wr.right - wr.left) - current_client_width
        dy = (wr.bottom - wr.top) - current_client_height

        # Применяем новые размеры окна
        SetWindowPos(hwnd, None, wr.left, wr.top, current_client_width, current_client_height, SWP_NOZORDER | SWP_NOMOVE)

VENDOR_PRIORITY = {
    0x10DE: 3,  # NVIDIA
    0x1002: 2,  # AMD
    0x8086: 1   # Intel
}
# Создаём DXGIFactory
def get_best_gpu():
    c = wmi.WMI()
    gpus = []

    for gpu in c.Win32_VideoController():
        try:
            raw_memory = gpu.AdapterRAM
            if not raw_memory:
                continue

            mem_bytes = int(raw_memory)
            if mem_bytes <= 0:
                try:
                    mem_bytes = get_gpu_memory_alternative(gpu)
                except:
                    continue

            mem_mb = mem_bytes // (1024 * 1024)

        except (ValueError, AttributeError):
            continue

        vendor_id = "0"
        device_id = "0"
        if gpu.PNPDeviceID:
            ven_match = re.search(r'VEN_([0-9A-Fa-f]{4})', gpu.PNPDeviceID)
            dev_match = re.search(r'DEV_([0-9A-Fa-f]{4})', gpu.PNPDeviceID)
            if ven_match:
                vendor_id = int(ven_match.group(1), 16)
            if dev_match:
                device_id = int(dev_match.group(1), 16)

        gpus.append({
            "VendorID": vendor_id,
            "DeviceID": device_id,
            "MemoryMB": mem_mb,
            "Priority": VENDOR_PRIORITY.get(vendor_id, 0)  # Если неизвестный вендор, приоритет 0
        })

    if not gpus:
        return {"VendorID": "0", "DeviceID": "0"}

    # Сортируем сначала по приоритету производителя, потом по памяти
    gpu_best = max(gpus, key=lambda x: (x["Priority"], x["MemoryMB"]))
    return {"VendorID": gpu_best["VendorID"], "DeviceID": gpu_best["DeviceID"]}


def get_gpu_memory_alternative(gpu):
    """Альтернативный метод получения памяти GPU через реестр"""
    import winreg

    try:
        # Получаем ID устройства из PNPDeviceID
        pnp_id = gpu.PNPDeviceID
        if not pnp_id:
            return 0

        # Формируем путь в реестре
        part = pnp_id.split("\\")[1]
        key_path = f"SYSTEM\\CurrentControlSet\\Control\\Class\\{part}"


        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            # Пытаемся прочитать значение памяти
            value, _ = winreg.QueryValueEx(key, "HardwareInformation.qwMemorySize")
            return int(value)
    except:
        return 0
def get_base_path():
    """Определяем базовый путь относительно запуска программы."""
    if getattr(sys, 'frozen', False):
        # Если программа собрана в .exe
        return os.path.dirname(sys.executable)
    else:
        # Если запущено через python main.py
        return os.path.dirname(os.path.abspath(sys.argv[0]))

import os

def find_latest_file(filename: str) -> str | None:
    settings = SettingsManager()
    latest_file_path = None
    latest_mtime = 0

    for root, dirs, files in os.walk(settings.get("AVASTSANDBOX_FOLDER", "C:\\avast! sandbox")):
        if filename in files:
            file_path = os.path.join(root, filename)
            mtime = os.path.getmtime(file_path)
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file_path = file_path

    return latest_file_path

def to_base62(num: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    base = len(alphabet)
    result = []
    while num:
        num, rem = divmod(num, base)
        result.append(alphabet[rem])
    return ''.join(reversed(result)) or '0'

class Account:
    def __init__(self, login, password, shared_secret=None, steam_id = 0):
        self.login = login
        self.password = password
        self.shared_secret = shared_secret
        self.steam_id = steam_id
        self.steamProcess = None
        self.CS2Process = None
        self.last_match_id = None

        self._settingsManager = SettingsManager()
        self._logManager = LogManager()

        self._color = "#DCE4EE"
        self._color_callback = None  # callback на смену цвета
        self._stop_monitoring = False  # флаг для остановки мониторинга
        runtime_path = Path("runtime.json")
        if runtime_path.exists():
            try:
                with open(runtime_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                entry = next((e for e in entries if e.get("login") == self.login), None)
                if entry:
                    steam_pid = entry.get("SteamPid")
                    cs2_pid = entry.get("CS2Pid")
                    if psutil.pid_exists(steam_pid) and psutil.pid_exists(cs2_pid):
                        steam_proc = psutil.Process(steam_pid)
                        cs2_proc = psutil.Process(cs2_pid)
                        if cs2_proc.name().lower() == "cs2.exe" and cs2_proc.ppid() == steam_proc.pid:
                            self.steamProcess = steam_proc
                            self.CS2Process = cs2_proc
                            self.setColor("green")
                            self.MonitorCS2(interval=5)  # запускаем мониторинг CS2
                            self.start_log_watcher(f"{login}.log")
                            csWindow = self.FindCSWindow()
                            fix_window(csWindow)
                            SetWindowText(csWindow, f"[FSN FREE] {self.login}")
            except Exception as e:
                print(f"Ошибка при чтении runtime.json: {e}")

    def start_log_watcher(self, filename: str):
        # Запускаем поток, который будет искать файл и потом его читать
        t = threading.Thread(target=self._watch_log_file, args=(filename,), daemon=True)
        t.start()

    def _watch_log_file(self, filename: str):
        timeout = 5 * 60  # 5 минут
        start_time = time.time()

        while time.time() - start_time < timeout:
            path = find_latest_file(filename)
            if path:
                try:
                    # Пробуем открыть файл, если доступ есть — переходим к чтению
                    with open(path, 'r', encoding='utf-8', errors='ignore'):
                        print("Найден log файл:", path)
                        self.tail_log_file(path)
                        return  # выходим из функции, поток теперь читает файл
                except PermissionError:
                    # Файл найден, но недоступен — продолжаем поиск
                    print(f"Файл найден, но недоступен: {path}, продолжаем поиск...")
            time.sleep(1)

        print("Файл не найден за 5 минут или недоступен.")
    def tail_log_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    self.process_log_line(line)
                else:
                    time.sleep(0.1)


    def process_log_line(self, line: str):
        if "Scratch RT Allocations:" in line:
            fix_window(self.FindCSWindow())
            return
        match = re.search(r"match_id=(\d+)", line)
        if match:
            match_id_str = match.group(1)
            match_id_int = int(match_id_str)
            match_id_compact = to_base62(match_id_int)
            self.last_match_id = match_id_compact
            self._logManager.add_log(f"[{self.login}] Found game: {match_id_compact}")

    def isCSValid(self):
        if self.CS2Process is None or self.steamProcess is None: return False
        if psutil.pid_exists(self.steamProcess.pid) and psutil.pid_exists(self.CS2Process.pid):
            steam_proc = psutil.Process(self.steamProcess.pid)
            cs2_proc = psutil.Process(self.CS2Process.pid)
            if cs2_proc.name().lower() == "cs2.exe" and cs2_proc.ppid() == steam_proc.pid:
                return True
        return False
    def setColorCallback(self, callback):
        """Регистрируем callback, который будет вызываться при смене цвета"""
        self._color_callback = callback

    def setColor(self, color):
        """Меняем цвет и вызываем callback, если он есть"""
        self._color = color
        if self._color_callback:
            self._color_callback(color)

    def getWindowSize(self):
        hwnd = self.FindCSWindow()
        rect = win32gui.GetWindowRect(hwnd)
        win_width = rect[2] - rect[0]
        win_height = rect[3] - rect[1]
        return win_width, win_height

    def MoveWindow(self, x, y):
        ctypes.windll.user32.SetProcessDPIAware()
        hwnd = self.FindCSWindow()
        if hwnd is None: return
        rect = win32gui.GetWindowRect(hwnd)
        win_width = rect[2] - rect[0]
        win_height = rect[3] - rect[1]
        win32gui.MoveWindow(hwnd, x, y, win_width, win_height, True)
        SetWindowText(hwnd, f"[FSN FREE] {self.login}")

    def FindCSWindow(self) -> int:
        if self.CS2Process and self.isCSValid():
            return GetMainWindowByPID(self.CS2Process.pid)
        return 0
    def get_auth_code(self):
        t = int(time.time() / 30)
        t = t.to_bytes(8, 'big')
        key = base64.b64decode(self.shared_secret)
        h = hmac.new(key, t, hashlib.sha1)
        signature = list(h.digest())
        start = signature[19] & 0xf
        fc32 = bytes_to_int(signature[start:start + 4])
        fc32 &= 2147483647
        fullcode = list('23456789BCDFGHJKMNPQRTVWXY')
        code = ''
        for i in range(5):
            code += fullcode[fc32 % 26]
            fc32 //= 26
        return code

    def MoveMouse(self, x: int, y: int):
        """
        Перемещает курсор мыши относительно окна CS2.
        """
        hwnd = self.FindCSWindow()
        if hwnd:
            MouseHelper.MoveMouse(hwnd, x, y)

    def ClickMouse(self, x: int, y: int, button: str = 'left'):
        """
        Кликает мышью относительно окна CS2.
        """
        hwnd = self.FindCSWindow()
        if hwnd:
            MouseHelper.ClickMouse(hwnd, x, y, button)

    def ProcessWindowsBeforeCS(self, steamPid):
        """Обрабатывает все окна Steam и выводит тексты TextBox"""

        parent = psutil.Process(steamPid)
        children = parent.children(recursive=True)  # рекурсивно

        all_pids = [steamPid] + [child.pid for child in children]

        for pid in all_pids:
            try:
                exclude_titles = {"Steam", "Friends List", "Special Offers"}
                windows = [hwnd for hwnd in findwindows.find_windows(process=pid) if
                           win32gui.GetWindowText(hwnd) not in exclude_titles]
                if not windows:
                    continue
                app = Application(backend="uia").connect(process=pid)
                for win in app.windows():
                    win.set_focus()
                    all_descendants = win.descendants()
                    edits = [c for c in all_descendants if c.friendly_class_name() == "Edit"]
                    buttons = [c for c in all_descendants if c.friendly_class_name() == "Button"]
                    statics = [c for c in all_descendants if c.friendly_class_name() == "Static"]
                    if len(edits) == 2 and any(btn.window_text().strip() == "Sign in" for btn in buttons):
                        edits[0].set_text(self.login)
                        edits[1].set_text(self.password)
                        sign_in_button = next((btn for btn in buttons if btn.window_text().strip() == "Sign in"), None)
                        sign_in_button.click()
                        time.sleep(2)
                    if any(txt.window_text().strip() == "Enter a code instead" for txt in statics):
                        target = next((s for s in statics if s.window_text().strip() == "Enter a code instead"), None)
                        target.click_input()
                    if any(btn.window_text().strip() == "Play anyway" for btn in buttons):
                        target = next((btn for btn in buttons if btn.window_text().strip() == "Play anyway"), None)
                        if target:
                            target.click()
                    if any(btn.window_text().strip().lower() == "no thanks".lower() for btn in buttons):
                        target = next(
                            (btn for btn in buttons if btn.window_text().strip().lower() == "no thanks".lower()), None)
                        if target:
                            target.click()
                    if any(txt.window_text().strip() == "Enter the code from your Steam Mobile App" for txt in statics) \
                            and self.shared_secret is not None:
                        win.set_focus()
                        pyperclip.copy(self.get_auth_code())
                        time.sleep(0.1)
                        MouseHelper.PasteText()

            except Exception as e:
                print(f"Не удалось подключиться к PID {pid}: {e}")

    def StartGame(self):
        print("Запуск Steam...")
        steam_path = self._settingsManager.get("SteamPath", r"C:\Program Files (x86)\Steam\steam.exe")
        cs2_path =self._settingsManager.get("CS2Path", "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive")
        if self._settingsManager.get("RemoveBackground", False):
            maps_path = Path(cs2_path) / "game" / "csgo" / "maps"
            if maps_path.exists() and maps_path.is_dir():
                for file in maps_path.iterdir():
                    if file.is_file() and file.name.endswith("_vanity.vpk"):
                        print(f"Delete file: {file}")
                        file.unlink()
            panorama_path = Path(cs2_path) / "game" / "csgo" / "panorama" / "videos"
            if panorama_path.exists() and panorama_path.is_dir():
                print(f"Delete folder: {panorama_path}")
                shutil.rmtree(panorama_path)
        shutil.copy2(
            os.path.join(get_base_path() + "/settings", "fsn.cfg"),
            os.path.join(Path(cs2_path) / "game" / "csgo" / "cfg", "fsn.cfg")
        )
        if self.steam_id != 0:
            userdata_path = os.path.join(os.path.dirname(steam_path), "userdata",
                                         str(self.steam_id - 76561197960265728))
            cfg_path = os.path.join(userdata_path, "730", "local", "cfg")
            os.makedirs(cfg_path, exist_ok=True)
            settings_path = get_base_path() + "/settings"
            if os.path.exists(os.path.join(settings_path, "cs2_video.txt")) and os.path.exists(
                    os.path.join(settings_path, "cs2_machine_convars.vcfg")):
                dst = os.path.join(cfg_path, "cs2_video.txt")
                src = os.path.join(settings_path, "cs2_video.txt")

                vendorID = self._settingsManager.get("VendorID", 0)
                deviceID = self._settingsManager.get("DeviceID", 0)

                # Если чего-то нет или 0, выбираем автоматически
                if vendorID == 0 or deviceID == 0:
                    best_gpu = get_best_gpu()  # Используем твою функцию выбора GPU
                    vendorID = best_gpu["VendorID"]
                    deviceID = best_gpu["DeviceID"]
                    self._settingsManager.set("VendorID", vendorID)
                    self._settingsManager.set("DeviceID", deviceID)
                    self._logManager.add_log(f"Detected VendorID: {vendorID}, DeviceID: {deviceID}")

                updates = {
                    "VendorID": str(vendorID),
                    "DeviceID": str(deviceID),
                }
                update_video_cfg(src, dst, updates)
                shutil.copy2(
                    os.path.join(settings_path, "cs2_machine_convars.vcfg"),
                    os.path.join(cfg_path, "cs2_machine_convars.vcfg")
                )

        try:
            WinregHelper.set_value(r"Software\Valve\Steam", "AutoLoginUser", self.login, winreg.REG_SZ)
            args = (f'{self._settingsManager.get("SteamArg", r"-nofriendsui -vgui -noreactlogin -noverifyfiles -nobootstrapupdate -skipinitialbootstrap -norepairfiles -overridepackageurl -disable-winh264")}' +
                    f' -applaunch 730 ' +
                    f'-con_logfile {self.login}.log ' +
                    f'{self._settingsManager.get("CS2Arg", r"-condebug -conclearlog +exec fsn.cfg -language english -windowed -allowmultiple -noborder -swapcores -noqueuedload -vrdisable -windowed -w 383 -h 280 -nopreload -limitvsconst -softparticlesdefaultoff -nohltv -noaafonts -nosound -novid +violence_hblood 0 +sethdmodels 0 +mat_disable_fancy_blending 1 +r_dynamic 0 +engine_no_focus_sleep 120 -nojoy")}')
            final = [steam_path] + shlex.split(args)
            self.steamProcess = subprocess.Popen(final)
        except Exception as e:
            print(f"Ошибка запуска Steam: {e}")
            return

        while True:
            # Обработка окон Steam
            self.ProcessWindowsBeforeCS(self.steamProcess.pid)
            # Проверка CS2.exe
            cs2_found = False
            for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                if proc.info['name'].lower() == 'cs2.exe':
                    try:
                        parent = psutil.Process(proc.info['ppid'])
                        if parent.pid == self.steamProcess.pid:
                            self.CS2Process = proc
                            cs2_found = True
                            break
                    except psutil.NoSuchProcess:
                        continue

            if cs2_found:
                break
        self.ProcessWindowsAfterCS(self.steamProcess.pid)
        time.sleep(5)
        runtime_path = Path("runtime.json")
        try:
            data = []
            if runtime_path.exists():
                with open(runtime_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            # удалим старые записи с этим логином, если есть
            data = [d for d in data if d.get("login") != self.login]
            data.append({
                "login": self.login,
                "SteamPid": self.steamProcess.pid,
                "CS2Pid": self.CS2Process.pid if self.CS2Process else None
            })
            with open(runtime_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.start_log_watcher(f"{self.login}.log")
        except Exception as e:
            print(f"Ошибка записи runtime.json: {e}")

    def MonitorCS2(self, interval: float = 2.0, retry_delay: float = 10.0):
        """
        Отслеживает процесс CS2. Если он пропадает, перепроверяет через retry_delay секунд.
        Если после повторной проверки процесс всё ещё отсутствует, завершает Steam и меняет цвет на стандартный.
        Запускается в отдельном потоке.
        """
        self._stop_monitoring = False

        def monitor():
            while not self._stop_monitoring:
                # Если CS2Process не задан, просто ждём следующий интервал
                if not getattr(self, 'CS2Process', None):
                    time.sleep(interval)
                    continue

                # Если процесс существует, просто ждём следующий интервал
                if psutil.pid_exists(self.CS2Process.pid):
                    time.sleep(interval)
                    continue

                # Процесс пропал — перепроверяем через retry_delay секунд
                print(f"CS2.exe не найден, перепроверяем через {retry_delay} секунд...")
                time.sleep(retry_delay)

                # Вторая проверка
                if not psutil.pid_exists(self.CS2Process.pid):
                    print("CS2.exe действительно пропал, убиваем Steam...")
                    self.KillSteamAndCS()
                    self.setColor("#DCE4EE")
                    break

                # Ждём интервал перед следующей проверкой
                time.sleep(interval)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    def KillSteamAndCS(self):
        """
        Ручное завершение процессов Steam и CS2.
        """
        try:
            if self.CS2Process and psutil.pid_exists(self.CS2Process.pid):
                print(f"Убиваем CS2.exe (PID {self.CS2Process.pid})")
                self.CS2Process.kill()
                self.CS2Process = None
        except Exception as e:
            print(f"Ошибка при убийстве CS2.exe: {e}")

        try:
            if self.steamProcess and psutil.pid_exists(self.steamProcess.pid):
                print(f"Убиваем Steam.exe (PID {self.steamProcess.pid})")
                self.steamProcess.kill()
                self.steamProcess = None
        except Exception as e:
            print(f"Ошибка при убийстве Steam.exe: {e}")

        self.setColor("#DCE4EE")
        self._stop_monitoring = True
    def ProcessWindowsAfterCS(self, steamPid):
        parent = psutil.Process(steamPid)
        children = parent.children(recursive=True)

        all_pids = [steamPid] + [child.pid for child in children]

        for pid in all_pids:
            try:
                windows = findwindows.find_windows(process=pid)
                for hwnd in windows:
                    if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception as e:
                print(f"Ошибка при обработке PID {pid}: {e}")