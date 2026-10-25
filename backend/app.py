# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, platform, webbrowser, os, re, shutil, datetime, socket

app  = Flask(__name__)
CORS(app)
OS   = platform.system()

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

# ── VOLUME ─────────────────────────────────────────────────────
def set_volume(level):
    level = max(0, min(100, int(level)))
    if OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            import ctypes
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        except Exception:
            # Fallback: use nircmd or powershell media key simulation
            try:
                ps = f"$obj = New-Object -ComObject WScript.Shell; " \
                     f"1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; " \
                     f"$steps = [int]({level} / 2); " \
                     f"1..$steps | ForEach-Object {{ $obj.SendKeys([char]175) }}"
                subprocess.Popen(
                    ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e2:
                return f"Volume error: {e2}"
    elif OS == "Darwin":
        os.system(f"osascript -e 'set volume output volume {level}'")
    else:
        os.system(f"amixer -D pulse sset Master {level}% 2>/dev/null || amixer sset Master {level}%")
    return f"Volume set to {level}%"

def mute_toggle():
    if OS == "Windows":
        ps = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
        subprocess.Popen(["powershell","-NonInteractive","-WindowStyle","Hidden","-Command",ps], creationflags=subprocess.CREATE_NO_WINDOW)
    elif OS == "Darwin":
        os.system("osascript -e 'set volume output muted (not (output muted of (get volume settings)))'")
    else:
        os.system("amixer -D pulse set Master toggle")
    return "Toggled mute"

# ── BRIGHTNESS ─────────────────────────────────────────────────
def set_brightness(level):
    level = max(0, min(100, int(level)))
    if OS == "Windows":
        ps = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
        subprocess.Popen(["powershell","-NonInteractive","-WindowStyle","Hidden","-Command",ps], creationflags=subprocess.CREATE_NO_WINDOW)
    elif OS == "Darwin":
        os.system(f"osascript -e 'tell application \"System Events\" to set brightness of display 1 to {level/100:.2f}'")
    else:
        os.system(f"brightnessctl set {level}% 2>/dev/null || true")
    return f"Brightness set to {level}%"

# ── OPEN APP ───────────────────────────────────────────────────
APP_MAP = {
    "notepad":      ("notepad",           "open -a TextEdit",              "gedit"),
    "calculator":   ("calc",              "open -a Calculator",            "gnome-calculator"),
    "paint":        ("mspaint",           "open -a Preview",               "gimp"),
    "chrome":       ("start chrome",      "open -a 'Google Chrome'",       "google-chrome"),
    "firefox":      ("start firefox",     "open -a Firefox",               "firefox"),
    "edge":         ("start msedge",      "open -a 'Microsoft Edge'",      "microsoft-edge"),
    "word":         ("start winword",     "open -a 'Microsoft Word'",      "libreoffice --writer"),
    "excel":        ("start excel",       "open -a 'Microsoft Excel'",     "libreoffice --calc"),
    "powerpoint":   ("start powerpnt",    "open -a 'Microsoft PowerPoint'","libreoffice --impress"),
    "explorer":     ("explorer",          "open -a Finder",                "nautilus"),
    "file explorer":("explorer",          "open -a Finder",                "nautilus"),
    "terminal":     ("start cmd",         "open -a Terminal",              "gnome-terminal"),
    "cmd":          ("start cmd",         "open -a Terminal",              "gnome-terminal"),
    "task manager": ("taskmgr",           "",                              "gnome-system-monitor"),
    "vlc":          ("start vlc",         "open -a VLC",                   "vlc"),
    "vscode":       ("start code",        "open -a 'Visual Studio Code'",  "code"),
    "vs code":      ("start code",        "open -a 'Visual Studio Code'",  "code"),
    "spotify":      ("start spotify",     "open -a Spotify",               "spotify"),
    "discord":      ("start discord",     "open -a Discord",               "discord"),
    "settings":     ("start ms-settings:","open -a 'System Preferences'",  "gnome-control-center"),
    "zoom":         ("start zoom",        "open -a zoom.us",               "zoom"),
    "teams":        ("start msteams",     "open -a 'Microsoft Teams'",     "teams"),
}

def open_app(name):
    name = name.lower().strip()
    idx  = {"Windows":0,"Darwin":1}.get(OS,2)
    if name in APP_MAP:
        cmd = APP_MAP[name][idx]
        if cmd:
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if OS=="Windows" else 0)
            return f"Opening {name}..."
    if OS=="Windows":
        subprocess.Popen(f"start {name}", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    elif OS=="Darwin":
        os.system(f"open -a '{name}'")
    else:
        subprocess.Popen(name, shell=True)
    return f"Attempting to open {name}..."

# ── FILE HELPERS ───────────────────────────────────────────────
def resolve_path(raw):
    raw = raw.strip().strip('"').strip("'")
    locs = {
        "desktop":   os.path.join(os.path.expanduser("~"), "Desktop"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "pictures":  os.path.join(os.path.expanduser("~"), "Pictures"),
        "music":     os.path.join(os.path.expanduser("~"), "Music"),
        "videos":    os.path.join(os.path.expanduser("~"), "Videos"),
    }
    for kw, folder in locs.items():
        if kw in raw.lower():
            fname = re.sub(rf'.*{kw}[/\\ ]*', '', raw, flags=re.I).strip()
            return os.path.join(folder, fname) if fname else folder
    return raw if os.path.isabs(raw) else os.path.join(DESKTOP, raw)

def cmd_create_file(text):
    is_folder = bool(re.search(r'\b(folder|directory|dir)\b', text, re.I))
    content = ""
    cm = re.search(r'\bwith\s+content\s+(.+)', text, re.I)
    if cm:
        content = cm.group(1).strip()
        text = text[:cm.start()].strip()

    patterns = [
        r'(?:create|make|new)\s+(?:a\s+)?(?:file|folder|directory|dir)\s+(?:named\s+|called\s+)?([^\s]+(?:\.[a-zA-Z0-9]+)?)\s+(?:in|on|at|inside)\s+(.+)',
        r'(?:create|make|new)\s+(?:a\s+)?(?:file|folder|directory|dir)\s+(?:named\s+|called\s+)?([^\s]+(?:\.[a-zA-Z0-9]+)?)$',
        r'(?:create|make|new)\s+(?:a\s+)?([^\s]+\.[a-zA-Z0-9]+)\s+(?:in|on|at|inside)\s+(.+)',
        r'(?:create|make|new)\s+(?:a\s+)?([^\s]+\.[a-zA-Z0-9]+)$',
    ]

    fname = None
    loc   = "desktop"

    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            fname = m.group(1).strip()
            loc   = m.group(2).strip() if m.lastindex >= 2 and m.group(2) else "desktop"
            break

    if not fname:
        return "Could not understand. Try: create file notes.txt in desktop"

    fname = re.sub(r'\s+(in|on|at|inside)\s+.*$', '', fname, flags=re.I).strip()
    folder = resolve_path(loc)
    full   = os.path.join(folder, fname)

    try:
        os.makedirs(folder, exist_ok=True)
        if is_folder:
            os.makedirs(full, exist_ok=True)
            return f"Folder created: {full}"
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created: {full}"
    except Exception as e:
        return f"Error creating file: {e}"

def cmd_delete_file(text):
    m = re.search(r'(?:delete|remove)\s+(?:file\s+|folder\s+)?(.+)', text, re.I)
    if not m: return "Say: delete file notes.txt"
    path = resolve_path(m.group(1))
    try:
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        return f"Deleted: {path}"
    except Exception as e:
        return f"Error: {e}"

def cmd_rename_file(text):
    m = re.search(r'rename\s+(.+?)\s+to\s+(.+)', text, re.I)
    if not m: return "Say: rename old.txt to new.txt"
    old = resolve_path(m.group(1))
    new = os.path.join(os.path.dirname(old), m.group(2).strip())
    try:
        os.rename(old, new)
        return f"Renamed to: {new}"
    except Exception as e:
        return f"Error: {e}"

def cmd_open_file(text):
    m = re.search(r'open\s+file\s+(.+)', text, re.I)
    if not m: return "Say: open file notes.txt"
    path = resolve_path(m.group(1))
    if OS=="Windows": os.startfile(path)
    elif OS=="Darwin": os.system(f"open '{path}'")
    else: os.system(f"xdg-open '{path}'")
    return f"Opening: {path}"

def cmd_list_files(text):
    m = re.search(r'(?:list|show)\s+files\s+(?:in\s+|on\s+)?(.+)', text, re.I)
    folder = resolve_path(m.group(1)) if m else DESKTOP
    try:
        items   = os.listdir(folder)
        files   = [i for i in items if os.path.isfile(os.path.join(folder,i))]
        folders = [i for i in items if os.path.isdir(os.path.join(folder,i))]
        out = f"Contents of {folder}:\n"
        if folders: out += "Folders: " + ", ".join(folders[:10]) + "\n"
        if files:   out += "Files: "   + ", ".join(files[:15])
        return out or "Empty folder"
    except Exception as e:
        return f"Error: {e}"

# ── SYSTEM INFO ────────────────────────────────────────────────
def get_system_info():
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return (f"CPU: {cpu}%  |  RAM: {ram.percent}% ({ram.used//1024//1024}MB/{ram.total//1024//1024}MB)  |  Disk: {disk.percent}% used")
    except:
        return f"OS: {OS} | Host: {socket.gethostname()}"

def get_battery():
    try:
        import psutil
        b = psutil.sensors_battery()
        if b: return f"Battery: {b.percent:.0f}% ({'Charging' if b.power_plugged else 'Discharging'})"
        return "No battery (desktop PC)"
    except: return "Battery info unavailable"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close()
        return f"Local IP: {ip}  |  Hostname: {socket.gethostname()}"
    except: return "Could not get IP"

def get_time():
    now = datetime.datetime.now()
    return f"Time: {now.strftime('%I:%M %p')}  |  Date: {now.strftime('%A, %d %B %Y')}"

def get_running_apps():
    try:
        import psutil
        procs = sorted(set(p.name() for p in psutil.process_iter(['name']) if p.info['name']))
        visible = [p for p in procs if not p.startswith('svchost') and '.' in p][:25]
        return "Running apps:\n" + "\n".join(f"  - {p}" for p in visible)
    except: return "Could not list processes"

def is_app_running(name):
    try:
        import psutil
        matches = [p.name() for p in psutil.process_iter(['name']) if name.lower() in p.info['name'].lower()]
        if matches:
            return f"YES, {matches[0]} is currently running."
        return f"NO, {name} is not running."
    except Exception as e: return f"Error: {e}"

def kill_app(name):
    name = name.strip()
    name = re.sub(r'\b(app|application|process|the|program)\b','', name, flags=re.I).strip()
    try:
        import psutil
        killed = []
        for p in psutil.process_iter(['name']):
            if name.lower() in p.info['name'].lower():
                p.kill()
                killed.append(p.info['name'])
        if killed:
            return f"Closed: {', '.join(set(killed))}"
        return f"'{name}' is not running."
    except Exception as e: return f"Error: {e}"

def cancel_shutdown():
    if OS == "Windows":
        subprocess.Popen("shutdown /a", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Shutdown cancelled!"
    return "Cancel shutdown only supported on Windows"

def get_wifi_status():
    try:
        if OS == "Windows":
            out = subprocess.check_output("netsh wlan show interfaces", shell=True, encoding='utf-8', errors='replace')
            ssid = re.search(r'SSID\s*:\s*(.+)', out)
            state = re.search(r'State\s*:\s*(.+)', out)
            sig = re.search(r'Signal\s*:\s*(.+)', out)
            result = []
            if state: result.append(f"Status: {state.group(1).strip()}")
            if ssid:  result.append(f"Network: {ssid.group(1).strip()}")
            if sig:   result.append(f"Signal: {sig.group(1).strip()}")
            return "  |  ".join(result) if result else "WiFi info not available"
        return get_ip()
    except: return get_ip()

def get_disk_info():
    try:
        import psutil
        parts = psutil.disk_partitions()
        result = []
        for p in parts:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                result.append(f"{p.device}: {usage.percent}% used ({usage.used//1024//1024//1024}GB / {usage.total//1024//1024//1024}GB)")
            except: pass
        return "\n".join(result) if result else "No disk info"
    except: return "Disk info unavailable"

def open_folder(name):
    locs = {
        "desktop":   os.path.join(os.path.expanduser("~"), "Desktop"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "pictures":  os.path.join(os.path.expanduser("~"), "Pictures"),
        "music":     os.path.join(os.path.expanduser("~"), "Music"),
        "videos":    os.path.join(os.path.expanduser("~"), "Videos"),
        "c drive":   "C:\\",  "c:": "C:\\",
    }
    path = locs.get(name.lower(), name)
    if OS == "Windows":
        subprocess.Popen(f'explorer "{path}"', shell=True)
    elif OS == "Darwin":
        os.system(f"open '{path}'")
    else:
        os.system(f"xdg-open '{path}'")
    return f"Opened folder: {path}"

def increase_volume_by(amount=10):
    if OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            import ctypes
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = min(100, current + amount)
            volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
            return f"Volume increased to {int(new_level)}%"
        except Exception:
            try:
                steps = int(amount / 2)
                ps = f"$obj = New-Object -ComObject WScript.Shell; 1..{steps} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
                subprocess.Popen(["powershell","-NonInteractive","-WindowStyle","Hidden","-Command",ps], creationflags=subprocess.CREATE_NO_WINDOW)
                return f"Volume increased by {amount}%"
            except Exception as e2:
                return f"Volume error: {e2}"
    return set_volume(min(100, 50 + amount))

def decrease_volume_by(amount=10):
    if OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            import ctypes
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = max(0, current - amount)
            volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
            return f"Volume decreased to {int(new_level)}%"
        except Exception:
            try:
                steps = int(amount / 2)
                ps = f"$obj = New-Object -ComObject WScript.Shell; 1..{steps} | ForEach-Object {{ $obj.SendKeys([char]174) }}"
                subprocess.Popen(["powershell","-NonInteractive","-WindowStyle","Hidden","-Command",ps], creationflags=subprocess.CREATE_NO_WINDOW)
                return f"Volume decreased by {amount}%"
            except Exception as e2:
                return f"Volume error: {e2}"
    return set_volume(max(0, 50 - amount))

def lock_screen():
    if OS=="Windows": subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
    elif OS=="Darwin": os.system("pmset displaysleepnow")
    else: os.system("gnome-screensaver-command -l")
    return "Screen locked"

def sleep_pc():
    if OS=="Windows": subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
    elif OS=="Darwin": os.system("pmset sleepnow")
    else: os.system("systemctl suspend")
    return "Going to sleep..."

# ── MAIN PARSER ────────────────────────────────────────────────
def parse_command(text):
    t = text.lower().strip()

    # ── MULTIPLE COMMANDS (split by |) ──────────────────────────
    if '|' in text:
        parts = [p.strip() for p in text.split('|') if p.strip()]
        results = [parse_command(p) for p in parts]
        return '  |  '.join(results)

    # ── VOLUME ─────────────────────────────────────────────────
    vm = re.search(r'\b(?:volume|sound|audio|vol)\b\s*(?:to|at|=|set\s*to)?\s*(\d+)', t)
    if vm: return set_volume(vm.group(1))
    vm2 = re.search(r'\bset\s+(?:volume|sound|audio)\s+(?:to\s+)?(\d+)', t)
    if vm2: return set_volume(vm2.group(1))
    if re.search(r'\b(volume up|sound up|louder|increase volume|increase sound|raise volume)\b', t): return increase_volume_by(15)
    if re.search(r'\b(volume down|sound down|quieter|decrease volume|lower volume|reduce volume)\b', t): return decrease_volume_by(15)
    if re.search(r'\b(mute|unmute|silence)\b', t): return mute_toggle()

    # ── BRIGHTNESS ─────────────────────────────────────────────
    bm = re.search(r'\bbrightness\b\s*(?:to|at|=)?\s*(\d+)', t)
    if bm: return set_brightness(bm.group(1))
    if re.search(r'\b(brightness up|brighter|increase brightness|raise brightness)\b', t): return set_brightness(80)
    if re.search(r'\b(brightness down|dimmer|dim|decrease brightness|lower brightness)\b', t): return set_brightness(30)

    # ── SCREENSHOT ─────────────────────────────────────────────
    if re.search(r'\b(screenshot|screen capture|print screen)\b', t):
        if OS == "Windows":
            try:
                from PIL import ImageGrab
                import datetime
                fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                path  = os.path.join(os.path.expanduser("~"), "Desktop", fname)
                img   = ImageGrab.grab()
                img.save(path)
                # Open Desktop folder so user can see the file
                subprocess.Popen(f'explorer /select,"{path}"', shell=True)
                return f"Screenshot saved to Desktop: {fname}"
            except ImportError:
                subprocess.Popen("snippingtool", shell=True)
                return "Pillow not installed — opened Snipping Tool instead. Run: pip install pillow"
        elif OS == "Darwin":
            os.system("screencapture -i ~/Desktop/screenshot.png")
        else:
            os.system("gnome-screenshot -i 2>/dev/null || scrot ~/Desktop/screenshot.png")
        return "Screenshot saved to Desktop!"

    # ── FILE OPERATIONS ─────────────────────────────────────────
    if re.search(r'\b(create|make|new)\b.+\b(file|folder|directory)\b', t) or \
       re.search(r'\b(create|make|new)\s+(?:a\s+)?[\w]+\.[a-zA-Z0-9]+', t) or \
       re.search(r'\b(create|make)\s+(?:a\s+)?folder\b', t):
        return cmd_create_file(text)
    if re.search(r'\b(delete|remove)\b.+\b(file|folder)\b', t):
        return cmd_delete_file(text)
    if re.search(r'\brename\b', t): return cmd_rename_file(text)
    if re.search(r'\bopen\s+file\b', t): return cmd_open_file(text)
    if re.search(r'\b(list|show)\s+files\b', t): return cmd_list_files(text)

    # ── OPEN FOLDER ─────────────────────────────────────────────
    if re.search(r'\bopen\s+(desktop|documents|downloads|pictures|music|videos|c drive|c:)\b', t):
        m = re.search(r'\bopen\s+(.+)', t)
        if m: return open_folder(m.group(1).strip())

    # ── CHECK IF APP IS RUNNING ─────────────────────────────────
    if re.search(r'\b(is|check if|check whether).+\b(running|open|active|on)\b', t) or \
       re.search(r'\b(running|open|active)\b.+\?', t):
        m = re.search(r'\bis\s+(.+?)\s+(running|open|active)\b', t) or \
            re.search(r'\bcheck\s+(?:if\s+)?(.+?)\s+is\s+(running|open|active)\b', t)
        if m: return is_app_running(m.group(1).strip())

    # ── SYSTEM INFO ─────────────────────────────────────────────
    if re.search(r'\b(system info|sysinfo|cpu|ram|memory usage|disk usage)\b', t): return get_system_info()
    if re.search(r'\b(battery|battery level|charge|charging)\b', t): return get_battery()
    if re.search(r'\b(ip address|my ip|local ip|network info|wifi status|wifi info|internet)\b', t): return get_wifi_status()
    if re.search(r'\b(disk|storage|hard drive|drive space)\b', t): return get_disk_info()
    if re.search(r'\b(time|date|clock|what time|today)\b', t): return get_time()
    if re.search(r'\b(running apps|list apps|show apps|what is running|active apps|processes)\b', t): return get_running_apps()

    # ── CLOSE / KILL APP ────────────────────────────────────────
    km = re.search(r'\b(kill|close|stop|end|force close|force quit|terminate)\s+(.+)', t)
    if km:
        app_name = km.group(2).strip()
        if not re.search(r'\b(tab|window|browser tab)\b', app_name):
            return kill_app(app_name)

    # ── POWER / SYSTEM ACTIONS ──────────────────────────────────
    if re.search(r'\b(cancel shutdown|abort shutdown|stop shutdown|undo shutdown)\b', t):
        return cancel_shutdown()
    if re.search(r'\block\s*(screen|pc|computer|laptop|my)?\b', t): return lock_screen()
    if re.search(r'\bsleep\s*(pc|computer|laptop|mode)?\b', t): return sleep_pc()
    if re.search(r'\b(empty recycle|clear trash|empty trash|clear recycle)\b', t):
        if OS=="Windows":
            subprocess.Popen(["powershell","-Command","Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], creationflags=subprocess.CREATE_NO_WINDOW)
            return "Recycle Bin emptied!"
        return "Only supported on Windows"
    if re.search(r'\b(shutdown|shut down|power off|turn off)\b', t):
        if OS=="Windows": subprocess.Popen("shutdown /s /t 10", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else: os.system("sudo shutdown -h +1")
        return "Shutting down in 10 seconds... Type 'cancel shutdown' to abort."
    if re.search(r'\b(restart|reboot|restart pc|restart laptop)\b', t):
        if OS=="Windows": subprocess.Popen("shutdown /r /t 10", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else: os.system("sudo reboot")
        return "Restarting in 10 seconds... Type 'cancel shutdown' to abort."
    if re.search(r'\b(hibernate)\b', t):
        if OS=="Windows": subprocess.Popen("shutdown /h", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Hibernating..."
    if re.search(r'\b(sign out|log out|logoff)\b', t):
        if OS=="Windows": subprocess.Popen("shutdown /l", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Signing out..."

    # ── MESSAGING ───────────────────────────────────────────────
    wm = re.search(r'whatsapp\s+(\+?[\d]+)\s+(.*)', t)
    if wm:
        webbrowser.open(f"https://wa.me/{wm.group(1)}?text={wm.group(2).replace(' ','%20')}")
        return f"Opening WhatsApp to {wm.group(1)}"
    if "whatsapp" in t:
        webbrowser.open("https://web.whatsapp.com"); return "Opening WhatsApp Web"
    if re.search(r'\b(gmail|email|mail)\b', t):
        webbrowser.open("https://mail.google.com"); return "Opening Gmail"

    # ── WEB ─────────────────────────────────────────────────────
    if "youtube" in t:
        q = re.sub(r'.*(youtube)\s*(search)?\s*','',t).strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={q.replace(' ','+')}" if q else "https://www.youtube.com")
        return f"YouTube: {q or 'home'}"
    if re.search(r'\b(maps|navigate|directions)\b', t):
        q = re.sub(r'.*(maps|navigate to|navigate|directions to|directions)\s*','',t).strip()
        webbrowser.open(f"https://maps.google.com/maps?q={q.replace(' ','+')}"); return f"Maps: {q}"
    if "weather" in t:
        q = re.sub(r'.*weather\s*(in|of|at)?\s*','',t).strip() or "today"
        webbrowser.open(f"https://www.google.com/search?q=weather+{q.replace(' ','+')}"); return f"Weather: {q}"
    if "news" in t:
        webbrowser.open("https://news.google.com"); return "Opening Google News"
    if re.search(r'\b(translate|translation)\b', t):
        q = re.sub(r'.*(translate|translation)\s*','',t).strip()
        webbrowser.open(f"https://translate.google.com/?text={q.replace(' ','+')}"); return f"Translating: {q}"
    if re.search(r'\b(spotify|music|play music)\b', t):
        webbrowser.open("https://open.spotify.com"); return "Opening Spotify Web"
    if re.search(r'\b(google drive|gdrive|drive)\b', t):
        webbrowser.open("https://drive.google.com"); return "Opening Google Drive"
    if re.search(r'\b(google meet|meet)\b', t):
        webbrowser.open("https://meet.google.com"); return "Opening Google Meet"
    if re.search(r'\b(calendar|google calendar)\b', t):
        webbrowser.open("https://calendar.google.com"); return "Opening Google Calendar"

    # ── MATH ────────────────────────────────────────────────────
    if re.search(r'\b(calculate|compute|solve|what is)\b', t):
        expr = re.sub(r'.*(calculate|compute|solve|what is)\s*','',t).strip()
        safe = re.sub(r'[^\d\+\-\*/\.\(\) ]','',expr)
        try: return f"Result: {eval(safe)}"
        except: pass

    # ── OPEN WEBSITE ────────────────────────────────────────────
    wm2 = re.search(r'open\s+(www\.\S+|\S+\.(com|org|net|in|io|co|edu)\S*)', t)
    if wm2:
        url = wm2.group(1)
        if not url.startswith("http"): url = "https://" + url
        webbrowser.open(url); return f"Opening {url}"

    # ── OPEN APP ────────────────────────────────────────────────
    am = re.search(r'\b(open|launch|start)\s+(.+)', t)
    if am: return open_app(am.group(2))

    # ── SEARCH FALLBACK ─────────────────────────────────────────
    webbrowser.open(f"https://www.google.com/search?q={text.replace(' ','+')}")
    return f"Searching Google: {text}"

# ── ROUTES ─────────────────────────────────────────────────────
@app.route("/command", methods=["POST"])
def command():
    data = request.json or {}
    q = data.get("query","").strip()
    if not q: return jsonify({"response":"Please enter a command."})
    try: result = parse_command(q)
    except Exception as e: result = f"Error: {e}"
    return jsonify({"response": result})

@app.route("/file/create",  methods=["POST"])
def api_file_create():
    d = request.json or {}
    path, content = d.get("path",""), d.get("content","")
    if not path: return jsonify({"ok":False,"msg":"No path"})
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent: os.makedirs(parent, exist_ok=True)
        with open(path,"w",encoding="utf-8") as f: f.write(content)
        return jsonify({"ok":True,"msg":f"Created: {path}"})
    except Exception as e: return jsonify({"ok":False,"msg":str(e)})

@app.route("/file/read",    methods=["POST"])
def api_file_read():
    d = request.json or {}
    try:
        with open(d.get("path",""),"r",encoding="utf-8") as f: c=f.read()
        return jsonify({"ok":True,"content":c,"msg":f"Read: {d['path']}"})
    except Exception as e: return jsonify({"ok":False,"content":"","msg":str(e)})

@app.route("/file/update",  methods=["POST"])
def api_file_update():
    d = request.json or {}
    try:
        with open(d.get("path",""),"w",encoding="utf-8") as f: f.write(d.get("content",""))
        return jsonify({"ok":True,"msg":f"Updated: {d['path']}"})
    except Exception as e: return jsonify({"ok":False,"msg":str(e)})

@app.route("/file/delete",  methods=["POST"])
def api_file_delete():
    d = request.json or {}
    path = d.get("path","")
    try:
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        return jsonify({"ok":True,"msg":f"Deleted: {path}"})
    except Exception as e: return jsonify({"ok":False,"msg":str(e)})

@app.route("/file/list",    methods=["POST"])
def api_file_list():
    d = request.json or {}
    folder = d.get("path", os.path.expanduser("~"))
    try:
        items = [{"name":n,"isDir":os.path.isdir(os.path.join(folder,n)),"path":os.path.join(folder,n)} for n in os.listdir(folder)]
        items.sort(key=lambda x:(not x["isDir"],x["name"].lower()))
        return jsonify({"ok":True,"items":items,"msg":f"Listed {folder}"})
    except Exception as e: return jsonify({"ok":False,"items":[],"msg":str(e)})

@app.route("/sysinfo")
def api_sysinfo():
    return jsonify({"time":get_time(),"battery":get_battery(),"system":get_system_info(),"ip":get_ip()})

@app.route("/ping")
def ping(): return "ok", 200

if __name__ == "__main__":
    print("Backend running on http://127.0.0.1:5050", flush=True)
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True, use_reloader=False)