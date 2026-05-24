#!/usr/bin/env python3
# Pegasus v1.2 - Created by thakur2309
# Use for Educational Purpose Only
import subprocess
import shutil
import sys
import os
import time
import re
import datetime
# ----------------- Config / Colors -----------------
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
RESET = "\033[0m"
BANNER = r"""
██████╗ ███████╗ ██████╗  █████╗ ███████╗██╗   ██╗███████╗
██╔══██╗██╔════╝██╔════╝ ██╔══██╗██╔════╝██║   ██║██╔════╝
██████╔╝█████╗  ██║  ███╗███████║███████╗██║   ██║███████╗
██╔═══╝ ██╔══╝  ██║   ██║██╔══██║╚════██║██║   ██║╚════██║
██║     ███████╗╚██████╔╝██║  ██║███████║╚██████╔╝███████╗
╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝                                                     
"""
HEADER_LINES = [
    " Pegasus v-1.3 | Created by thakur2309",
    " Android Device Management & Security Tool ",
    " Use For Eduaction Purpose Only "

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
def get_selected_device():
    devices = adb_devices_list()
    if not devices:
        print(RED + "[!] No device detected." + RESET)
        print(YELLOW + "Please connect your device via USB and enable USB Debugging (Developer Options)." + RESET)
        print(YELLOW + "Settings -> Developer options -> USB debugging (enable)." + RESET)
        input("\nPress Enter after connecting device to continue...")
        return None
    if len(devices) == 1:
        return devices[0]
    else:
        print(CYAN + "[+] Multiple devices detected:" + RESET)
        for i, dev in enumerate(devices, 1):
            print(f"{i}. {dev}")
        while True:
            try:
                choice = int(input("Select device number: "))
                if 1 <= choice <= len(devices):
                    return devices[choice - 1]
                else:
                    print(RED + "Invalid choice." + RESET)
            except ValueError:
                print(RED + "Enter a number." + RESET)
# ----------------- Device Connection Logging -----------------
connected_devices = {}  # device_id: connect_time

def update_device_logs():
    current_devices = adb_devices_list()
    now = datetime.datetime.now()
    # Check for disconnected
    for dev in list(connected_devices.keys()):
        if dev not in current_devices:
            start = connected_devices.pop(dev)
            duration = now - start
            with open("connection_log.txt", "a") as f:
                f.write(f"{dev} disconnected at {now}, connected for {duration}\n")
    # Check for new connected
    for dev in current_devices:
        if dev not in connected_devices:
            connected_devices[dev] = now
            with open("connection_log.txt", "a") as f:
                f.write(f"{dev} connected at {now}\n")

def option_view_connection_history():
    update_device_logs()  # Update before viewing
    if not os.path.exists("connection_log.txt"):
        print(YELLOW + "No connection log yet." + RESET)
        return
    print(CYAN + "[*] Device Connection History:" + RESET)
    with open("connection_log.txt", "r") as f:
        print(f.read())
    # Show current connections
    if connected_devices:
        now = datetime.datetime.now()
        print(CYAN + "[*] Currently Connected:" + RESET)
        for dev, start in connected_devices.items():
            duration = now - start
            print(f"{dev} connected since {start}, duration so far: {duration}")
# ----------------- Option Implementations -----------------
def option_check_device():
    print(CYAN + "\n[+] Checking for connected devices..." + RESET)
    device = get_selected_device()
    if device is None:
        return
    print(GREEN + f"[+] Device found: {device}" + RESET)
    print(CYAN + "[*] Gathering device info..." + RESET)
    model, _ = run_cmd(f"adb -s {device} shell getprop ro.product.model", capture=True)
    android_ver, _ = run_cmd(f"adb -s {device} shell getprop ro.build.version.release", capture=True)
    battery_info, _ = run_cmd(f"adb -s {device} shell dumpsys battery | grep level", capture=True)
    if model: print(f"Model: {model}")
    if android_ver: print(f"Android: {android_ver}")
    if battery_info: print(f"Battery: {battery_info}")
    else:
        batt, _ = run_cmd(f"adb -s {device} shell dumpsys battery", capture=True)
        for line in (batt or "").splitlines():
            if "level" in line:
                print(line.strip())
    print()
def option_connect_device():
    print(CYAN + "\n[+] Running 'adb devices'..." + RESET)
    usb_devices = [d for d in adb_devices_list() if ':' not in d]
    enable_tcpip = input("Do you want to enable ADB over WiFi (requires USB, only first time)? (y/n): ").strip().lower()
    if enable_tcpip == 'y':
        if not usb_devices:
            print(RED + "[-] No device detected via USB." + RESET)
            print(YELLOW + "Please connect your device via USB and enable USB Debugging (Developer Options)." + RESET)
            return
        if len(usb_devices) > 1:
            print(CYAN + "[+] Multiple USB devices detected:" + RESET)
            for i, dev in enumerate(usb_devices, 1):
                print(f"{i}. {dev}")
            while True:
                try:
                    choice = int(input("Select USB device number for TCPIP mode: "))
                    if 1 <= choice <= len(usb_devices):
                        usb_device = usb_devices[choice - 1]
                        break
                    print(RED + "Invalid choice." + RESET)
                except ValueError:
                    print(RED + "Enter a number." + RESET)
        else:
            usb_device = usb_devices[0]
        print(GREEN + "[+] Device detected via USB. Switching adb to tcpip mode on port 5555..." + RESET)
        run_cmd(f"adb -s {usb_device} tcpip 5555")
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
    tcp_devices = [d for d in adb_devices_list() if ':' in d]
    if not tcp_devices:
        print(YELLOW + "[-] No wireless devices connected." + RESET)
        print("\nCurrent adb devices:")
        run_cmd("adb devices")
        return
    if len(tcp_devices) == 1:
        disconnect_cmd = f"adb disconnect {tcp_devices[0]}"
    else:
        print(CYAN + "[+] Multiple wireless devices:" + RESET)
        for i, dev in enumerate(tcp_devices, 1):
            print(f"{i}. {dev}")
        print("0. All")
        while True:
            try:
                choice = int(input("Select number to disconnect (0 for all): "))
                if choice == 0:
                    disconnect_cmd = "adb disconnect"
                    break
                elif 1 <= choice <= len(tcp_devices):
                    disconnect_cmd = f"adb disconnect {tcp_devices[choice - 1]}"
                    break
                print(RED + "Invalid choice." + RESET)
            except ValueError:
                print(RED + "Enter a number." + RESET)
    out, err = run_cmd(disconnect_cmd, capture=True)
    print(GREEN + "[+] Disconnect issued." + RESET)
    print("\nCurrent adb devices:")
    run_cmd("adb devices")
def option_screen_recording():
    device = get_selected_device()
    if device is None:
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
    cmd = f"adb -s {device} shell screenrecord --time-limit {dsec} /sdcard/{filename}"
    rc = run_cmd(cmd)
    if rc is None:
        print(YELLOW + "Fallback recording method..." + RESET)
        run_cmd(f"adb -s {device} shell screenrecord /sdcard/{filename} &")
        time.sleep(dsec)
        run_cmd(f"adb -s {device} shell pkill -f screenrecord")
    print(CYAN + "[*] Pulling recording to current directory..." + RESET)
    run_cmd(f"adb -s {device} pull /sdcard/{filename} ./")
    print(GREEN + f"[+] Recording saved as ./{filename}" + RESET)
    view = input("Do you want to open the recording now? (y/n): ").strip().lower()
    if view == "y":
        opener = shutil.which("xdg-open") or "xdg-open"
        run_cmd(f"{opener} {filename}")
def option_screen_mirror():
    device = get_selected_device()
    if device is None:
        return
    if not scrcpy_available():
        print(RED + "[!] scrcpy not found." + RESET)
        print(YELLOW + "Install with: sudo apt install scrcpy -y" + RESET)
        return
    print(CYAN + "[*] Launching scrcpy..." + RESET)
    run_cmd(f"scrcpy -s {device}")
def option_show_apk_list():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Fetching installed packages..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell pm list packages -f", capture=True)
    if not out:
        print(RED + "No output. Is device connected?" + RESET)
        return
    # Clean: extract only package names
    cleaned_lines = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            parts = line.split("=")
            if len(parts) > 1:
                pkg = parts[-1]
                cleaned_lines.append(pkg)
    print(CYAN + "[+] Installed Package Names:" + RESET)
    for pkg in cleaned_lines:
        print(pkg)
    print(f"\nTotal: {len(cleaned_lines)} packages")
    save = input("\nDo you want to save the clean list to apk_list.txt? (y/n): ").strip().lower()
    if save == "y":
        with open("apk_list.txt", "w") as f:
            f.write("\n".join(cleaned_lines) + "\n")
        print(GREEN + "[+] Saved clean list to ./apk_list.txt" + RESET)
def option_take_screenshot():
    device = get_selected_device()
    if device is None:
        return
    remote = "/sdcard/screen.png"
    local = "screen.png"
    print(CYAN + "[*] Taking screenshot..." + RESET)
    run_cmd(f"adb -s {device} shell screencap -p {remote}")
    print(CYAN + "[*] Pulling screenshot..." + RESET)
    run_cmd(f"adb -s {device} pull {remote} ./")
    print(GREEN + f"[+] Screenshot saved as ./{local}" + RESET)
    view = input("Do you want to open the screenshot now? (y/n): ").strip().lower()
    if view == "y":
        opener = shutil.which("xdg-open") or "xdg-open"
        run_cmd(f"{opener} {local}")
def option_power_off():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Sending power off command..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell reboot -p", capture=True)
    if err:
        print(RED + "[-] Error powering off device:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Device is powering off." + RESET)
def option_install_apk():
    device = get_selected_device()
    if device is None:
        return
    apk_path = input("Enter path to APK file (e.g., ./app.apk): ").strip()
    if not os.path.isfile(apk_path):
        print(RED + "[-] File does not exist." + RESET)
        return
    print(CYAN + "[*] Installing APK..." + RESET)
    out, err = run_cmd(f"adb -s {device} install {apk_path}", capture=True)
    if "Success" in out:
        print(GREEN + "[+] APK installed successfully." + RESET)
    else:
        print(RED + "[-] Failed to install APK:" + RESET)
        print(err or out)
def option_delete_apk():
    device = get_selected_device()
    if device is None:
        return
    package = input("Enter package name to uninstall (e.g., com.example.app): ").strip()
    if not package:
        print(RED + "[-] No package name provided." + RESET)
        return
    print(CYAN + "[*] Uninstalling package..." + RESET)
    out, err = run_cmd(f"adb -s {device} uninstall {package}", capture=True)
    if "Success" in out:
        print(GREEN + "[+] Package uninstalled successfully." + RESET)
    else:
        print(RED + "[-] Failed to uninstall package:" + RESET)
        print(err or out)
def option_pull_file():
    device = get_selected_device()
    if device is None:
        return
    remote_path = input("Enter remote file path (e.g., /sdcard/file.txt): ").strip()
    local_path = input("Enter local destination path (e.g., ./file.txt): ").strip()
    if not remote_path or not local_path:
        print(RED + "[-] Both remote and local paths are required." + RESET)
        return
    print(CYAN + "[*] Pulling file..." + RESET)
    out, err = run_cmd(f"adb -s {device} pull {remote_path} {local_path}", capture=True)
    if err and "error" in err.lower():
        print(RED + "[-] Failed to pull file:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] File pulled to {local_path}" + RESET)
def option_push_file():
    device = get_selected_device()
    if device is None:
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
    out, err = run_cmd(f"adb -s {device} push {local_path} {remote_path}", capture=True)
    if err and "error" in err.lower():
        print(RED + "[-] Failed to push file:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] File pushed to {remote_path}" + RESET)
def option_send_sms():
    device = get_selected_device()
    if device is None:
        return
    phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
    message = input("Enter message to send: ").strip()
    if not phone_number or not message:
        print(RED + "[-] Phone number and message are required." + RESET)
        return
    # Sanitize message to escape quotes
    message = message.replace('"', '\\"')
    print(CYAN + "[*] Sending SMS..." + RESET)
    out, err = run_cmd(f'adb -s {device} shell am start -a android.intent.action.SENDTO -d sms:{phone_number} --es sms_body "{message}"', capture=True)
    if err:
        print(RED + "[-] Failed to send SMS:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] SMS sent successfully." + RESET)
def option_dump_contacts():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Dumping contacts..." + RESET)
    # Updated URI for better compatibility on newer Android
    out, err = run_cmd(f"adb -s {device} shell content query --uri content://com.android.contacts/data/phones/", capture=True)
    if not out or "No result found" in out or err:
        print(RED + "[-] No contacts found or access denied (common on Android 10+)." + RESET)
        print(YELLOW + "Tip: Contacts might be synced with Google account, check there." + RESET)
        return
    # Parse: Row format -> display_name=NAME, data1=NUMBER
    cleaned_contacts = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("Row:"):
            continue
        name_match = re.search(r'display_name=([^,]+)', line)
        number_match = re.search(r'data1=([^,]+)', line)
        if name_match and number_match:
            name = name_match.group(1).strip()
            number = number_match.group(1).strip()
            if name and number:
                cleaned_contacts.append(f"{name}: {number}")
    print(CYAN + "[+] Contacts (Name: Number):" + RESET)
    if cleaned_contacts:
        for contact in cleaned_contacts:
            print(contact)
        print(f"\nTotal: {len(cleaned_contacts)} contacts")
    else:
        print(YELLOW + "No contacts parsed (device may have restricted access)." + RESET)
    save = input("\nDo you want to save clean contacts to contacts.txt? (y/n): ").strip().lower()
    if save == "y" and cleaned_contacts:
        with open("contacts.txt", "w") as f:
            f.write("\n".join(cleaned_contacts) + "\n")
        print(GREEN + "[+] Saved clean contacts to ./contacts.txt" + RESET)
def option_reboot_device():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Sending reboot command..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell reboot", capture=True)
    if err:
        print(RED + "[-] Error rebooting device:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Device is rebooting." + RESET)
def option_start_app():
    device = get_selected_device()
    if device is None:
        return
    package = input("Enter package name to start (e.g., com.example.app): ").strip()
    if not package:
        print(RED + "[-] Package name is required." + RESET)
        return
    print(CYAN + "[*] Starting application..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell monkey -p {package} 1", capture=True)
    if err:
        print(RED + "[-] Failed to start application:" + RESET)
        print(err)
    else:
        print(GREEN + "[+] Application started." + RESET)
def option_get_device_logs():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Fetching device logs..." + RESET)
    filename = "device_log.txt"
    out, err = run_cmd(f"adb -s {device} logcat -d > {filename}", capture=True)
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
    device = get_selected_device()
    if device is None:
        return
    state = input("Enter Wi-Fi state (enable/disable): ").strip().lower()
    if state not in ["enable", "disable"]:
        print(RED + "[-] Invalid state. Use 'enable' or 'disable'." + RESET)
        return
    print(CYAN + f"[*] {'Enabling' if state == 'enable' else 'Disabling'} Wi-Fi..." + RESET)
    cmd = f"adb -s {device} shell svc wifi {state}"
    out, err = run_cmd(cmd, capture=True)
    if err:
        print(RED + f"[-] Failed to {state} Wi-Fi:" + RESET)
        print(err)
    else:
        print(GREEN + f"[+] Wi-Fi {state}d successfully." + RESET)
def option_check_storage():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Checking storage info..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell df -h", capture=True) # Human readable
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
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Opening Camera app..." + RESET)
    run_cmd(f"adb -s {device} shell am start -a android.media.action.IMAGE_CAPTURE")
    time.sleep(3)
    print(CYAN + "[*] Capturing photo automatically..." + RESET)
    run_cmd(f"adb -s {device} shell input keyevent 27")
    time.sleep(2)
    print(CYAN + "[*] Finding latest photo..." + RESET)
    out, err = run_cmd(f"adb -s {device} shell ls -t /sdcard/DCIM/Camera/ | head -1", capture=True)
    if not out.strip():
        print(RED + "[-] No photo found in DCIM/Camera." + RESET)
        return
    latest = out.strip()
    remote = f"/sdcard/DCIM/Camera/{latest}"
    local = latest
    print(CYAN + f"[*] Pulling {latest}..." + RESET)
    run_cmd(f"adb -s {device} pull {remote} ./")
    if os.path.isfile(local):
        print(GREEN + f"[+] Photo saved as {local}" + RESET)
        view = input("Do you want to open the photo now? (y/n): ").strip().lower()
        if view == "y":
            opener = shutil.which("xdg-open") or "xdg-open"
            run_cmd(f"{opener} {local}")
    else:
        print(RED + "[-] Failed to pull photo." + RESET)
def option_troubleshoot():
    print(CYAN + "[*] Troubleshooting ADB connection..." + RESET)
    run_cmd("adb kill-server")
    run_cmd("adb start-server")
    print(GREEN + "[+] ADB server restarted." + RESET)
    print(CYAN + "[*] Current devices:" + RESET)
    run_cmd("adb devices")

# ----------------- New Cyber Defence Features -----------------
def cyber_root_detection():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Checking for root access..." + RESET)
    methods = [
        f"adb -s {device} shell which su",
        f"adb -s {device} shell getprop ro.build.tags | grep test-keys",
        f"adb -s {device} shell ls /system/bin/su",
        f"adb -s {device} shell ls /system/xbin/su"
    ]
    rooted = False
    for cmd in methods:
        out, _ = run_cmd(cmd, capture=True)
        if out and "not found" not in out.lower() and out != "":
            rooted = True
            break
    if rooted:
        print(RED + "[!] Device appears to be ROOTED (Security Risk for banking apps)" + RESET)
    else:
        print(GREEN + "[+] No root detected." + RESET)

def cyber_apk_permissions():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Dumping dangerous permissions per app (granted only)..." + RESET)
    pkg_out, _ = run_cmd(f"adb -s {device} shell pm list packages", capture=True)
    if not pkg_out:
        print(RED + "[-] Failed to fetch package list." + RESET)
        return
    packages = [line.split(":")[1].strip() for line in pkg_out.splitlines() if line.startswith("package:")]
    
    dangerous_perms = [
        "android.permission.CAMERA", "android.permission.ACCESS_FINE_LOCATION", 
        "android.permission.ACCESS_COARSE_LOCATION", "android.permission.RECORD_AUDIO", 
        "android.permission.READ_SMS", "android.permission.CALL_PHONE", 
        "android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_CONTACTS", "android.permission.READ_PHONE_STATE"
    ]
    
    print(YELLOW + "App Package → Granted Dangerous Permissions:" + RESET)
    found_any = False
    for pkg in packages:
        dump_out, _ = run_cmd(f"adb -s {device} shell dumpsys package {pkg}", capture=True)
        if not dump_out:
            continue
        granted = []
        lines = dump_out.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("install permissions:") or line.startswith("runtime permissions:"):
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("install permissions:", "runtime permissions:", "User ")):
                    perm_line = lines[i].strip()
                    if ": granted=true" in perm_line:
                        perm = perm_line.split(":")[0].strip()
                        if perm in dangerous_perms:
                            granted.append(perm)
                    i += 1
                continue
            i += 1
        if granted:
            found_any = True
            print(f"  {pkg}: {', '.join(granted)}")
    
    if not found_any:
        print(GREEN + "[+] No dangerous permissions currently granted to any app." + RESET)
        print(YELLOW + "[*] Note: Runtime permissions need user approval to be granted." + RESET)

