import threading
import time

from Managers.AccountsManager import AccountManager
from Managers.LobbyManager import LobbyManager
from Managers.LogManager import LogManager


class AutoAcceptModule:
    def __init__(self):
        self._running = False
        self._thread = None
        self.logManager = LogManager()
        self.accountManager = AccountManager()

    def _auto_accept_loop(self):
        lobbyManager = LobbyManager() # Предполагаю, что есть ссылка на LobbyManager

        while self._running:
            if not lobbyManager.isValid():
                # Старая логика: все аккаунты
                accounts = [acc for acc in self.accountManager.accounts if acc.isCSValid()]
                self._check_accounts(accounts)
            else:
                # Разделяем на команды
                team1_accounts = [lobbyManager.team1.leader] + lobbyManager.team1.bots
                team2_accounts = [lobbyManager.team2.leader] + lobbyManager.team2.bots
                accounts = team1_accounts + team2_accounts
                self._check_accounts(accounts)

            time.sleep(1)  # Основная пауза цикла

    def _check_accounts(self, accounts):
        if not accounts:
            return
        if len(accounts) < 2:
            return
        valid_accounts = [acc for acc in accounts if acc.last_match_id is not None]

        # Если нет ни одного аккаунта с установленным last_match_id — ничего не делаем
        if not valid_accounts:
            return
        time.sleep(1)
        first_id = accounts[0].last_match_id
        all_same = first_id is not None and all(acc.last_match_id == first_id for acc in accounts)

        if all_same:
            self.logManager.add_log("[AutoAccept] Game found accepting...")
            for acc in accounts:
                acc.last_match_id = None
                win_width, win_height = acc.getWindowSize()
                center_x = win_width // 2
                center_y = win_height // 2
                acc.ClickMouse(center_x, center_y)
                time.sleep(0.2)
            return

        # Перепроверка через секунду
        time.sleep(1)
        first_id_retry = accounts[0].last_match_id
        all_same_retry = first_id_retry is not None and all(acc.last_match_id == first_id_retry for acc in accounts)

        if all_same_retry:
            self.logManager.add_log("[AutoAccept] Game found accepting...")
            for acc in accounts:
                acc.last_match_id = None
                win_width, win_height = acc.getWindowSize()
                center_x = win_width // 2
                center_y = win_height // 2
                acc.ClickMouse(center_x, center_y)
                time.sleep(0.2)
        else:
            print("Miss game")
            for acc in accounts:
                acc.last_match_id = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._auto_accept_loop, daemon=True)
            self._thread.start()
            print("AutoAccept started")

    def stop(self):
        if self._running:
            self._running = False
            if self._thread is not None:
                self._thread.join(timeout=1)
            print("AutoAccept stopped")

    def toggle(self):
        if self._running:
            self.stop()
        else:
            self.start()
