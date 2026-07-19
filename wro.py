#!/usr/bin/env python3
"""Download, install, and run ForgeMiner with a live progress-style display."""

import os
import re
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

DOWNLOAD_URL = (
    "https://github.com/0xHashRaptor/ForgeMiner/releases/download/"
    "v1.4.1/ForgeMiner-1.4.1-linux.tar.gz"
)
POOL = "prl.kryptex.network:7048"
ALGORITHM = "pearlhash"
WALLET = os.environ.get("MINER_WALLET", "")
WORKER = os.environ.get("MINER_WORKER", "nv")

BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_PATH = BASE_DIR / "ForgeMiner-1.4.1-linux.tar.gz"
MINER_PATH = BASE_DIR / "forge"
BAR_WIDTH = 30

HASHRATE_RE = re.compile(r"\b(?:GPU\d+|Total).*?([\d.]+)\s*(GH|TH)/s", re.I)
TEMP_RE = re.compile(r"(\d+)\s*°C")
POWER_RE = re.compile(r"(\d+)\s*W")
JOB_RE = re.compile(r"\bnew job\b", re.I)
SHARES_RE = re.compile(
    r"Shares\s+(\d+)\s+accepted\s*\|\s*(\d+)\s+stale\s*\|\s*(\d+)\s+rejected",
    re.I,
)


def download_progress(block_count, block_size, total_size):
    if total_size <= 0:
        return
    downloaded = min(block_count * block_size, total_size)
    percent = downloaded * 100 / total_size
    filled = int(BAR_WIDTH * percent / 100)
    bar = "#" * filled + "-" * (BAR_WIDTH - filled)
    sys.stdout.write(f"\rDownloading: [{bar}] {percent:6.2f}%")
    sys.stdout.flush()


def safe_extract(archive, destination):
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if os.path.commonpath((str(destination), str(target))) != str(destination):
            raise RuntimeError(f"Unsafe archive path: {member.name}")
    archive.extractall(destination)


def install_miner():
    if MINER_PATH.exists():
        return

    print(f"Downloading ForgeMiner from {DOWNLOAD_URL}")
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, ARCHIVE_PATH, download_progress)
    except Exception as error:
        print(f"\nDownload failed: {error}", file=sys.stderr)
        raise SystemExit(1)

    print("\nExtracting ForgeMiner...")
    with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
        safe_extract(archive, BASE_DIR)

    if not MINER_PATH.exists():
        raise SystemExit("The 'forge' executable was not found after extraction.")
    MINER_PATH.chmod(MINER_PATH.stat().st_mode | 0o111)


def parse_line(line, stats):
    match = HASHRATE_RE.search(line)
    if match:
        stats["hashrate"] = f"{match.group(1)} {match.group(2)}/s"
    if "°C" in line:
        match = TEMP_RE.search(line)
        if match:
            stats["temperature"] = f"{match.group(1)}°C"
    match = POWER_RE.search(line)
    if match:
        stats["power"] = f"{match.group(1)} W"
    if JOB_RE.search(line):
        stats["jobs"] += 1
    match = SHARES_RE.search(line)
    if match:
        stats["accepted"], stats["stale"], stats["rejected"] = match.groups()


def elapsed(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def render(stats, started, frame):
    position = frame % (BAR_WIDTH * 2)
    if position >= BAR_WIDTH:
        position = BAR_WIDTH * 2 - position - 1
    bar = ["-"] * BAR_WIDTH
    bar[position] = "#"
    output = (
        f"\rForgeMiner [{''.join(bar)}] {stats['hashrate']:>10} | "
        f"GPU {stats['temperature']:>5} | Power {stats['power']:>6} | "
        f"Jobs {stats['jobs']:<4} | Shares "
        f"{stats['accepted']}/{stats['stale']}/{stats['rejected']} | "
        f"{elapsed(time.monotonic() - started)}"
    )
    sys.stdout.write(output[:160].ljust(160))
    sys.stdout.flush()


def run_miner():
    command = [
        str(MINER_PATH), "--pool", POOL, "--algorithm", ALGORITHM,
        "--wallet", WALLET, "--worker", WORKER,
    ]
    stats = {
        "hashrate": "--", "temperature": "--", "power": "--", "jobs": 0,
        "accepted": "0", "stale": "0", "rejected": "0",
    }
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    def stop_miner(signum, frame):
        if process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGINT, stop_miner)
    signal.signal(signal.SIGTERM, stop_miner)
    started = time.monotonic()
    try:
        for line_number, line in enumerate(process.stdout):
            parse_line(line, stats)
            render(stats, started, line_number)
        return_code = process.wait()
    except KeyboardInterrupt:
        stop_miner(None, None)
        return_code = process.wait()
    sys.stdout.write("\n")
    print("ForgeMiner exited normally." if return_code == 0 else f"ForgeMiner exited with code {return_code}.")
    return return_code


def main():
    if not WALLET:
        print("Set the wallet first, for example:", file=sys.stderr)
        print("  MINER_WALLET=your_wallet python3 wrapper.py", file=sys.stderr)
        return 2
    install_miner()
    return run_miner()


if __name__ == "__main__":
    raise SystemExit(main())