def cyber_security_audit():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Running Device Security Audit..." + RESET)
    info = {}
    cmds = {
        "Android Version": f"adb -s {device} shell getprop ro.build.version.release",
        "Security Patch Level": f"adb -s {device} shell getprop ro.build.version.security_patch",
        "Encryption Status": f"adb -s {device} shell getprop ro.crypto.state",
        "Build Tags": f"adb -s {device} shell getprop ro.build.tags"
    }
    for name, cmd in cmds.items():
        out, _ = run_cmd(cmd, capture=True)
        info[name] = out or "Unknown"
        print(f"{name}: {info[name]}")
    
    # Debuggable apps count
    pkg_out, _ = run_cmd(f"adb -s {device} shell pm list packages", capture=True)
    packages = [line.split(":")[1].strip() for line in (pkg_out or "").splitlines() if line.startswith("package:")]
    debuggable_count = 0
    for pkg in packages:
        dump_out, _ = run_cmd(f"adb -s {device} shell dumpsys package {pkg} | grep debuggable", capture=True)
        if "debuggable=true" in (dump_out or "").lower():
            debuggable_count += 1
    print(f"Debuggable Apps Count: {debuggable_count} (Should be 0 in production)")

def cyber_debuggable_apps():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Scanning for debuggable apps..." + RESET)
    pkg_out, _ = run_cmd(f"adb -s {device} shell pm list packages", capture=True)
    packages = [line.split(":")[1].strip() for line in (pkg_out or "").splitlines() if line.startswith("package:")]
    found = []
    for pkg in packages:
        dump_out, _ = run_cmd(f"adb -s {device} shell dumpsys package {pkg} | grep debuggable", capture=True)
        if "debuggable=true" in (dump_out or "").lower():
            found.append(pkg)
    if found:
        print(RED + "[!] Debuggable apps found (Security Risk):" + RESET)
        for pkg in found:
            print(f"  - {pkg}")
    else:
        print(GREEN + "[+] No debuggable apps detected." + RESET)

