#!/usr/bin/env python3
# Pegasus v1.2 - Created by thakur2309
# Use for Educational Purpose Only

import subprocess
import shutil
import sys
import os
import time
import re

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
    "              Pegasus v1.2  ",
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

def option_power_off():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Sending power off command..." + RESET)
    out, err = run_cmd("adb shell reboot -p", capture=True)
    if err:
        print(RED + "[-] Error powering off device:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Device is powering off." + RESET)

def option_install_apk():
    if not ensure_device_connected_prompt():
        return
    apk_path = input("Enter path to APK file (e.g., ./app.apk): ").strip()
    if not os.path.isfile(apk_path):
        print(RED + "[-] File does not exist." + RESET)
        return
    print(CYAN + "[*] Installing APK..." + RESET)
    out, err = run_cmd(f"adb install {apk_path}", capture=True)
    if "Success" in out:
        print(GREEN + "[+] APK installed successfully." + RESET)
    else:
        print(RED + "[-] Failed to install APK:" + RESET)
        print(err or out)

def option_delete_apk():
    if not ensure_device_connected_prompt():
        return
    package = input("Enter package name to uninstall (e.g., com.example.app): ").strip()
    if not package:
        print(RED + "[-] No package name provided." + RESET)
        return
    print(CYAN + "[*] Uninstalling package..." + RESET)
    out, err = run_cmd(f"adb uninstall {package}", capture=True)
    if "Success" in out:
        print(GREEN + "[+] Package uninstalled successfully." + RESET)
    else:
        print(RED + "[-] Failed to uninstall package:" + RESET)
        print(err or out)

def option_pull_file():
    if not ensure_device_connected_prompt():
        return
    remote_path = input("Enter remote file path (e.g., /sdcard/file.txt): ").strip()
    local_path = input("Enter local destination path (e.g., ./file.txt): ").strip()
    if not remote_path or not local_path:
        print(RED + "[-] Both remote and local paths are required." + RESET)
        return
    print(CYAN + "[*] Pulling file..." + RESET)
    out, err = run_cmd(f"adb pull {remote_path} {local_path}", capture=True)
    if err and "error" in err.lower():
        print(RED + "[-] Failed to pull file:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] File pulled to {local_path}" + RESET)

def option_push_file():
    if not ensure_device_connected_prompt():
        return
    local_path = input("Enter local file path (e.g., ./file.txt): ").strip()
    remote_path = input("Enter remote destination path (e.g., /sdcard/file.txt): ").strip()
    if not os.path.isfile(local_path):
        print(RED + "[-] Local file does not exist." + RESET)
        return
    if not remote_path:
        print(RED + "[-] Remote path is required." + RESET)
        return
    print(CYAN + "[*] Pushing file..." + RESET)
    out, err = run_cmd(f"adb push {local_path} {remote_path}", capture=True)
    if err and "error" in err.lower():
        print(RED + "[-] Failed to push file:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] File pushed to {remote_path}" + RESET)

def option_send_sms():
    if not ensure_device_connected_prompt():
        return
    phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
    message = input("Enter message to send: ").strip()
    if not phone_number or not message:
        print(RED + "[-] Phone number and message are required." + RESET)
        return
    # Sanitize message to escape quotes
    message = message.replace('"', '\\"')
    print(CYAN + "[*] Sending SMS..." + RESET)
    out, err = run_cmd(f'adb shell am start -a android.intent.action.SENDTO -d sms:{phone_number} --es sms_body "{message}"', capture=True)
    if err:
        print(RED + "[-] Failed to send SMS:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] SMS sent successfully." + RESET)

def option_dump_contacts():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Dumping contacts..." + RESET)
    out, err = run_cmd("adb shell content query --uri content://contacts/phones/", capture=True)
    if out:
        print(out)
        save = input("\nDo you want to save contacts to contacts.txt? (y/n): ").strip().lower()
        if save == "y":
            with open("contacts.txt", "w") as f:
                f.write(out + "\n")
            print(GREEN + "[+] Saved to ./contacts.txt" + RESET)
    else:
        print(RED + "[-] Failed to dump contacts:" + RESET)
        print(err or "No contacts found.")

def option_reboot_device():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Sending reboot command..." + RESET)
    out, err = run_cmd("adb shell reboot", capture=True)
    if err:
        print(RED + "[-] Error rebooting device:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Device is rebooting." + RESET)

def option_start_app():
    if not ensure_device_connected_prompt():
        return
    package = input("Enter package name to start (e.g., com.example.app): ").strip()
    if not package:
        print(RED + "[-] Package name is required." + RESET)
        return
    print(CYAN + "[*] Starting application..." + RESET)
    out, err = run_cmd(f"adb shell monkey -p {package} 1", capture=True)
    if err:
        print(RED + "[-] Failed to start application:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Application started." + RESET)

def option_get_device_logs():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Fetching device logs..." + RESET)
    filename = "device_log.txt"
    out, err = run_cmd(f"adb logcat -d > {filename}", capture=True)
    if os.path.isfile(filename):
        print(GREEN + f"[+] Logs saved to ./{filename}" + RESET)
        view = input("Do you want to open the logs now? (y/n): ").strip().lower()
        if view == "y":
            opener = shutil.which("xdg-open") or "xdg-open"
            run_cmd(f"{opener} {filename}")
    else:
        print(RED + "[-] Failed to fetch logs:" + RESET)
        print(err)

