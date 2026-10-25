# 🤖 Nexus Desktop Assistant

AI-powered desktop controller with voice commands, file CRUD,
volume/brightness control, web automation — in a full Electron window.

---

## 📁 Project Structure

```
desktop-assistant/
├── main.js                  ← Electron entry (opens window, starts Python)
├── preload.js               ← Electron IPC bridge
├── index.html               ← Full chat UI (ChatGPT-style)
├── package.json             ← npm / Electron config
├── setup_and_run.bat        ← ONE-CLICK setup for Windows
├── setup_and_run.sh         ← ONE-CLICK setup for Mac/Linux
└── backend/
    ├── app.py               ← Flask backend (all commands)
    └── requirements.txt     ← Python packages
```

---

## ⚙️ How to Run  (3 simple steps)

### ✅ Requirements
- Python 3.8+   →  https://python.org/downloads
- Node.js 18+   →  https://nodejs.org

---

### Windows (easiest)
```
Double-click setup_and_run.bat
```

### Mac / Linux
```bash
chmod +x setup_and_run.sh
./setup_and_run.sh
```

### Manual steps (any OS)
```bash
# 1. Install Python deps
pip install flask flask-cors pycaw comtypes psutil

# 2. Install Electron
npm install

# 3. Launch
npm start
```

---

## 💬 Commands Reference

### System
| Command                  | Action                    |
|--------------------------|---------------------------|
| open chrome / notepad    | Opens the app             |
| volume 70                | Sets volume to 70%        |
| volume up / volume down  | Increase / decrease       |
| mute / unmute            | Toggle mute               |
| brightness 80            | Sets brightness to 80%    |
| screenshot               | Opens snipping tool       |
| shutdown / restart       | System commands           |

### Web
| Command                        | Action               |
|--------------------------------|----------------------|
| search python tutorial         | Google search        |
| youtube lo-fi music            | YouTube search       |
| weather in Chennai             | Live weather         |
| navigate to Chennai airport    | Google Maps          |
| open gmail / open whatsapp     | Open web apps        |
| news                           | Google News          |

### Files (use the 📁 File Manager tab)
- 📂 Open any folder
- ➕ Create new file
- ✏️ Edit file in built-in editor
- 💾 Save changes
- 🗑 Delete files

---

## 🎙 Voice Commands
Click the 🎙 mic button and speak — works for ANY command above.

---

## ❌ No API Keys Needed
Everything runs locally. Python + Electron only.
