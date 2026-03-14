import ctypes
import re
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time
import base64
import hashlib, hmac
import winreg
import pyperclip
import json
from pathlib import Path
import psutil
import win32con
import win32gui
import win32process
from pywinauto import Application, findwindows

from Helpers.ConfigHelper import ConfigHelper
from Helpers.MouseController import MouseHelper
from Helpers.WinregHelper import WinregHelper
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager
from Utils.HardwareUtils import HardwareUtils
from Utils.SystemUtils import SystemUtils


def bytes_to_int(bytes):
    result = 0
    for b in bytes:
        result = result * 256 + int(b)
    return result


def make_writable(path):
    if os.path.exists(path):
        os.chmod(path, stat.S_IWRITE)


def get_gpu_memory_alternative(gpu):
    """Альтернативный метод получения памяти GPU через реестр"""
    import winreg
    try:
        pnp_id = gpu.PNPDeviceID
        if not pnp_id:
            return 0
        part = pnp_id.split("\\")[1]
        key_path = f"SYSTEM\\CurrentControlSet\\Control\\Class\\{part}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "HardwareInformation.qwMemorySize")
            return int(value)
    except Exception:
        return 0


def get_base_path():
    """Определяем базовый путь относительно запуска программы."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(sys.argv[0]))


import os


def find_latest_file(filename: str) -> str | None:
    settings = SettingsManager()
    latest_file_path = None
    latest_mtime = 0
    try:
        for root, dirs, files in os.walk(settings.get("AVASTSANDBOX_FOLDER", "C:\\avast! sandbox")):
            if filename in files:
                file_path = os.path.join(root, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_file_path = file_path
                except OSError:
                    continue
    except Exception:
        pass
    return latest_file_path


def to_base62(num: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    base = len(alphabet)
    result = []
    while num:
        num, rem = divmod(num, base)
        result.append(alphabet[rem])
    return ''.join(reversed(result)) or '0'


def _force_remove_readonly(func, path, exc_info):
    """Обработчик ошибок для shutil.rmtree — снимает read-only и повторяет."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class Account:
    def __init__(self, login, password, shared_secret=None, steam_id=0):
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
        self._color_callback = None
        self._stop_monitoring = False

        runtime_path = Path("runtime.json")
        if runtime_path.exists():
            try:
                with open(runtime_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                entry = next((e for e in entries if e.get("login") == self.login), None)
                if entry:
                    steam_pid = entry.get("SteamPid")
                    cs2_pid = entry.get("CS2Pid")
                    if steam_pid and cs2_pid and psutil.pid_exists(steam_pid) and psutil.pid_exists(cs2_pid):
                        try:
                            steam_proc = psutil.Process(steam_pid)
                            cs2_proc = psutil.Process(cs2_pid)
                            if cs2_proc.name().lower() == "cs2.exe" and cs2_proc.ppid() == steam_proc.pid:
                                self.steamProcess = steam_proc
                                self.CS2Process = cs2_proc
                                self.setColor("green")
                                self.MonitorCS2(interval=5)
                                self.start_log_watcher(f"{login}.log")
                                csWindow = self.FindCSWindow()
                                if csWindow:
                                    SystemUtils.fix_window_dpi(csWindow)
                                    SystemUtils.SetWindowText(csWindow, f"[FSN FREE] {self.login}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                            print(f"[{self.login}] Не удалось восстановить процессы: {e}")
            except Exception as e:
                print(f"Ошибка при чтении runtime.json: {e}")

    # -------------------------------------------------------------------------
    # Log watching
    # -------------------------------------------------------------------------
    def start_log_watcher(self, filename: str):
        t = threading.Thread(target=self._watch_log_file, args=(filename,), daemon=True)
        t.start()

    def _watch_log_file(self, filename: str):
        timeout = 5 * 60
        start_time = time.time()
        while time.time() - start_time < timeout:
            path = find_latest_file(filename)
            if path:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore'):
                        print("Найден log файл:", path)
                        self.tail_log_file(path)
                        return
                except PermissionError:
                    print(f"Файл найден, но недоступен: {path}, продолжаем поиск...")
            time.sleep(1)
        print(f"[{self.login}] Лог файл не найден за 5 минут.")

    def tail_log_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                while not self._stop_monitoring:
                    line = f.readline()
                    if line:
                        self.process_log_line(line)
                    else:
                        time.sleep(0.1)
        except Exception as e:
            print(f"[{self.login}] Ошибка чтения лога: {e}")

    def process_log_line(self, line: str):
        if "Scratch RT Allocations:" in line:
            try:
                csWindow = self.FindCSWindow()
                if csWindow:
                    SystemUtils.fix_window_dpi(csWindow)
            except Exception:
                pass
            return
        match = re.search(r"match_id=(\d+)", line)
        if match:
            match_id_str = match.group(1)
            match_id_int = int(match_id_str)
            match_id_compact = to_base62(match_id_int)
            self.last_match_id = match_id_compact
            self._logManager.add_log(f"[{self.login}] Found game: {match_id_compact}")

    # -------------------------------------------------------------------------
    # Validity / color
    # -------------------------------------------------------------------------
    def isCSValid(self) -> bool:
        if self.CS2Process is None or self.steamProcess is None:
            return False
        try:
            steam_pid = self.steamProcess.pid
            cs2_pid = self.CS2Process.pid
            if not psutil.pid_exists(steam_pid) or not psutil.pid_exists(cs2_pid):
                return False
            cs2_proc = psutil.Process(cs2_pid)
            steam_proc = psutil.Process(steam_pid)
            if cs2_proc.name().lower() == "cs2.exe" and cs2_proc.ppid() == steam_proc.pid:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False

    def setColorCallback(self, callback):
        self._color_callback = callback

    def setColor(self, color):
        self._color = color
        if self._color_callback:
            try:
                self._color_callback(color)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Window helpers
    # -------------------------------------------------------------------------
    def getWindowSize(self):
        hwnd = self.FindCSWindow()
        if not hwnd:
            return 0, 0
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return rect[2] - rect[0], rect[3] - rect[1]
        except Exception:
            return 0, 0

    def MoveWindow(self, x, y):
        ctypes.windll.user32.SetProcessDPIAware()
        hwnd = self.FindCSWindow()
        if not hwnd:
            return
        try:
            rect = win32gui.GetWindowRect(hwnd)
            win_width = rect[2] - rect[0]
            win_height = rect[3] - rect[1]
            win32gui.MoveWindow(hwnd, x, y, win_width, win_height, True)
            SystemUtils.SetWindowText(hwnd, f"[FSN FREE] {self.login}")
        except Exception as e:
            print(f"[{self.login}] Ошибка перемещения окна: {e}")

    def FindCSWindow(self) -> int:
        if self.CS2Process and self.isCSValid():
            try:
                return SystemUtils.get_hwnd_by_pid(self.CS2Process.pid)
            except Exception:
                pass
        return 0

    # -------------------------------------------------------------------------
    # Auth
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Mouse
    # -------------------------------------------------------------------------
    def MoveMouse(self, x: int, y: int):
        hwnd = self.FindCSWindow()
        if hwnd:
            MouseHelper.MoveMouse(hwnd, x, y)

    def ClickMouse(self, x: int, y: int, button: str = 'left'):
        hwnd = self.FindCSWindow()
        if hwnd:
            MouseHelper.ClickMouse(hwnd, x, y, button)

    # -------------------------------------------------------------------------
    # Window processing (before/after CS launch)
    # -------------------------------------------------------------------------
    def ProcessWindowsBeforeCS(self, steamPid):
        """Обрабатывает все окна Steam и выводит тексты TextBox"""
        try:
            parent = psutil.Process(steamPid)
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"[{self.login}] ProcessWindowsBeforeCS: не удалось получить процесс {steamPid}: {e}")
            return
        try:
            windows = findwindows.find_windows(process=steamPid)
            for hwnd in windows:
                title = win32gui.GetWindowText(hwnd)
                if title and 'Steam Service Error' in title:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass
        all_pids = [steamPid] + [child.pid for child in children]

        for pid in all_pids:
            if not psutil.pid_exists(pid):
                continue

            try:
                exclude_titles = {"Steam", "Friends List", "Special Offers"}
                windows = [hwnd for hwnd in findwindows.find_windows(process=pid)
                           if win32gui.GetWindowText(hwnd) not in exclude_titles]
                if not windows:
                    continue

                app = Application(backend="uia").connect(process=pid)
                for win in app.windows():
                    try:
                        win.set_focus()
                        all_descendants = win.descendants()
                        edits = [c for c in all_descendants if c.friendly_class_name() == "Edit"]
                        buttons = [c for c in all_descendants if c.friendly_class_name() == "Button"]
                        statics = [c for c in all_descendants if c.friendly_class_name() == "Static"]
                        if len(edits) == 2 and any(btn.window_text().strip() == "Sign in" for btn in buttons):
                            edits[0].set_text(self.login)
                            edits[1].set_text(self.password)
                            sign_in_button = next((btn for btn in buttons if btn.window_text().strip() == "Sign in"), None)
                            if sign_in_button:
                                sign_in_button.click()
                            time.sleep(2)
                        if any(txt.window_text().strip() == "Enter a code instead" for txt in statics):
                            target = next((s for s in statics if s.window_text().strip() == "Enter a code instead"), None)
                            if target:
                                target.click_input()
                        if any(btn.window_text().strip() == "Play anyway" for btn in buttons):
                            target = next((btn for btn in buttons if btn.window_text().strip() == "Play anyway"), None)
                            if target:
                                target.click()
                        if any(btn.window_text().strip().lower() == "no thanks" for btn in buttons):
                            target = next((btn for btn in buttons if btn.window_text().strip().lower() == "no thanks"), None)
                            if target:
                                target.click()
                        if any(txt.window_text().strip() == "Enter the code from your Steam Mobile App" for txt in statics) \
                                and self.shared_secret is not None:
                            win.set_focus()
                            pyperclip.copy(self.get_auth_code())
                            time.sleep(0.1)
                            MouseHelper.PasteText()
                    except Exception as e:
                        print(f"[{self.login}] Ошибка обработки окна: {e}")
            except Exception as e:
                print(f"[{self.login}] Не удалось подключиться к PID {pid}: {e}")

    def ProcessWindowsAfterCS(self, steamPid):
        try:
            parent = psutil.Process(steamPid)
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"[{self.login}] ProcessWindowsAfterCS: не удалось получить процесс {steamPid}: {e}")
            return

        all_pids = [steamPid] + [child.pid for child in children]

        # Сначала находим hwnd окна CS2 чтобы его не закрывать
        cs2_hwnd = self.FindCSWindow()

        for pid in all_pids:
            if not psutil.pid_exists(pid):
                continue
            try:
                windows = findwindows.find_windows(process=pid)
                for hwnd in windows:
                    if cs2_hwnd and hwnd == cs2_hwnd:
                        continue  # пропускаем окно CS2
                    try:
                        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[{self.login}] Ошибка при обработке PID {pid}: {e}")

    # -------------------------------------------------------------------------
    # runtime.json helpers
    # -------------------------------------------------------------------------
    def _save_runtime(self):
        runtime_path = Path("runtime.json")
        try:
            data = []
            if runtime_path.exists():
                with open(runtime_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data = [d for d in data if d.get("login") != self.login]
            data.append({
                "login": self.login,
                "SteamPid": self.steamProcess.pid if self.steamProcess else None,
                "CS2Pid": self.CS2Process.pid if self.CS2Process else None,
            })
            with open(runtime_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[{self.login}] Ошибка записи runtime.json: {e}")

    def _remove_from_runtime(self):
        runtime_path = Path("runtime.json")
        try:
            if not runtime_path.exists():
                return
            with open(runtime_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = [d for d in data if d.get("login") != self.login]
            with open(runtime_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[{self.login}] Ошибка очистки runtime.json: {e}")

    # -------------------------------------------------------------------------
    # cfg / game files
    # -------------------------------------------------------------------------
    def _prepare_cfg_folder(self, cfg_path: str):
        """
        Надёжно сносит и пересоздаёт папку cfg.
        Сначала снимает атрибуты через attrib, потом удаляет,
        с повторной попыткой при PermissionError.
        """
        if os.path.exists(cfg_path):
            # Снимаем все системные атрибуты
            subprocess.run(
                f'attrib -R -A -S -H "{cfg_path}" /S /D',
                shell=True, capture_output=True
            )
            time.sleep(0.3)  # даём файловой системе применить изменения

            # Пытаемся удалить с обработчиком read-only
            try:
                shutil.rmtree(cfg_path, onerror=_force_remove_readonly)
            except Exception as e:
                print(f"[{self.login}] rmtree не смог удалить {cfg_path}: {e}")
                # Крайний вариант — через cmd
                subprocess.run(f'rd /s /q "{cfg_path}"', shell=True, capture_output=True)
                time.sleep(0.3)

        os.makedirs(cfg_path, exist_ok=True)

    # -------------------------------------------------------------------------
    # StartGame
    # -------------------------------------------------------------------------
    def StartGame(self) -> bool:
        print(f"[{self.login}] Запуск Steam...")
        steam_path = self._settingsManager.get("SteamPath", r"C:\Program Files (x86)\Steam\steam.exe")
        cs2_path = self._settingsManager.get(
            "CS2Path", r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive"
        )

        # --- Remove background files ---
        if self._settingsManager.get("RemoveBackground", False):
            maps_path = Path(cs2_path) / "game" / "csgo" / "maps"
            if maps_path.exists() and maps_path.is_dir():
                for file in maps_path.iterdir():
                    if file.is_file() and file.name.endswith("_vanity.vpk"):
                        try:
                            file.unlink()
                            print(f"[{self.login}] Удалён файл: {file}")
                        except Exception as e:
                            print(f"[{self.login}] Не удалось удалить {file}: {e}")
            panorama_path = Path(cs2_path) / "game" / "csgo" / "panorama" / "videos"
            if panorama_path.exists() and panorama_path.is_dir():
                try:
                    shutil.rmtree(panorama_path, onerror=_force_remove_readonly)
                    print(f"[{self.login}] Удалена папка: {panorama_path}")
                except Exception as e:
                    print(f"[{self.login}] Не удалось удалить {panorama_path}: {e}")

        # --- Copy fsn.cfg ---
        try:
            shutil.copy2(
                os.path.join(get_base_path(), "settings", "fsn.cfg"),
                os.path.join(Path(cs2_path) / "game" / "csgo" / "cfg", "fsn.cfg")
            )
        except Exception as e:
            print(f"[{self.login}] Не удалось скопировать fsn.cfg: {e}")

        # --- Prepare userdata cfg ---
        if self.steam_id != 0:
            account_id = str(self.steam_id - 76561197960265728)
            userdata_path = os.path.join(os.path.dirname(steam_path), "userdata", account_id)
            cfg_path = os.path.join(userdata_path, "730", "local", "cfg")

            self._prepare_cfg_folder(cfg_path)

            settings_path = os.path.join(get_base_path(), "settings")
            video_src = os.path.join(settings_path, "cs2_video.txt")
            convars_src = os.path.join(settings_path, "cs2_machine_convars.vcfg")

            if os.path.exists(video_src) and os.path.exists(convars_src):
                dst_video = os.path.join(cfg_path, "cs2_video.txt")
                dst_convars = os.path.join(cfg_path, "cs2_machine_convars.vcfg")

                vendorID = self._settingsManager.get("VendorID", 0)
                deviceID = self._settingsManager.get("DeviceID", 0)

                if vendorID == 0 or deviceID == 0:
                    best_gpu = HardwareUtils.get_best_gpu()
                    vendorID = best_gpu["VendorID"]
                    deviceID = best_gpu["DeviceID"]
                    self._settingsManager.set("VendorID", vendorID)
                    self._settingsManager.set("DeviceID", deviceID)
                    self._logManager.add_log(f"[{self.login}] Detected VendorID: {vendorID}, DeviceID: {deviceID}")

                updates = {
                    "VendorID": str(vendorID),
                    "DeviceID": str(deviceID),
                }
                ConfigHelper.update_video_cfg(video_src, dst_video, updates)
                try:
                    shutil.copy2(convars_src, dst_convars)
                except Exception as e:
                    print(f"[{self.login}] Не удалось скопировать convars: {e}")

                # Снимаем атрибуты после записи
                subprocess.run(
                    f'attrib -R -A -S -H "{cfg_path}\\*" /S /D',
                    shell=True, capture_output=True
                )

        # --- Launch Steam ---
        try:
            WinregHelper.set_value(r"Software\Valve\Steam", "AutoLoginUser", self.login, winreg.REG_SZ)
            args = (
                f'{self._settingsManager.get("SteamArg", r"-nofriendsui -vgui -noreactlogin -noverifyfiles -nobootstrapupdate -skipinitialbootstrap -norepairfiles -overridepackageurl -disable-winh264")}'
                f' -applaunch 730 '
                f'-con_logfile {self.login}.log '
                f'{self._settingsManager.get("CS2Arg", r"-condebug -conclearlog +exec fsn.cfg -language english -windowed -allowmultiple -noborder -swapcores -noqueuedload -vrdisable -windowed -w 383 -h 280 -nopreload -limitvsconst -softparticlesdefaultoff -nohltv -noaafonts -nosound -novid +violence_hblood 0 +sethdmodels 0 +mat_disable_fancy_blending 1 +r_dynamic 0 +engine_no_focus_sleep 120 -nojoy")}'
            )
            final = [steam_path] + shlex.split(args)
            self.steamProcess = subprocess.Popen(final)
        except Exception as e:
            print(f"[{self.login}] Ошибка запуска Steam: {e}")
            return False

        # --- Wait for CS2 to appear ---
        max_wait = 180  # секунд максимум
        waited = 0
        cs2_found = False

        while waited < max_wait:
            # Проверяем что Steam ещё жив
            if not psutil.pid_exists(self.steamProcess.pid):
                print(f"[{self.login}] Steam процесс завершился неожиданно!")
                return False

            self.ProcessWindowsBeforeCS(self.steamProcess.pid)

            try:
                for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                    try:
                        if proc.info['name'] and proc.info['name'].lower() == 'cs2.exe':
                            ppid = proc.info['ppid']
                            if ppid == self.steamProcess.pid:
                                self.CS2Process = proc
                                cs2_found = True
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as e:
                print(f"[{self.login}] Ошибка при поиске CS2: {e}")

            if cs2_found:
                break

            time.sleep(1)
            waited += 1

        if not cs2_found:
            print(f"[{self.login}] CS2 не запустился за {max_wait} секунд!")
            return False

        self.ProcessWindowsAfterCS(self.steamProcess.pid)

        # Ждём пока CS2 нормально инициализируется
        time.sleep(5)

        # Устанавливаем заголовок окна
        csWindow = self.FindCSWindow()
        if csWindow:
            SystemUtils.fix_window_dpi(csWindow)
            SystemUtils.SetWindowText(csWindow, f"[FSN FREE] {self.login}")

        self.setColor("green")
        self._save_runtime()
        self.MonitorCS2(interval=5)
        self.start_log_watcher(f"{self.login}.log")
        return True
    # -------------------------------------------------------------------------
    # Monitor CS2
    # -------------------------------------------------------------------------
    def MonitorCS2(self, interval: float = 2.0, retry_delay: float = 10.0):
        """
        Отслеживает процесс CS2. Если он пропадает — перепроверяет через retry_delay.
        Если процесс действительно пропал — убивает Steam и чистит runtime.json.
        """
        self._stop_monitoring = False

        def monitor():
            while not self._stop_monitoring:
                if not getattr(self, 'CS2Process', None):
                    time.sleep(interval)
                    continue

                try:
                    alive = psutil.pid_exists(self.CS2Process.pid)
                except Exception:
                    alive = False

                if alive:
                    time.sleep(interval)
                    continue

                # Процесс пропал — перепроверяем
                print(f"[{self.login}] CS2.exe не найден, перепроверяем через {retry_delay} с...")
                time.sleep(retry_delay)

                try:
                    still_gone = not psutil.pid_exists(self.CS2Process.pid)
                except Exception:
                    still_gone = True

                if still_gone:
                    print(f"[{self.login}] CS2.exe действительно пропал, убиваем Steam...")
                    self.KillSteamAndCS()
                    break

                time.sleep(interval)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    # -------------------------------------------------------------------------
    # Kill
    # -------------------------------------------------------------------------
    def KillSteamAndCS(self):
        """Завершает процессы CS2 и Steam, чистит runtime.json."""
        self._stop_monitoring = True

        if self.CS2Process:
            try:
                if psutil.pid_exists(self.CS2Process.pid):
                    print(f"[{self.login}] Убиваем CS2.exe (PID {self.CS2Process.pid})")
                    self.CS2Process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"[{self.login}] Ошибка при убийстве CS2.exe: {e}")
            finally:
                self.CS2Process = None

        if self.steamProcess:
            try:
                if psutil.pid_exists(self.steamProcess.pid):
                    print(f"[{self.login}] Убиваем Steam.exe (PID {self.steamProcess.pid})")
                    self.steamProcess.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"[{self.login}] Ошибка при убийстве Steam.exe: {e}")
            finally:
                self.steamProcess = None

        self.setColor("#DCE4EE")
        self._remove_from_runtime()