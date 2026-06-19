import modal

app = modal.App("hermes")

WALLET = "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t"
WORKER = "modal-h100"
GPU = "H100"
TIMEOUT = 86400

akoya_image = (
    modal.Image.from_registry(
        "registry.akoyapool.com/akoya-miner:latest",
        add_python="3.11",
    )
    .dockerfile_commands([
        "ENTRYPOINT []",
        "CMD []",
    ])
)


@app.function(
    gpu=GPU,
    image=akoya_image,
    timeout=TIMEOUT,
    scaledown_window=300,
)
def mine():
    import subprocess
    import os

    os.environ["AKOYA_POOL_WALLET"]    = WALLET
    os.environ["AKOYA_POOL_WORKER"]    = WORKER
    os.environ["AKOYA_POOL_HOST"]      = "pool-v2.akoyapool.com"
    os.environ["AKOYA_POOL_PORT"]      = "443"
    os.environ["AKOYA_POOL_USE_TLS"]   = "1"
    os.environ["AKOYA_GPU_INDICES"]    = "all"
    os.environ["AKOYA_METRICS_PORT"]   = "9100"
    os.environ["AKOYA_PEARL_GEMM_LIB"] = "/app/lib/libpearl_gemm_capi.so"
    os.environ["AKOYA_PEARL_MINING_LIB"] = "/app/lib/libpearl_mining_capi.so"

    # GPU kernel selection
    cc = subprocess.run(
        ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
        capture_output=True, text=True
    ).stdout.strip().split("\n")[0]
    major, minor = cc.split(".")
    print(f"[Modal] GPU compute: {major}.{minor}")

    lib_dir = "/app/lib"
    target = f"{lib_dir}/libpearl_gemm_capi.so"
    if int(major) == 12: src = "blackwell"
    elif int(major) == 9: src = "h100"
    elif int(major) == 8 and int(minor) == 9: src = "ada"
    else: src = "portable"

    lib_file = f"{lib_dir}/libpearl_gemm_capi_{src}.so"
    if os.path.lexists(target): os.unlink(target)
    os.symlink(lib_file, target)
    print(f"[Modal] Kernel: {src}")

    os.makedirs("/var/lib/akoya-miner", exist_ok=True)
    os.execv("/app/akoya-miner", ["/app/akoya-miner", "mine-blocks"])


@app.local_entrypoint()
def main():
    mine.remote()