def cyber_device_shell():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Opening interactive ADB shell (type 'exit' to quit)..." + RESET)
    print(YELLOW + "[*] Use carefully - only on your own device!" + RESET)
    run_cmd(f"adb -s {device} shell")

def cyber_network_check():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Checking connected Wi-Fi security..." + RESET)
    out, _ = run_cmd(f"adb -s {device} shell dumpsys wifi", capture=True)
    if out:
        if "WPA" in out or "WPA2" in out or "WPA3" in out:
            print(GREEN + "[+] Connected to secured Wi-Fi network." + RESET)
        elif "open" in out.lower():
            print(RED + "[!] Connected to OPEN (unsecured) Wi-Fi!" + RESET)
        else:
            print(YELLOW + "[*] Wi-Fi security status unclear." + RESET)
    if check_dependency("nmap"):
        ip_range = input("Enter local network range for scan (e.g. 192.168.1.0/24) or press Enter to skip: ").strip()
        if ip_range:
            print(CYAN + "[*] Running nmap ping scan on host PC..." + RESET)
            run_cmd(f"nmap -sn {ip_range}")
    else:
        print(YELLOW + "[*] nmap not found on host for advanced network scan." + RESET)

def cyber_recent_logs():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "\n[+] Fetching recent security-related logs..." + RESET)
    print(YELLOW + "[*] Filtering for permission, security, and denial events." + RESET)
    run_cmd(f"adb -s {device} logcat -d *:W | grep -i 'permission\\|security\\|denied\\|violation\\|warning'")

