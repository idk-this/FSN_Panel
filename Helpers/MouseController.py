import time

import pyautogui


import pyautogui
import win32gui
import win32con
import ctypes

class MouseHelper:
    """
    Статический хелпер для управления мышью относительно окна.
    """

    @staticmethod
    def get_window_client_rect(hwnd):
        """
        Возвращает координаты клиентской области окна в глобальных координатах.
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None
        rect = win32gui.GetClientRect(hwnd)
        left, top = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
        right, bottom = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
        return (left, top, right, bottom)

    @staticmethod
    def MoveMouse(hwnd, x, y):
        """
        Перемещает курсор мыши в координаты (x, y) относительно клиентской области окна.
        """
        client_rect = MouseHelper.get_window_client_rect(hwnd)
        if client_rect is None:
            return
        screen_x = client_rect[0] + x
        screen_y = client_rect[1] + y
        pyautogui.moveTo(screen_x, screen_y)

    @staticmethod
    def ClickMouse(hwnd, x, y, button='left'):
        """
        Кликает мышью в координаты (x, y) относительно клиентской области окна.
        """
        MouseHelper.MoveMouse(hwnd, x, y)
        pyautogui.click(button=button)

    @staticmethod
    def PasteText():
        # keybd_event устарел, но работает во многих системах
        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002
        try:
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)  # ctrl down
            ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)  # v down
            time.sleep(0.01)
            ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)  # v up
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)  # ctrl up
            return True
        except Exception:
            return False