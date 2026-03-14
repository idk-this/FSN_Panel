# FSN Panel

**FSN Panel** is a panel for launching multiple CS2 accounts simultaneously, managing their windows, and collecting lobbies.

Created in 12 hours using Chat GPT.

---
> ⚠️ WARNING: If you're worried about a stealer, use the source code directly. I'm not responsible for your accounts, and if you're so stupid that all your accounts were stolen, don't blame me. All source code is open and publicly available.
---

## 📌 Requirements

| Requirement   | Note                      |
| ------------- | ------------------------- |
| Python 3.11   | Required to run the panel |
| Avast Sandbox | Avast Premium required    |
| Steam         | Latest version            |
| CS2           | Latest version            |

> ⚠️ Important: Make sure `steam.exe` always runs as administrator for proper functionality.

---

## 🛠 Installation

1. Clone the repository:

```bash
git clone https://github.com/idk-this/FSN_Panel
cd FSN_Panel
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the panel:

```bash
python main.py
```

---
## 🛠 Troubleshooting

### Status colors change from yellow to white immediately
**Issue:** When launching, account indicators briefly turn yellow and then revert to white without starting the game.

**Solution:** Navigate to your Steam installation directory and completely delete the `userdata` folder.

### Accounts or games fail to launch/accept
**Issue:** The panel does not trigger the game client, or accounts do not start at all.
**Solution:** The panel must be run with **Administrator privileges**.

If you are running from source:
1. Open **Command Prompt (CMD)** as **Administrator**.
2. Navigate to your project directory:
   ```bash
   cd C:/path/to/FSN_Panel
   ```
3. Run the script:
   ```bash
   python main.py
    ```
---
## ⚙ Account Setup
1. To add accounts, place your `maFiles` (optional) in the `mafiles` folder.
2. Add logins and passwords in the `logpass.txt` file in the format:

```
login:password
```

---

## 🖼 Example Screenshot

<img width="1642" height="909" alt="image" src="https://github.com/user-attachments/assets/48aadeae-7365-44fb-9824-a69dc730a6da" />


---

## 🚀 Usage

* The panel allows launching multiple CS2 accounts simultaneously.
* Automatically arranges windows and collects lobbies.
* Works with accounts listed in `logpass.txt` and `maFiles`.