def option_scan_device_vulnerabilities():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Scanning for device vulnerabilities..." + RESET)
    patch_level, _ = run_cmd(f"adb -s {device} shell getprop ro.build.version.security_patch", capture=True)
    print(f"Security Patch Level: {patch_level}")
    build_date, _ = run_cmd(f"adb -s {device} shell getprop ro.build.date", capture=True)
    print(f"Build Date: {build_date}")
    try:
        patch_date = datetime.datetime.strptime(patch_level, "%Y-%m-%d")
        if patch_date < datetime.datetime(2025, 1, 1):
            print(RED + "[!] Device may have known vulnerabilities (patch older than 2025-01-01)" + RESET)
        else:
            print(GREEN + "[+] Patch level is recent." + RESET)
    except:
        print(YELLOW + "[?] Unable to parse patch level." + RESET)
    print(YELLOW + "For specific CVEs, search online for your Android version and patch level." + RESET)

def option_dump_sms_call_logs():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Dumping SMS..." + RESET)
    sms_out, _ = run_cmd(f"adb -s {device} shell content query --uri content://sms/ --projection address:body:date", capture=True)
    print(sms_out)
    print(CYAN + "[*] Dumping Call Logs..." + RESET)
    call_out, _ = run_cmd(f"adb -s {device} shell content query --uri content://call_log/calls --projection number:duration:date:type", capture=True)
    print(call_out)
    save = input("Save to files? (y/n): ").lower()
    if save == 'y':
        with open("sms_logs.txt", "w") as f:
            f.write(sms_out)
        with open("call_logs.txt", "w") as f:
            f.write(call_out)
        print(GREEN + "[+] Saved to sms_logs.txt and call_logs.txt" + RESET)

