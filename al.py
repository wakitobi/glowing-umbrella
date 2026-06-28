import subprocess
import modal

image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .run_commands(
        "curl -fsSL https://code-server.dev/install.sh | sh"
    )
)

app = modal.App("vscode")

@app.function(
    image=image,
    gpu="T4",          # or modal.gpu.T4()
    timeout=60 * 60,
    cpu=1,
    memory=1192,
)
def vscode():
    with modal.forward(8080) as tunnel:
        print("VS Code:", tunnel.url)

        subprocess.run([
            "code-server",
            "--bind-addr", "0.0.0.0:8080",
            "--auth", "none",
            "/workspace",
        ])
