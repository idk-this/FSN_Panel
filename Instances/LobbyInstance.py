import time

import win32gui

from Helpers.MouseController import MouseHelper


class LobbyInstance:
    def __init__(self, leader, bots):
        self.leader = leader
        self.bots = bots

    def Collect(self):
        LeaderHwnd = self.leader.FindCSWindow()
        if not LeaderHwnd:
            print("[LobbyInstance] Collect: не найдено окно лидера!")
            return

        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            if not hwnd:
                print(f"[LobbyInstance] Collect: не найдено окно бота {bot.login}, пропускаем")
                continue

            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                bot.MoveMouse(380, 100)
                time.sleep(0.5)
                bot.ClickMouse(375, 8)
                time.sleep(1)
                bot.ClickMouse(204, 157)
                time.sleep(0.5)
                bot.ClickMouse(237, 157)
            except Exception as e:
                print(f"[LobbyInstance] Ошибка при обработке бота {bot.login}: {e}")
                continue

            try:
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
            except Exception as e:
                print(f"[LobbyInstance] Ошибка при действии лидера: {e}")

        time.sleep(1.5)

        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            if not hwnd:
                print(f"[LobbyInstance] Collect (accept): не найдено окно бота {bot.login}")
                continue
            try:
                win32gui.SetForegroundWindow(hwnd)
                bot.MoveMouse(380, 100)
                time.sleep(0.6)
                bot.ClickMouse(306, 37)
            except Exception as e:
                print(f"[LobbyInstance] Ошибка принятия инвайта ботом {bot.login}: {e}")

    def Disband(self):
        for bot in self.bots:
            hwnd = bot.FindCSWindow()
            if not hwnd:
                print(f"[LobbyInstance] Disband: не найдено окно бота {bot.login}, пропускаем")
                continue
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                bot.MoveMouse(380, 100)
                time.sleep(0.5)
                bot.ClickMouse(375, 8)
            except Exception as e:
                print(f"[LobbyInstance] Ошибка при Disband бота {bot.login}: {e}")