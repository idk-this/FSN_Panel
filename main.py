import ctypes
import sys
import subprocess
from ui.app import App

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if not is_admin():
        args = " ".join(sys.argv)
        subprocess.run(["powershell", "Start-Process", f"'{sys.executable}'", "-ArgumentList", f"'{args}'", "-Verb", "RunAs"])
        sys.exit()

    app = App()
    app.mainloop()