# FSN Panel

**FSN Panel** is a panel for launching multiple CS2 accounts simultaneously, managing their windows, and collecting lobbies.

Created in 12 hours using Chat GPT.

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