def option_toggle_wifi():
    if not ensure_device_connected_prompt():
        return
    state = input("Enter Wi-Fi state (enable/disable): ").strip().lower()
    if state not in ["enable", "disable"]:
        print(RED + "[-] Invalid state. Use 'enable' or 'disable'." + RESET)
        return
    print(CYAN + f"[*] {'Enabling' if state == 'enable' else 'Disabling'} Wi-Fi..." + RESET)
    cmd = f"adb shell svc wifi {state}"
    out, err = run_cmd(cmd, capture=True)
    if err:
        print(RED + f"[-] Failed to {state} Wi-Fi:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] Wi-Fi {state}d successfully." + RESET)

def option_check_storage():
    if not ensure_device_connected_prompt():
        return
    print(CYAN + "[*] Checking storage info..." + RESET)
    out, err = run_cmd("adb shell df", capture=True)
    if out:
        print(out)
        save = input("\nDo you want to save storage info to storage_info.txt? (y/n): ").strip().lower()
        if save == "y":
            with open("storage_info.txt", "w") as f:
                f.write(out + "\n")
            print(GREEN + "[+] Saved to ./storage_info.txt" + RESET)
    else:
        print(RED + "[-] Failed to fetch storage info:" + RESET)
        print(err)

def option_take_photo():
    if not ensure_device_connected_prompt():
        return
    
    print(CYAN + "[*] Opening Camera app..." + RESET)
    run_cmd("adb shell am start -a android.media.action.IMAGE_CAPTURE")
    time.sleep(3)  # wait for camera app to open

    print(CYAN + "[*] Capturing photo automatically..." + RESET)
    run_cmd("adb shell input keyevent 27")  # press shutter button
    time.sleep(2)  # wait for photo to save

    print(CYAN + "[*] Finding latest photo..." + RESET)
    out, err = run_cmd("adb shell ls -t /sdcard/DCIM/Camera/ | head -1", capture=True)
    if not out.strip():
        print(RED + "[-] No photo found in DCIM/Camera." + RESET)
        return
    
    latest = out.strip()
    remote = f"/sdcard/DCIM/Camera/{latest}"
    local = latest

    print(CYAN + f"[*] Pulling {latest}..." + RESET)
    run_cmd(f"adb pull {remote} ./")

    if os.path.isfile(local):
        print(GREEN + f"[+] Photo saved as {local}" + RESET)
        view = input("Do you want to open the photo now? (y/n): ").strip().lower()
        if view == "y":
            opener = shutil.which("xdg-open") or "xdg-open"
            run_cmd(f"{opener} {local}")
    else:
        print(RED + "[-] Failed to pull photo." + RESET)


# ----------------- Menu / Main Loop -----------------
def show_menu():
    print()
    col_space = " " * 11
    print(YELLOW + f"[1] Check Device{col_space}    [2] Connect a Device{col_space}[3] Disconnect Device\n")

    print(YELLOW + f"[4] Screen Recording{col_space}[5] Screen Mirror{col_space}   [6] Show APK List\n")

    print(YELLOW + f"[7] Take Screenshot{col_space} [8] Power Off{col_space}       [9] Install APK\n")

    print(YELLOW + f"[10] Delete APK{col_space}     [11] Pull File{col_space}      [12] Push File\n")

    print(YELLOW + f"[13] Send SMS{col_space}       [14] Dump Contacts{col_space}  [15] Reboot Device\n")

    print(YELLOW + f"[16] Start App{col_space}      [17] Get Device Logs{col_space}[18] Toggle Wi-Fi\n")

    print(YELLOW + f"[19] Check Storage{col_space}  [20] Take Photo{col_space}     [q] Quit\n")
    print()

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
        choice = input(GREEN + "Select an option (1-20) or q to quit: " + RESET).strip().lower()
        if choice == "q":
            print(CYAN + "Exiting Pegasus. Stay ethical." + RESET)
            break
        options = {
            "1": option_check_device,
            "2": option_connect_device,
            "3": option_disconnect_device,
            "4": option_screen_recording,
            "5": option_screen_mirror,
            "6": option_show_apk_list,
            "7": option_take_screenshot,
            "8": option_power_off,
            "9": option_install_apk,
            "10": option_delete_apk,
            "11": option_pull_file,
            "12": option_push_file,
            "13": option_send_sms,
            "14": option_dump_contacts,
            "15": option_reboot_device,
            "16": option_start_app,
            "17": option_get_device_logs,
            "18": option_toggle_wifi,
            "19": option_check_storage,
            "20": option_take_photo
        }
        if choice in options:
            options[choice]()
        else:
            print(RED + "Invalid option. Choose 1-20 or q." + RESET)
        input("\nPress Enter to return to menu...")
        print_banner()

# Define run() function to encapsulate main functionality
def run():
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + CYAN + "Interrupted. Bye." + RESET)
        sys.exit(0)
if __name__ == "__main__":
    run()

