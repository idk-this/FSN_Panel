import winreg

class WinregHelper:
    @staticmethod
    def set_value(path, name, value, value_type=winreg.REG_DWORD, root=winreg.HKEY_CURRENT_USER):
        key = winreg.CreateKey(root, path)
        winreg.SetValueEx(key, name, 0, value_type, value)
        winreg.CloseKey(key)

    @staticmethod
    def get_value(path, name, root=winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, path) as key:
                return winreg.QueryValueEx(key, name)[0]
        except FileNotFoundError:
            return None

    @staticmethod
    def delete_value(path, name, root=winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass

    @staticmethod
    def delete_key(path, root=winreg.HKEY_CURRENT_USER):
        def _delete_recursively(root_key, sub_key):
            try:
                with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                            _delete_recursively(key, sub)
                        except OSError:
                            break
                        i += 1
                winreg.DeleteKey(root_key, sub_key)
            except FileNotFoundError:
                pass

        _delete_recursively(root, path)
