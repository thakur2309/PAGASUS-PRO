#!/usr/bin/env python3
# Pegasus v1.1 - Created by thakur2309
# Use for Educational Purpose Only

import subprocess
import shutil
import sys
import os
import time

# ----------------- Config / Colors -----------------
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

BANNER = r"""
██████╗  █████╗  ██████╗  █████╗ ███████╗██╗   ██╗███████╗
██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔════╝██║   ██║██╔════╝
██████╔╝███████║██║  ███╗███████║███████╗██║   ██║███████╗
██╔═══╝ ██╔══██║██║   ██║██╔══██║╚════██║██║   ██║╚════██║
██║     ██║  ██║╚██████╔╝██║  ██║███████║╚██████╔╝███████║
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝
"""

HEADER_LINES = [
    "              Pegasus v1.1  ",
    "          Created by thakur2309",
    "      Use for Educational Purpose Only"
]

# ----------------- Helpers -----------------
def check_dependency(cmd_name, apt_pkg_name=None):
    path = shutil.which(cmd_name)
    return bool(path)

def run_cmd(cmd, capture=False):
    try:
        if capture:
            res = subprocess.run(cmd, shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.stdout.strip(), res.stderr.strip()
        else:
            return subprocess.call(cmd, shell=True)
    except Exception as e:
        return None

def adb_available():
    return check_dependency("adb")

def scrcpy_available():
    return check_dependency("scrcpy")

def clear_screen():
    os.system("clear" if shutil.which("clear") else "cls")

def print_banner():
    clear_screen()
    print(GREEN + BANNER + RESET)
    for line in HEADER_LINES:
        print(GREEN + line.center(55) + RESET)
    print(CYAN + "-"*59 + RESET)
    print()

# ----------------- ADB Helpers -----------------
def adb_devices_list():
    out, err = run_cmd("adb devices", capture=True)
    if out is None:
        return []
    lines = out.splitlines()
    devices = []
    for line in lines[1:]:
        line = line.strip()
        if line:
            parts = line.split()
            devices.append(parts[0])
    return devices

def ensure_device_connected_prompt():
    devices = adb_devices_list()
    if not devices:
        print(RED + "[!] No device detected." + RESET)
        print(YELLOW + "Please connect your device via USB and enable USB Debugging (Developer Options)." + RESET)
        print(YELLOW + "Settings -> Developer options -> USB debugging (enable)." + RESET)
        input("\nPress Enter after connecting device to continue...")
        return False
    return True

# ----------------- Option Implementations -----------------
def option_check_device():
    print(CYAN + "\n[+] Checking for connected devices..." + RESET)
    devices = adb_devices_list()
    if not devices:
        print(RED + "[-] No device detected." + RESET)
        print(YELLOW + "Choose option 2 to connect a device or connect via USB and allow debugging on device." + RESET)
        return
    device = devices[0]
    print(GREEN + f"[+] Device found: {device}" + RESET)
    print(CYAN + "[*] Gathering device info..." + RESET)
    model, _ = run_cmd("adb shell getprop ro.product.model", capture=True)
    android_ver, _ = run_cmd("adb shell getprop ro.build.version.release", capture=True)
    battery_info, _ = run_cmd("adb shell dumpsys battery | grep level", capture=True)
    if model: print(f"Model: {model}")
    if android_ver: print(f"Android: {android_ver}")
    if battery_info: print(f"Battery: {battery_info}")
    else:
        batt, _ = run_cmd("adb shell dumpsys battery", capture=True)
        for line in (batt or "").splitlines():
            if "level" in line:
                print(line.strip())
    print()

def option_connect_device():
    print(CYAN + "\n[+] Running 'adb devices'..." + RESET)
    devices = adb_devices_list()
    if not devices:
        print(RED + "[-] No device detected via USB." + RESET)
        print(YELLOW + "Please connect your device via USB and enable USB Debugging (Developer Options)." + RESET)
        return
    print(GREEN + "[+] Device detected via USB. Switching adb to tcpip mode on port 5555..." + RESET)
    run_cmd("adb tcpip 5555")
    ip = input("Enter device IP address (e.g. 192.168.1.10): ").strip()
    if not ip:
        print(RED + "No IP provided. Aborting connect." + RESET)
        return
    print(CYAN + f"Connecting to {ip}:5555 ..." + RESET)
    out, err = run_cmd(f"adb connect {ip}:5555", capture=True)
    if "connected" in out.lower() or "already" in out.lower():
        print(GREEN + "[+] Connected successfully over Wi-Fi." + RESET)
        run_cmd("adb devices")
    else:
        print(RED + "[-] Could not connect. Output:" + RESET)
        print(out or err)

def option_disconnect_device():
    print(CYAN + "\n[*] Disconnecting adb connections..." + RESET)
    out, err = run_cmd("adb disconnect", capture=True)
    print(GREEN + "[+] adb disconnect issued." + RESET)
    print("\nCurrent adb devices:")
    run_cmd("adb devices")

def option_screen_recording():
    if not ensure_device_connected_prompt():
        return
    dur = input("Enter recording duration (e.g. '15s' or '30' for seconds): ").strip()
    if dur.endswith("s"):
        dur_val = dur[:-1]
    else:
        dur_val = dur
    try:
        dsec = int(dur_val)
    except:
        print(RED + "Invalid duration. Enter seconds as integer (e.g. 15)." + RESET)
        return
    filename = "record.mp4"
    print(CYAN + f"[*] Starting screenrecord for {dsec} seconds..." + RESET)
    cmd = f"adb shell screenrecord --time-limit {dsec} /sdcard/{filename}"
    rc = run_cmd(cmd)
    if rc is None:
        print(YELLOW + "Fallback recording method..." + RESET)
        run_cmd(f"adb shell screenrecord /sdcard/{filename} &")
        time.sleep(dsec)
        run_cmd("adb shell pkill -f screenrecord")
    print(CYAN + "[*] Pulling recording to current directory..." + RESET)
    run_cmd(f"adb pull /sdcard/{filename} ./")
    print(GREEN + f"[+] Recording saved as ./{filename}" + RESET)
    view = input("Do you want to open the recording now? (y/n): ").strip().lower()
    if view == "y":
        opener = shutil.which("xdg-open") or "xdg-open"
        run_cmd(f"{opener} {filename}")

def option_screen_mirror():
    if not ensure_device_connected_prompt():
        return
    if not scrcpy_available():
        print(RED + "[!] scrcpy not found." + RESET)
        print(YELLOW + "Install with: sudo apt install scrcpy -y" + RESET)
        return
    print(CYAN + "[*] Launching scrcpy..." + RESET)
    run_cmd("scrcpy")

def option_show_apk_list():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Fetching installed packages..." + RESET)
    out, err = run_cmd("adb shell pm list packages -f", capture=True)
    if out:
        print(out)
        save = input("\nDo you want to save the list to apk_list.txt? (y/n): ").strip().lower()
        if save == "y":
            with open("apk_list.txt", "w") as f:
                f.write(out + "\n")
            print(GREEN + "[+] Saved to ./apk_list.txt" + RESET)
    else:
        print(RED + "No output. Is device connected?" + RESET)

def option_take_screenshot():
    if not ensure_device_connected_prompt():
        return
    remote = "/sdcard/screen.png"
    local = "screen.png"
    print(CYAN + "[*] Taking screenshot..." + RESET)
    run_cmd(f"adb shell screencap -p {remote}")
    print(CYAN + "[*] Pulling screenshot..." + RESET)
    run_cmd(f"adb pull {remote} ./")
    print(GREEN + f"[+] Screenshot saved as ./{local}" + RESET)
    view = input("Do you want to open the screenshot now? (y/n): ").strip().lower()
    if view == "y":
        opener = shutil.which("xdg-open") or "xdg-open"
        run_cmd(f"{opener} {local}")

# ----------------- Menu / Main Loop -----------------
def show_menu():
    print()
    col_space = " " * 11
    print(f"[1] Check Device{col_space}    [2] Connect a Device{col_space}[3] Disconnect Device\n")
    print(f"[4] Screen Recording{col_space}[5] Screen Mirror{col_space}   [6] Show APK List\n")
    empty = "[ ] ----- soon -----"
    print(f"{empty}{col_space}[7] Take Screenshot {col_space}{empty}\n")

def dependencies_check():
    print(CYAN + "[*] Checking dependencies..." + RESET)
    deps = [("adb", adb_available()), ("scrcpy", scrcpy_available())]
    for name, available in deps:
        if available:
            print(GREEN + f"[OK] {name} installed" + RESET)
        else:
            print(RED + f"[MISSING] {name} (install: sudo apt install {name} -y)" + RESET)

def main():
    print_banner()
    dependencies_check()
    while True:
        print()
        show_menu()
        choice = input(GREEN + "Select an option (1-7) or q to quit: " + RESET).strip().lower()
        if choice == "q":
            print(CYAN + "Exiting Pegasus. Stay ethical." + RESET)
            break
        if choice == "1":
            option_check_device()
        elif choice == "2":
            option_connect_device()
        elif choice == "3":
            option_disconnect_device()
        elif choice == "4":
            option_screen_recording()
        elif choice == "5":
            option_screen_mirror()
        elif choice == "6":
            option_show_apk_list()
        elif choice == "7":
            option_take_screenshot()
        else:
            print(RED + "Invalid option. Choose 1-7 or q." + RESET)
        input("\nPress Enter to return to menu...")
        print_banner()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + CYAN + "Interrupted. Bye." + RESET)
        sys.exit(0)
