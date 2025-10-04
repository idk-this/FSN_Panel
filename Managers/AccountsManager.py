import os
import json
import threading
import queue

from Instances.AccountInstance import Account


class AccountManager:
    _instance = None  # статическое поле для хранения одного экземпляра

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, logpass_file="logpass.txt", mafiles_dir="mafiles"):
        if hasattr(self, "_initialized"):
            return  # чтобы __init__ не выполнялся повторно
        self._initialized = True
        self.selected_accounts = []
        self.logpass_file = logpass_file
        self.mafiles_dir = mafiles_dir
        self.accounts = self._load_accounts()

        self.accounts_start_queue = queue.Queue()
        self.accounts_start_queue_thread = threading.Thread(target=self._accounts_start_process_queue, daemon=True)
        self.accounts_start_queue_thread.start()

    def _load_accounts(self):
        # Создаем файл, если его нет
        if not os.path.exists(self.logpass_file):
            with open(self.logpass_file, "w") as f:
                f.write("example:password\n")

        # Загружаем логины и пароли
        with open(self.logpass_file, "r") as f:
            lines = [line.strip().split(":") for line in f if ":" in line]

        # Загружаем mafiles
        mafiles = {}
        if os.path.exists(self.mafiles_dir):
            for file in os.listdir(self.mafiles_dir):
                if file.lower().endswith(".mafile"):
                    try:
                        with open(os.path.join(self.mafiles_dir, file), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            account_name = data.get("account_name", "").lower()

                            # Извлекаем shared_secret и identity_secret
                            shared_secret = data.get("shared_secret")

                            # Извлекаем steam_id из вложенного Session
                            steam_id = 0
                            session = data.get("Session")
                            if session and "SteamID" in session:
                                steam_id = session.get("SteamID", 0)

                            if account_name:
                                mafiles[account_name] = {
                                    "shared_secret": shared_secret,
                                    "steam_id": steam_id
                                }
                    except Exception:
                        pass

        # Создаем список аккаунтов
        accounts = []
        for login, password in lines:
            mafile_data = mafiles.get(login.lower())
            if mafile_data:
                try:
                    accounts.append(Account(
                        login,
                        password,
                        mafile_data.get("shared_secret"),
                        int(mafile_data.get("steam_id", 0))
                        ))
                except Exception:
                    pass


            else:
                accounts.append(Account(login, password, None, 0))  # Без shared_secret и steam_id

        return accounts

    def get_all_accounts(self):
        return self.accounts

    def count_launched_accounts(self):
        return sum(1 for account in self.accounts if account._color == "green")
    def get_account(self, login):
        login = login.lower()
        for account in self.accounts:
            if account.login.lower() == login:
                return account
        return None

    def add_to_start_queue(self, account):
        if account.isCSValid():
            print(f"{account.login} is already running skip")
            return

        # Проверка: уже в очереди
        if account in list(self.accounts_start_queue.queue):
            print(f"{account.login} in start queue skip")
            return
        account.setColor("yellow")
        # Если не в очереди и не запущен, добавляем
        self.accounts_start_queue.put(account)
        print(f"{account.login} added to start queue")

    def _accounts_start_process_queue(self):
        """Обрабатываем очередь аккаунтов по одному"""
        while True:
            account = self.accounts_start_queue.get()
            if account is None:
                break

            try:
                account.StartGame()  # запуск аккаунта
                # После успешного запуска меняем цвет на зелёный
                account.setColor("green")
                account.MonitorCS2(interval=5)  # запускаем мониторинг CS2
            except Exception as e:
                print(f"Ошибка запуска {account.login}: {e}")
                account.KillSteamAndCS()
            finally:
                self.accounts_start_queue.task_done()