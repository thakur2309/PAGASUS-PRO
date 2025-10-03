# Pegasus v1.1 — ADB Utility Toolkit

> **Use for Educational Purpose Only — Stay Ethical.**  
> Creator: **thakur2309**  
> YouTube: **Firewall Breaker**

Pegasus is a simple, menu‑driven Python tool that helps you work with Android devices via **ADB**.  
It’s perfect for beginners who want a clean interface to: check device info, connect over Wi‑Fi, take screenshots, record the screen, mirror the display (via **scrcpy**), and list installed APKs.

---

## 🔖 Table of Contents
- [Features](#-features)
- [Requirements](#-requirements)
- [Phone Setup (Android)](#-phone-setup-android)
- [Linux Setup (Kali/Ubuntu/Debian)](#-linux-setup-kaliubuntudebian)
- [Windows Setup (Optional)](#-windows-setup-optional)
- [Get the Code](#-get-the-code)
- [Run Pegasus](#-run-pegasus)
- [How to Use (Step by Step)](#-how-to-use-step-by-step)
- [Menu Options Explained](#-menu-options-explained)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Disclaimer](#-disclaimer)

---
## 🗝️ Licence key
- 🔐 Licence key - `FIREWALLBREAKER`
- 📌 Instagram Username `sudo_xploit`
  
- 👉 [Instagram](https://www.instagram.com/sudo_xploit?igsh=MWN0YWc3N2JyenhoNw==)

---
### Example Output V-1.1 🎥
![Instagram Image ](https://raw.githubusercontent.com/thakur2309/PAGASUS-PRO/refs/heads/main/Screenshot_2025_1002_113702.jpg)

---
### Example Output V-1.2 🎥
![Instagram Image ](https://raw.githubusercontent.com/thakur2309/PAGASUS-PRO/refs/heads/main/Screenshot_2025_1003_144711.jpg)

<h3 align="center"> 📌Version-1.3 comming soon..</h3>

## ✨ Features
- ✅ Detect connected Android device and show **model / Android version / battery**
- ✅ **Wi‑Fi ADB** connect (after one‑time USB pairing)
- ✅ **Disconnect** all ADB sessions
- ✅ **Screen Recording** and auto‑pull to your PC
- ✅ **Screen Mirroring** with `scrcpy` (optional but recommended)
- ✅ **Show installed APK list**
- ✅ **Screenshot** and save to your PC
- ✅ Clean banner, color output, and beginner‑friendly prompts

---

## ⚙️ Requirements
**On PC (Linux or Windows):**
- Python **3.8+**
- **ADB** (Android Debug Bridge)
- **scrcpy** *(optional, only for screen mirroring)*
- `git` *(to clone the repo)*

**On Android phone:**
- Developer options **enabled**
- **USB debugging** turned on
- For Wi‑Fi ADB: phone and PC must be on the **same network**

---

## 📱 Phone Setup (Android)
1. Open **Settings** → **About phone** → tap **Build number** 7 times to enable **Developer options**.  
2. Go to **Settings** → **Developer options** → enable **USB debugging**.  
3. Connect the phone to PC via **USB cable** and **Allow** the RSA fingerprint prompt.  
4. *(For Wi‑Fi ADB)* Ensure **phone and PC are on the same Wi‑Fi**. Find phone IP:  
   - Wi‑Fi details page (IP address), **or**  
   - After USB connection:  
     ```bash
     adb shell ip addr show wlan0 | grep 'inet '
     ```

---

## 🐧 Linux Setup (Kali/Ubuntu/Debian)
```bash
sudo apt update
# Core tools
sudo apt install -y adb scrcpy python3 python3-venv git

# (Recommended) Udev rules so device works without sudo
sudo apt install -y android-sdk-platform-tools-common
```

> If `scrcpy` is not needed, you may skip it. Everything else is required.

---
## scrcpy Installation  

Since `sudo apt install scrcpy` may not work on some systems, please follow the official installation guide:  

👉 [scrcpy Installation for Linux](https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md)


## 🪟 Windows Setup (Optional)
- Install **Android Platform Tools** (ADB) from Google or via **winget**:
  ```powershell
  winget install --id Google.PlatformTools
  ```
- Install **scrcpy** (optional) from releases or via **winget**:
  ```powershell
  winget install Genymobile.scrcpy
  ```
- Install **Python 3** from [python.org](https://www.python.org/downloads/) and ensure **Add to PATH** is checked.
- Open **Command Prompt / PowerShell** in the project folder to run the script.

---

## ⬇️ Get the Code
```bash
git clone https://github.com/thakur2309/PAGASUS-PRO.git
cd PAGASUS-PRO
# Place your script here as: pegasus.py
```

*(If your file name is different, adjust commands accordingly.)*

---

## ▶️ Run Pegasus
```bash
python3 pegasus.py
```
If you see the Pegasus banner and the menu, you’re good to go.

---

## 🧭 How to Use (Step by Step)
1. **Connect via USB** and authorize the device on first use.  
2. Launch Pegasus: `python3 pegasus.py`.  
3. Start with **[1] Check Device** to verify connection and view info.  
4. To use **Wi‑Fi ADB**:  
   - Keep USB connected once, choose **[2] Connect a Device**.  
   - Script will switch ADB to TCP/IP on **port 5555** and ask for your **phone’s IP**.  
   - Enter IP (example: `192.168.1.42`) → it will run `adb connect <ip>:5555`.  
   - You can now disconnect USB and continue **wirelessly**.  
5. Use other options as needed (record screen, mirror, screenshot, list APKs, etc.).  
6. When done, choose **[3] Disconnect Device** or simply close the program.

---

## 🧰 Menu Options Explained
- **[1] Check Device**  
  Shows connected device list and prints **Model**, **Android version**, and **Battery** level.

- **[2] Connect a Device (Wi‑Fi ADB)**  
  Puts ADB in TCP/IP mode (`adb tcpip 5555`) and connects to the phone at `<IP>:5555`.

- **[3] Disconnect Device**  
  Runs `adb disconnect` to close all ADB over‑network sessions.

- **[4] Screen Recording**  
  Prompts for duration (in seconds), records using:
  ```bash
  adb shell screenrecord --time-limit <secs> /sdcard/record.mp4
  adb pull /sdcard/record.mp4 ./
  ```
  Saves file as `./record.mp4` locally.

- **[5] Screen Mirror (scrcpy)**  
  Opens **scrcpy** to mirror and control your phone on the desktop. *(Requires `scrcpy` installed.)*

- **[6] Show APK List**  
  Lists installed packages with paths:
  ```bash
  adb shell pm list packages -f
  ```
  Optionally saves to `apk_list.txt`.

- **[ ] Take Screenshot → **[7]**  
  Captures and pulls a screenshot:
  ```bash
  adb shell screencap -p /sdcard/screen.png
  adb pull /sdcard/screen.png ./
  ```

---

## 🧩 Troubleshooting
- **Device not detected**
  - Use a good USB cable and port.
  - Run:
    ```bash
    adb kill-server
    adb start-server
    adb devices
    ```
  - Accept the **Allow USB debugging** prompt on phone.
  - On Linux, install udev rules: `sudo apt install android-sdk-platform-tools-common` and replug the device.

- **`adb connect <ip>:5555` fails**
  - Ensure phone & PC are on the **same network**.
  - Re‑enable TCP/IP: `adb tcpip 5555` (over USB) and try again.
  - Verify IP is correct from Wi‑Fi details.

- **`scrcpy` not found**
  - Since `sudo apt install scrcpy` may not work on some systems, please follow the official installation guide:  

👉 [scrcpy Installation Guide for Linux](https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md)
 - **`scrcpy` not found in windows**
   - `winget install Genymobile.scrcpy` (Windows).

- **Permission denied / file not pulled**
  - Ensure storage permission if prompted on device.
  - Try alternative paths like `/sdcard/Download/`.

---

## ❓ FAQ
**Q: Does Pegasus require root?**  
A: **No**, ADB + Developer Options are enough.

**Q: Will this hack devices?**  
A: **No**. Pegasus is a utility around ADB for legitimate debugging, automation, and learning.

**Q: Can I use Pegasus wirelessly without USB every time?**  
A: After the first USB authorization + `adb tcpip 5555`, you can connect over Wi‑Fi using `adb connect <ip>:5555` (until the phone restarts or IP changes).

**Q: Where are the files saved?**  
A: In the **current working directory** (e.g., `record.mp4`, `screen.png`, `apk_list.txt`).

---

## ⚠️ Disclaimer
This tool is intended **only for educational and lawful use** on devices **you own** or have **explicit permission** to manage. The creator and contributors are **not responsible** for any misuse.  
Stay ethical — **Firewall Breaker** community promotes **learning & safety**, not harm.

---

👨‍💻 **Author**  
- Made with ❤️ by **thakur2309** 
- Name: **Alok Thakur**  
- YouTube: [🔥 Firewall Breaker](https://www.youtube.com/@FirewallBreaker09)

---
## 📌 Contact Me  

<a href="https://youtube.com/@firewallbreaker09">
  <img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube">
</a>  
<br>  

<a href="https://github.com/thakur2309?tab=repositories">
  <img src="https://img.shields.io/badge/GitHub-000000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
</a>  
<br>  

<a href="https://whatsapp.com/channel/0029VbAiqVMKLaHjg5J1Nm2F">
  <img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="WhatsApp Channel">
</a>

