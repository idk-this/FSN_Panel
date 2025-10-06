import base64
import json
import re
import time
import rsa
import requests
import hmac
import struct
import hashlib
import os
from requests.cookies import RequestsCookieJar

class SteamLoginSession:
    def __init__(self, username: str = None, password: str = None, shared_secret: str = None):
        self.username = username
        self.password = password
        self.shared_secret = shared_secret
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/118.0.0.0 Safari/537.36',
            'Referer': 'https://steamcommunity.com/login',
            'Origin': 'https://steamcommunity.com'
        })

        self.client_id = None
        self.steamid = None
        self.request_id = None
        self.refresh_token = None
        self.session_id = None

    # ======================= LOGIN =======================

    def login(self):
        self._init_sessionid()
        self._begin_auth_session()
        self._update_steam_guard()
        self._poll_for_tokens()
        self._finalize_login()

    # ======================= SESSION SAVE/LOAD =======================

    def save_session(self, file_path: str):
        """
        Save session for self.username. Cookies are saved as a list of cookies
        with domain/path so they can be restored exactly.
        """
        if not self.username:
            raise RuntimeError("Cannot save session without username")

        # collect cookies as list of dicts preserving domain/path/expires/secure
        cookies_list = []
        for c in self.session.cookies:
            cookies_list.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires,
                "secure": bool(c.secure),
            })

        # load existing file (if any)
        data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}

        data[self.username] = {
            "steamid": self.steamid,
            "cookies": cookies_list
        }

        # write atomically
        tmp = file_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, file_path)

    def load_session(self, file_path: str) -> bool:
        """
        Load session for self.username.
        Returns True if the restored session appears logged in.
        Backwards-compatible: supports old format where `cookies` was a dict {name: value}.
        """
        if not self.username:
            raise RuntimeError("Cannot load session without username")

        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            return False

        if self.username not in data:
            return False

        entry = data[self.username]
        cookies = entry.get("cookies")

        # If cookies saved as dict (old behaviour), fallback
        if isinstance(cookies, dict):
            # old format: name -> value. Set them on common steam domains for compatibility.
            for name, value in cookies.items():
                for domain in (".steamcommunity.com", ".steampowered.com", "store.steampowered.com"):
                    try:
                        self.session.cookies.set(name, value, domain=domain, path="/")
                    except Exception:
                        # best-effort, ignore malformed entries
                        pass
        elif isinstance(cookies, list):
            jar = RequestsCookieJar()
            for c in cookies:
                try:
                    name = c.get("name")
                    value = c.get("value")
                    domain = c.get("domain") or ".steamcommunity.com"
                    path = c.get("path") or "/"
                    # preserve domain/path using RequestsCookieJar.set
                    jar.set(name, value, domain=domain, path=path)
                except Exception:
                    # ignore bad cookie entries
                    continue
            # merge jar into session
            self.session.cookies.update(jar)
        else:
            # unknown cookie format
            return False

        # restore steamid if saved
        saved_steamid = entry.get("steamid")
        self.steamid = saved_steamid or None

        # ensure we have sessionid value (update self.session_id if present in cookies)
        for cookie in self.session.cookies:
            if cookie.name == "sessionid":
                self.session_id = cookie.value
                break

        # if steamid is missing, try to discover it from the session
        if not self.steamid:
            self.steamid = self._discover_steamid()

        # finally validate
        return self.is_logged_in()

    def _discover_steamid(self):
        """
        Try to obtain steamid from a logged-in session by hitting /my/home and
        checking the final URL (e.g. /profiles/<steamid>/home).
        Returns steamid as string or None.
        """
        try:
            r = self.session.get("https://steamcommunity.com/my/home", allow_redirects=True, timeout=10)
            final_url = r.url or ""
            m = re.search(r"/profiles/(\d+)", final_url)
            if m:
                return m.group(1)
        except Exception:
            pass
        # fallback: maybe we can parse the page content for steamid embedded in HTML (rare)
        try:
            r = self.session.get("https://steamcommunity.com/", timeout=10)
            m2 = re.search(r"g_steamID = \"(\d+)\"", r.text)
            if m2:
                return m2.group(1)
        except Exception:
            pass
        return None
    # ======================= PRIVATE =======================

    def _init_sessionid(self):
        r = self.session.get("https://steamcommunity.com/")
        cookies = self.session.cookies.get_dict()
        self.session_id = cookies.get('sessionid')
        if not self.session_id:
            raise RuntimeError("Не удалось получить sessionid cookie.")

    def _get_rsa_key(self):
        r = self.session.get(
            f"https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/?account_name={self.username}"
        )
        js = r.json()["response"]
        mod = int(js["publickey_mod"], 16)
        exp = int(js["publickey_exp"], 16)
        ts = js["timestamp"]

        key = rsa.PublicKey(mod, exp)
        encrypted_password = base64.b64encode(
            rsa.encrypt(self.password.encode('utf-8'), key)
        ).decode('utf-8')
        return encrypted_password, ts

    def _begin_auth_session(self):
        enc_password, rsa_timestamp = self._get_rsa_key()

        data = {
            'account_name': self.username,
            'encrypted_password': enc_password,
            'encryption_timestamp': rsa_timestamp,
            'persistence': '1',
            'platform_type': 'WebBrowser',
        }

        r = self.session.post(
            "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1",
            data=data
        )
        if r.status_code != 200:
            raise RuntimeError(f"Ошибка BeginAuthSession: {r.status_code}")

        resp = r.json().get("response", {})
        self.client_id = resp.get("client_id")
        self.steamid = resp.get("steamid")
        self.request_id = resp.get("request_id")

        if not self.client_id or not self.steamid or not self.request_id:
            raise RuntimeError("Не удалось получить client_id/steamid/request_id.")

    def _generate_steam_guard_code(self):
        shared_secret_bytes = base64.b64decode(self.shared_secret)
        time_buffer = struct.pack(">Q", int(time.time()) // 30)
        hmac_hash = hmac.new(shared_secret_bytes, time_buffer, hashlib.sha1).digest()
        start = hmac_hash[19] & 0x0F
        full_code = struct.unpack(">I", hmac_hash[start:start+4])[0] & 0x7FFFFFFF
        chars = '23456789BCDFGHJKMNPQRTVWXY'
        code = ''
        for _ in range(5):
            code += chars[full_code % len(chars)]
            full_code //= len(chars)
        return code

    def _update_steam_guard(self):
        code = self._generate_steam_guard_code()
        data = {
            'client_id': self.client_id,
            'steamid': self.steamid,
            'code_type': 3,
            'code': code
        }
        r = self.session.post(
            "https://api.steampowered.com/IAuthenticationService/UpdateAuthSessionWithSteamGuardCode/v1/",
            data=data
        )
        if r.status_code != 200:
            raise RuntimeError(f"Steam Guard update failed: {r.status_code}")

    def _poll_for_tokens(self):
        for _ in range(30):
            r = self.session.post(
                "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/",
                data={'client_id': self.client_id, 'request_id': self.request_id}
            )
            if r.status_code != 200:
                time.sleep(1)
                continue

            resp = r.json().get("response", {})
            if "refresh_token" in resp:
                self.refresh_token = resp["refresh_token"]
                return
            time.sleep(1)
        raise TimeoutError("Не удалось получить refresh_token за отведённое время.")

    def _finalize_login(self):
        data = {
            'nonce': self.refresh_token,
            'sessionid': self.session_id,
            'redir': 'https://steamcommunity.com/login/home/?goto='
        }
        r = self.session.post("https://login.steampowered.com/jwt/finalizelogin", data=data)
        if r.status_code == 403:
            raise RuntimeError("403 при финализации входа. Проверьте правильность токенов.")
        if r.status_code != 200:
            raise RuntimeError(f"Ошибка finalizelogin: {r.status_code}")

        resp = r.json()
        transfer_info = resp.get("transfer_info", [])
        for item in transfer_info:
            params = item.get("params", {})
            self.session.post(item["url"], data={
                'nonce': params.get('nonce'),
                'auth': params.get('auth'),
                'steamID': self.steamid
            })

    def is_logged_in(self) -> bool:
        """
        Return True if the current session is logged in.
        If steamid is known, check the profile page. Otherwise, try to discover it.
        """
        try:
            if self.steamid:
                r = self.session.get(f"https://steamcommunity.com/profiles/{self.steamid}/home", timeout=10)
                return r.status_code == 200
            # try to discover steamid and then validate
            discovered = self._discover_steamid()
            if discovered:
                self.steamid = discovered
                return True
            return False
        except Exception:
            return False
