import time

import pyautogui
import pyperclip
import win32gui
import keyboard

from Helpers.MouseController import MouseHelper


class LobbyInstance:
    def __init__(self, leader, bots):
        self.leader = leader
        self.bots = bots

    def Collect(self):

        LeaderHwnd = self.leader.FindCSWindow()

        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            bot.MoveMouse(380, 100)
            time.sleep(0.5)
            bot.ClickMouse(375, 8)
            time.sleep(1)
            bot.ClickMouse(204, 157)
            time.sleep(0.5)
            bot.ClickMouse(237, 157)
            win32gui.SetForegroundWindow(LeaderHwnd)
            self.leader.MoveMouse(380, 100)
            time.sleep(0.6)
            self.leader.ClickMouse(375, 8)
            time.sleep(1)
            MouseHelper.PasteText()
            time.sleep(1)
            self.leader.ClickMouse(195, 140)
            time.sleep(1.5)
            for i in range(142, 221, 5):
                self.leader.ClickMouse(235, i)
                time.sleep(0.001)
            self.leader.ClickMouse(235, 165)
        time.sleep(1.5)
        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            win32gui.SetForegroundWindow(hwnd)
            bot.MoveMouse(380, 100)
            time.sleep(0.6)
            bot.ClickMouse(306, 37)

    def Disband(self):
        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            bot.MoveMouse(380, 100)
            time.sleep(0.5)
            bot.ClickMouse(375, 8)