def option_network_connections():
    device = get_selected_device()
    if device is None:
        return
    print(CYAN + "[*] Monitoring network connections..." + RESET)
    out, _ = run_cmd(f"adb -s {device} shell netstat", capture=True)
    if not out:
        out, _ = run_cmd(f"adb -s {device} shell cat /proc/net/tcp", capture=True)
    print(out)
# ----------------- Cyber Defence Sub-Menu -----------------
def show_cyber_menu():
    print_banner()  # Show banner in cyber menu as well
    print(GREEN + "═════ PENETRATION TESTING FEATURES ═════" + RESET)
    print()
    print(CYAN + "[1] Root Detection\n")
    print(CYAN + "[2] APK Dangerous Permissions Dump\n")
    print(CYAN + "[3] Device Security Audit\n")
    print(CYAN + "[4] Check Debuggable Apps\n")
    print(CYAN + "[5] Access Device Shell (Interactive)\n")
    print(CYAN + "[6] Network Security Check\n")
    print(CYAN + "[7] Dump SMS/Call Logs\n")
    print(CYAN + "[8] Recent Security Logs\n")
    print(CYAN + "[9] Scan for Device Vulnerabilities\n")
    print(CYAN + "[10] Network Connections Monitor\n")
    print()
    print(YELLOW + "[0] Back to Main Menu")
    print(GREEN + "══════════════════════════════════" + RESET)
    print()

