import ctypes
from ctypes import wintypes
import win32gui, win32process, win32con

user32 = ctypes.WinDLL('user32', use_last_error=True)

HWND = wintypes.HWND
RECT = wintypes.RECT
LPRECT = ctypes.POINTER(RECT)
BOOL = wintypes.BOOL
UINT = wintypes.UINT

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

SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004


class SystemUtils:
    @staticmethod
    def show_error(message):
        try:
            user32.MessageBoxW(0, message, "System Error", 0x10)
        except Exception:
            print(f"[SystemUtils] show_error: {message}")

    @staticmethod
    def fix_window_dpi(hwnd):
        if not hwnd:
            return
        try:
            SetProcessDPIAware()

            wr = RECT()
            cr = RECT()

            if not GetWindowRect(hwnd, ctypes.byref(wr)) or not GetClientRect(hwnd, ctypes.byref(cr)):
                return

            current_client_width = cr.right - cr.left
            current_client_height = cr.bottom - cr.top
            current_window_width = wr.right - wr.left
            current_window_height = wr.bottom - wr.top

            if current_client_width != current_window_width or current_client_height != current_window_height:
                SetWindowPos(hwnd, None, wr.left, wr.top, current_client_width, current_client_height,
                             SWP_NOZORDER | SWP_NOMOVE)
        except Exception as e:
            print(f"[SystemUtils] fix_window_dpi error: {e}")

    @staticmethod
    def SetWindowText(hwnd, text, *args):
        if not hwnd:
            return
        try:
            SetWindowText(hwnd, text, *args)
        except Exception as e:
            print(f"[SystemUtils] SetWindowText error: {e}")

    @staticmethod
    def get_hwnd_by_pid(pid) -> int:
        """Возвращает HWND главного окна процесса, или 0 если не найдено."""
        if not pid:
            return 0
        hwnds = []

        def enum_windows_callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd) or not win32gui.IsWindowEnabled(hwnd):
                    return True
                if win32gui.GetParent(hwnd) != 0:
                    return True
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == pid:
                    hwnds.append(hwnd)
                    return False  # нашли, останавливаем
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            # EnumWindows бросает исключение когда callback возвращает False — это нормально
            if hwnds:
                pass  # всё хорошо, нашли окно
            else:
                print(f"[SystemUtils] get_hwnd_by_pid({pid}) error: {e}")

        return hwnds[0] if hwnds else 0