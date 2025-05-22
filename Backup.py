import os
import shutil
from ping3 import ping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configuration
ip_range = range(1, 255)
folders_to_backup = [r"C$\important", r"C$\temp"]
exclude_files = {"main.log", "error.log"}
exclude_subfolders = {os.path.normpath(r"temp\dont_copy")}
server_backup_root = r"\\myserver\backup_week1"

def is_online(ip):
    try:
        return ping(ip, timeout=1) is not None
    except:
        return False

def should_exclude(path):
    norm_path = os.path.normpath(path).lower()
    return any(ex in norm_path for ex in exclude_subfolders) or os.path.basename(path).lower() in exclude_files

def copy_if_newer(src_file, dst_file):
    if os.path.exists(dst_file):
        if os.path.getmtime(src_file) <= os.path.getmtime(dst_file):
            return
    shutil.copy2(src_file, dst_file)

def backup_folder(ip, folder_path):
    unc_path = os.path.join(f"\\\\{ip}", folder_path)
    if not os.path.exists(unc_path):
        print(f"[{ip}] Cannot access {unc_path}")
        return

    for root, dirs, files in os.walk(unc_path):
        rel_root = os.path.relpath(root, unc_path)
        if should_exclude(rel_root):
            continue

        backup_root = os.path.join(server_backup_root, ip, os.path.basename(folder_path), rel_root)
        os.makedirs(backup_root, exist_ok=True)

        for file in files:
            if should_exclude(file):
                continue
            src_file = os.path.join(root, file)
            dst_file = os.path.join(backup_root, file)
            try:
                copy_if_newer(src_file, dst_file)
            except Exception as e:
                print(f"[{ip}] Error copying {src_file}: {e}")

def handle_ip(ip):
    print(f"[{ip}] Checking...")
    if not is_online(ip):
        print(f"[{ip}] Offline.")
        return
    print(f"[{ip}] Online. Backing up...")

    for folder in folders_to_backup:
        backup_folder(ip, folder)

def main():
    with ThreadPoolExecutor(max_workers=10) as executor:
        ips = [f"192.168.1.{i}" for i in ip_range]
        executor.map(handle_ip, ips)

if __name__ == "__main__":
    main()
