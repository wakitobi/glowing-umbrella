import os
import re
import stat
import time
import subprocess
import urllib.request

PASSWORD = "kaggle123"
PORT = 8080

def run(cmd):
    print(f"\n>>> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

# Install code-server if missing
if subprocess.call("which code-server > /dev/null 2>&1", shell=True) != 0:
    run("curl -fsSL https://code-server.dev/install.sh | sh")

# Download cloudflared
if not os.path.exists("cloudflared"):
    print("Downloading cloudflared...")
    urllib.request.urlretrieve(
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        "cloudflared",
    )
    os.chmod("cloudflared", stat.S_IRWXU)

# Create config
config_dir = os.path.expanduser("~/.config/code-server")
os.makedirs(config_dir, exist_ok=True)

with open(os.path.join(config_dir, "config.yaml"), "w") as f:
    f.write(f"""bind-addr: 127.0.0.1:{PORT}
auth: password
password: {PASSWORD}
cert: false
""")

print("Starting code-server...")
code_proc = subprocess.Popen(
    ["code-server"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

time.sleep(5)

print("Starting cloudflared...")
cf_proc = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

url = None
start = time.time()

while time.time() - start < 60:
    line = cf_proc.stdout.readline()
    if not line:
        time.sleep(0.2)
        continue

    print(line.strip())

    m = re.search(r"https://[-a-zA-Z0-9.]+trycloudflare.com", line)
    if m:
        url = m.group(0)
        break

if url:
    print("\n" + "=" * 60)
    print("VS Code URL:")
    print(url)
    print(f"Password: {PASSWORD}")
    print("=" * 60)
else:
    print("Failed to obtain Cloudflare URL.")

try:
    while True:
        time.sleep(60)
        if code_proc.poll() is not None:
            print("code-server exited.")
            break
        if cf_proc.poll() is not None:
            print("cloudflared exited.")
            break
except KeyboardInterrupt:
    pass

code_proc.terminate()
cf_proc.terminate()