def cyber_defence_mode():
    print_banner()
    print(GREEN + "[+] Cyber Security Mode Activated!" + RESET)
    while True:
        show_cyber_menu()
        choice = input(GREEN + "Select cyber option (0-8): " + RESET).strip()
        cyber_options = {
            "1": cyber_root_detection,
            "2": cyber_apk_permissions,
            "3": cyber_security_audit,
            "4": cyber_debuggable_apps,
            "5": cyber_device_shell,
            "6": cyber_network_check,
            "7": option_dump_sms_call_logs,
            "8": cyber_recent_logs,
            "9": option_scan_device_vulnerabilities,
            "10": option_network_connections,
            "0": lambda: "back"
        }
        if choice in cyber_options:
            if choice == "0":
                return
            result = cyber_options[choice]()
            if result == "back":
                return
            input("\nPress Enter to continue...")
        else:
            print(RED + "Invalid option. Please try again." + RESET)
            time.sleep(1)

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
    print(YELLOW + f"[21] Troubleshoot Connection\n\n")
    print(CYAN + f"[22] Unlock Advanced Security Tools\n")
    print(CYAN + f"[23] View Device Connection History" + RESET)
    print("\n")

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
    update_device_logs()  # Initial log
    while True:
        update_device_logs()
        print_banner()
        show_menu()
        choice = input(GREEN + "Select an option (1-23) or q to quit: " + RESET).strip().lower()
        if choice == "q":
            update_device_logs()  # Final check
            now = datetime.datetime.now()
            for dev, start in connected_devices.items():
                duration = now - start
                with open("connection_log.txt", "a") as f:
                    f.write(f"{dev} session ended at exit, connected for {duration}\n")
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
            "20": option_take_photo,
            "21": option_troubleshoot,
            "22": cyber_defence_mode,
            "23": option_view_connection_history
        }
        if choice in options:
            options[choice]()
        else:
            print(RED + "Invalid option. Choose 1-23 or q." + RESET)
        input("\nPress Enter to return to menu...")

def run():
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + CYAN + "Interrupted. Bye." + RESET)
        sys.exit(0)
run()