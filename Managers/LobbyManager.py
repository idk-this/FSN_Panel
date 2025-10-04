import ctypes
import random
import threading
import time

import keyboard

from Instances.LobbyInstance import LobbyInstance
from Managers.AccountsManager import AccountManager
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager


class LobbyManager:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LobbyManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._accountManager = AccountManager()
        self._logManager = LogManager()
        self._settingManager = SettingsManager()
        self.team1 = None
        self.team2 = None
        self._initialized = True

    def Shuffle(self):
        valid_accounts = [acc for acc in self._accountManager.accounts if acc.isCSValid()]
        total = len(valid_accounts)

        # Правила распределения
        lobby_rules = {4: 1, 6: 2, 8: 3, 10: 4}

        if total < 4 or total > 10 or total % 2 == 1:
            self._logManager.add_log("Incorrect number of accounts")
            return

        bots_per_leader = lobby_rules[total]
        shuffled = valid_accounts[:]
        while True:
            random.shuffle(shuffled)
            # Проверяем, что лидеры не совпадают с предыдущим порядком (не просто swap)
            if shuffled != valid_accounts:
                break

        # Разделяем на команды
        leader1 = shuffled[0]
        bots1 = shuffled[1:1 + bots_per_leader]

        leader2 = shuffled[1 + bots_per_leader]
        bots2 = shuffled[1 + bots_per_leader + 1: 1 + bots_per_leader * 2 + 1]

        self.team1 = LobbyInstance(leader1, bots1)
        self.team2 = LobbyInstance(leader2, bots2)
        self.MoveWindows()
        self._logManager.add_log("Successfully shuffled accounts")

    def isValid(self):
        # Проверяем, что обе команды существуют
        if self.team1 is None or self.team2 is None:
            return False

        # Проверяем, что лидер и все боты команды 1 валидны
        if not self.team1.leader.isCSValid():
            return False
        if any(not bot.isCSValid() for bot in self.team1.bots):
            return False

        # Проверяем, что лидер и все боты команды 2 валидны
        if not self.team2.leader.isCSValid():
            return False
        if any(not bot.isCSValid() for bot in self.team2.bots):
            return False

        # Всё прошло — объект валиден
        return True
    def CollectLobby(self):
        self.team1.Collect()
        self.team2.Collect()
    def DisbandLobbies(self):
        if self.team1 is not None:
            self.team1.Disband()
            self.team1 = None
        if self.team2 is not None:
            self.team2.Disband()
            self.team2 = None

    def MoveWindows(self):
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        x = 0
        y = 0
        max_row_height = 0

        # Проходим по командам по очереди
        for team in [self.team1, self.team2]:
            members = [team.leader] + team.bots
            for member in members:
                win_width, win_height = member.getWindowSize()  # предполагаем, что есть метод для получения размеров окна

                # Перенос на новую строку, если не помещается по ширине
                if x + win_width > screen_width:
                    x = 0
                    y += max_row_height
                    max_row_height = 0

                member.MoveWindow(x, y)  # перемещаем окно
                x += win_width
                max_row_height = max(max_row_height, win_height)

            # После команды сбрасываем x и увеличиваем y, чтобы следующая команда шла ниже
            x = 0
            y += max_row_height
            max_row_height = 0