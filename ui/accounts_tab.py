import os
import re
import threading
import customtkinter

from Helpers.LoginExecutor import SteamLoginSession
from Managers.AccountsManager import AccountManager
from Managers.LogManager import LogManager
from Managers.SettingsManager import SettingsManager


class AccountsControl(customtkinter.CTkTabview):
    def __init__(self, parent, update_label):
        super().__init__(parent, width=250)
        self._active_stat_threads = 0
        self._stat_lock = threading.Lock()
        self._settingsManager = SettingsManager()
        self._logManager = LogManager()
        self.accountsManager = AccountManager()
        self.update_label = update_label
        self.stat_buttons = []
        self.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # Вкладки
        self.add("Accounts Control")
        self.tab("Accounts Control").grid_columnconfigure(0, weight=1)

        self.add("Account Stat")
        self.tab("Account Stat").grid_columnconfigure(0, weight=1)

        self.create_control_buttons()
        self.create_stat_buttons()

    # ----------------- Вкладка Accounts Control -----------------
    def create_control_buttons(self):
        buttons = [
            ("Start selected accounts", "darkgreen", self.start_selected),
            ("Kill selected accounts", "red", self.kill_selected),
            ("Select first 10 accounts", None, self.select_first_10),
            ("Select first 4 accounts", None, self.select_first_4),
        ]
        for i, (text, color, cmd) in enumerate(buttons):
            b = customtkinter.CTkButton(self.tab("Accounts Control"), text=text, fg_color=color, command=cmd)
            b.grid(row=i, column=0, padx=20, pady=10)

    def create_stat_buttons(self):
        buttons = [
            ("Get level", None, self.try_get_level),
            ("Get wingman Rank", None, self.try_get_wingmanRank),
            ("Get MM Ranks", None, self.try_get_mapStats),
            ("Get premier Rank", None, self.try_get_premierRank),
            ("Get all in html", None, self.save_stats_to_html),
        ]
        for i, (text, color, cmd) in enumerate(buttons):
            b = customtkinter.CTkButton(self.tab("Account Stat"), text=text, fg_color=color,
                                        command=lambda c=cmd: self._run_stat_with_lock(c))
            b.grid(row=i, column=0, padx=20, pady=10)
            self.stat_buttons.append(b)

    def _disable_stat_buttons(self):
        for b in self.stat_buttons:
            b.configure(state="disabled")

    def _enable_stat_buttons(self):
        for b in self.stat_buttons:
            b.configure(state="normal")

    def _run_stat_with_lock(self, func):
        def wrapper():
            with self._stat_lock:
                self._active_stat_threads += 1
                if self._active_stat_threads == 1:
                    self._disable_stat_buttons()
            try:
                func()
            finally:
                with self._stat_lock:
                    self._active_stat_threads -= 1
                    if self._active_stat_threads == 0:
                        self._enable_stat_buttons()

        self._run_in_thread(wrapper)

    # ----------------- Control Actions -----------------
    def start_selected(self):
        steam_path = self._settingsManager.get("SteamPath", r"C:\Program Files (x86)\Steam\steam.exe")
        cs2_path = self._settingsManager.get(
            "CS2Path", r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive"
        )
        cs2_exe_path = os.path.join(cs2_path, r"game\bin\win64\cs2.exe")

        if not os.path.isfile(steam_path) or not steam_path.lower().endswith('.exe'):
            self._logManager.add_log("Steam path incorrect")
            return
        if not os.path.isfile(cs2_exe_path):
            self._logManager.add_log("CS2 path incorrect")
            return

        for acc in self.accountsManager.selected_accounts:
            self.accountsManager.add_to_start_queue(acc)
            print("Starting:", acc.login)

        self.accountsManager.selected_accounts.clear()
        self.update_label()

    def kill_selected(self):
        for acc in self.accountsManager.selected_accounts:
            acc.KillSteamAndCS()

    def select_first_10(self):
        self._select_first_n(10)

    def select_first_4(self):
        self._select_first_n(4)

    def _select_first_n(self, n):
        for acc in self.accountsManager.accounts[:n]:
            if acc not in self.accountsManager.selected_accounts:
                self.accountsManager.selected_accounts.append(acc)
        self.update_label()

    # ----------------- Helper Methods -----------------
    def _fetch_html(self, steam, url_suffix="gcpd/730/?tab=matchmaking"):
        SESSION_FILE = "settings/sessions.json"
        if not steam.load_session(SESSION_FILE):
            try:
                steam.login()
                steam.save_session(SESSION_FILE)
            except Exception as e:
                self._logManager.add_log(f"[{steam.login}] ❌ Failed to login: {e}")
                return None
        try:
            resp = steam.session.get(f'https://steamcommunity.com/profiles/{steam.steamid}/{url_suffix}', timeout=10)
        except Exception as e:
            self._logManager.add_log(f"[{steam.login}] ❌ Failed to fetch page: {e}")
            return None
        if resp.status_code != 200:
            self._logManager.add_log(f"[{steam.login}] ❌ HTTP {resp.status_code}")
            return None
        return resp.text

    def _parse_table(self, html, columns_regex, row_identifier=None):
        """
        columns_regex: regex for <tr> cells
        row_identifier: optional regex to filter only specific rows
        """
        table_match = re.search(r'<table class="generic_kv_table">.*?</table>', html, re.DOTALL)
        if not table_match:
            return []

        table_html = table_match.group(0)
        rows = re.findall(columns_regex, table_html)

        if row_identifier:
            rows = [r for r in rows if re.search(row_identifier, r[0])]

        return rows

    def _run_in_thread(self, func):
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

    # ----------------- Stats Methods -----------------
    def try_get_level(self):
        def worker():
            for acc in self.accountsManager.selected_accounts:
                steam = SteamLoginSession(acc.login, acc.password, acc.shared_secret)
                html = self._fetch_html(steam, url_suffix="gcpd/730")
                if not html:
                    continue
                rank_match = re.search(r'CS:GO Profile Rank:\s*([^\n<]+)', html)
                xp_match = re.search(r'Experience points earned towards next rank:\s*([^\n<]+)', html)
                if rank_match and xp_match:
                    rank = rank_match.group(1).strip()
                    exp = xp_match.group(1).strip()
                    self._logManager.add_log(f"[{acc.login}] ✅ Level: {rank} | XP: {exp}")
                else:
                    self._logManager.add_log(f"[{acc.login}] ❌ Failed to parse rank from profile page")
        self._run_stat_with_lock(worker)

    def try_get_premierRank(self):
        def worker():
            for acc in self.accountsManager.selected_accounts:
                steam = SteamLoginSession(acc.login, acc.password, acc.shared_secret)
                html = self._fetch_html(steam)
                if not html:
                    continue

                match = re.search(
                    r'<td>Premier</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                    html
                )
                if match:
                    wins, ties, losses = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    skill = match.group(4).strip()
                    skill = int(skill) if skill.isdigit() else -1
                    self._logManager.add_log(f"[{acc.login}] Premier: W:{wins} T:{ties} L:{losses} R:{skill}")
                else:
                    self._logManager.add_log(f"[{acc.login}] ⚠ Premier stats not found")

        self._run_stat_with_lock(worker)

    def try_get_wingmanRank(self):
        def worker():
            for acc in self.accountsManager.selected_accounts:
                steam = SteamLoginSession(acc.login, acc.password, acc.shared_secret)
                html = self._fetch_html(steam)
                if not html:
                    continue

                match = re.search(
                    r'<td>Wingman</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                    html
                )
                if match:
                    wins, ties, losses = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    skill = match.group(4).strip()
                    skill = int(skill) if skill.isdigit() else -1
                    self._logManager.add_log(f"[{acc.login}] Wingman: W:{wins} T:{ties} L:{losses} R:{skill}")
                else:
                    self._logManager.add_log(f"[{acc.login}] ⚠ Wingman stats not found")

        self._run_stat_with_lock(worker)

    def try_get_mapStats(self):
        def worker():
            for acc in self.accountsManager.selected_accounts:
                steam = SteamLoginSession(acc.login, acc.password, acc.shared_secret)
                html = self._fetch_html(steam)
                if not html:
                    continue

                # Находим таблицу с Map
                table_match = re.search(
                    r'<table class="generic_kv_table"><tr>\s*<th>Matchmaking Mode</th>\s*<th>Map</th>.*?</table>',
                    html, re.DOTALL
                )
                if not table_match:
                    self._logManager.add_log(f"[{acc.login}] ⚠ No map stats table found")
                    continue

                table_html = table_match.group(0)
                rows = re.findall(
                    r'<tr>\s*<td>([^<]+)</td><td>([^<]+)</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                    table_html
                )

                if not rows:
                    self._logManager.add_log(f"[{acc.login}] ⚠ Map stats not found in table")
                    continue

                for mode, map_name, wins, ties, losses, skill in rows:
                    wins, ties, losses = int(wins), int(ties), int(losses)
                    skill = skill.strip()
                    skill = int(skill) if skill.isdigit() else -1
                    self._logManager.add_log(
                        f"[{acc.login}] Map '{map_name}': W:{wins} T:{ties} L:{losses} R:{skill}"
                    )

        self._run_stat_with_lock(worker)

    def save_stats_to_html(self, filename="cs2_stats.html"):
        """
        Сохраняет статистику выбранных аккаунтов в аккуратный компактный HTML-отчёт.
        """

        def worker():
            html_parts = [
                "<!DOCTYPE html>",
                "<html><head><meta charset='UTF-8'><title>CS2 Stats</title>",
                "<style>",
                "body { background-color: #121212; color: #eee; font-family: 'Segoe UI', Tahoma, sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; }",
                "h1 { color: #00bfff; margin-bottom: 30px; }",
                ".account-card { background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 20px; width: 100%; max-width: 600px; box-shadow: 0 3px 8px rgba(0,0,0,0.5); }",
                ".account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }",
                ".account-title { font-size: 1.3em; color: #ffcc00; }",
                ".account-level { font-size: 0.95em; color: #00ff90; }",
                "table { border-collapse: collapse; width: 100%; margin-bottom: 10px; font-size: 13px; }",
                "th, td { border: 1px solid #333; padding: 5px; text-align: center; }",
                "th { background-color: #222; color: #fff; }",
                "tr:nth-child(even) { background-color: #2a2a2a; }",
                "tr:hover { background-color: #333; }",
                ".wins { color: #00ff00; font-weight: bold; }",
                ".ties { color: #ffff66; font-weight: bold; }",
                ".losses { color: #ff5555; font-weight: bold; }",
                ".skill { color: #00bfff; font-weight: bold; }",
                ".missing { color: #ff5555; font-style: italic; font-size: 12px; }",
                "</style></head><body>",
                "<h1>CS2 Account Stats</h1>"
            ]
            i = 1
            accounts = self.accountsManager.selected_accounts
            for acc in accounts:
                self._logManager.add_log(f"Collecting stats ({i}/{len(accounts)})")
                steam = SteamLoginSession(acc.login, acc.password, acc.shared_secret)
                level_html = self._fetch_html(steam, "gcpd/730")
                rank_match = re.search(r'CS:GO Profile Rank:\s*([^\n<]+)', level_html) if level_html else None
                xp_match = re.search(r'Experience points earned towards next rank:\s*([^\n<]+)',
                                     level_html) if level_html else None
                level = rank_match.group(1).strip() if rank_match else "N/A"
                xp = xp_match.group(1).strip() if xp_match else "N/A"

                # Получаем статистику матчей с другой страницы
                stats_html = self._fetch_html(steam)  # статистика матчей

                html_parts.append("<div class='account-card'>")
                html_parts.append(
                    f"<div class='account-header'><div class='account-title'>{acc.login}</div><div class='account-level'>Level: {level} | XP: {xp}</div></div>")

                # --- Premier ---
                premier_match = re.search(r'<td>Premier</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                                          stats_html) if stats_html else None
                html_parts.append(
                    "<table><tr><th colspan='4'>Premier</th></tr><tr><th>W</th><th>T</th><th>L</th><th>R</th></tr>")
                if premier_match:
                    wins, ties, losses = int(premier_match.group(1)), int(premier_match.group(2)), int(
                        premier_match.group(3))
                    skill = premier_match.group(4).strip()
                    skill = int(skill) if skill.isdigit() else -1
                    html_parts.append(
                        f"<tr><td class='wins'>{wins}</td><td class='ties'>{ties}</td><td class='losses'>{losses}</td><td class='skill'>{skill}</td></tr>")
                else:
                    html_parts.append("<tr><td colspan='4' class='missing'>Статистика не найдена</td></tr>")
                html_parts.append("</table>")

                # --- Wingman ---
                wingman_match = re.search(r'<td>Wingman</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                                          stats_html) if stats_html else None
                html_parts.append(
                    "<table><tr><th colspan='4'>Wingman</th></tr><tr><th>W</th><th>T</th><th>L</th><th>R</th></tr>")
                if wingman_match:
                    wins, ties, losses = int(wingman_match.group(1)), int(wingman_match.group(2)), int(
                        wingman_match.group(3))
                    skill = wingman_match.group(4).strip()
                    skill = int(skill) if skill.isdigit() else -1
                    html_parts.append(
                        f"<tr><td class='wins'>{wins}</td><td class='ties'>{ties}</td><td class='losses'>{losses}</td><td class='skill'>{skill}</td></tr>")
                else:
                    html_parts.append("<tr><td colspan='4' class='missing'>Статистика не найдена</td></tr>")
                html_parts.append("</table>")

                # --- Map Stats ---
                table_match = re.search(
                    r'<table class="generic_kv_table"><tr>\s*<th>Matchmaking Mode</th>\s*<th>Map</th>.*?</table>',
                    stats_html, re.DOTALL) if stats_html else None
                html_parts.append("<table><tr><th>Map</th><th>W</th><th>T</th><th>L</th><th>R</th></tr>")
                if table_match:
                    table_html = table_match.group(0)
                    rows = re.findall(
                        r'<tr>\s*<td>([^<]+)</td><td>([^<]+)</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td><td>([^<]*)</td>',
                        table_html)
                    if rows:
                        for mode, map_name, wins, ties, losses, skill in rows:
                            wins, ties, losses = int(wins), int(ties), int(losses)
                            skill = skill.strip()
                            skill = int(skill) if skill.isdigit() else -1
                            html_parts.append(
                                f"<tr><td>{map_name}</td><td class='wins'>{wins}</td><td class='ties'>{ties}</td><td class='losses'>{losses}</td><td class='skill'>{skill}</td></tr>")
                    else:
                        html_parts.append("<tr><td colspan='5' class='missing'>Статистика не найдена</td></tr>")
                else:
                    html_parts.append("<tr><td colspan='5' class='missing'>Статистика не найдена</td></tr>")
                html_parts.append("</table>")

                html_parts.append("</div>")  # конец карточки
                i+=1

            html_parts.append("</body></html>")

            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(html_parts))

            self._logManager.add_log(f"✅ Stats saved to {filename}")

        self._run_stat_with_lock(worker)



