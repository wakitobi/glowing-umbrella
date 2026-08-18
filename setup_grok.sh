#!/usr/bin/env bash
# setup_grok.sh — install grok-power2b wheel on a Linux x86-64 box and (optionally) register as a systemd service.
# Usage:
#   ./setup_grok.sh [WHEEL] [THREADS] [WORKER]
#     WHEEL    path to grok_power2b-0.1.0-cp312-cp312-linux_x86_64.whl (default: ./grok_power2b-0.1.0-cp312-cp312-linux_x86_64.whl)
#     THREADS  thread count for mining, or "min,max" for randomized range (default: value baked into .env)
#     WORKER   pool worker name to write into the extracted .env, e.g. "wallet.machine2" (default: keep baked-in username)
#   Env: GROK_DATA_DIR to override runtime dir (default ~/.local/share/grok-power2b)
set -euo pipefail

WHEEL="${1:-./grok_power2b-0.1.0-cp312-cp312-linux_x86_64.whl}"
THREADS="${2:-}"
WORKER="${3:-}"
APP_NAME="grok-power2b"

# --- checks ---------------------------------------------------------------
if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "FATAL: this wheel is Linux x86-64 only (got $(uname -s)/$(uname -m))" >&2
  exit 1
fi
[[ -f "$WHEEL" ]] || { echo "FATAL: wheel not found: $WHEEL" >&2; exit 1; }

# --- python 3.12 via uv (preferred) or system python3.12 ------------------
if command -v uv >/dev/null 2>&1; then
  echo ">> using uv for the venv"
  uv venv --python 3.12 "$HOME/.venvs/$APP_NAME"
  PY="$HOME/.venvs/$APP_NAME/bin/python"
  "$PY" -m ensurepip >/dev/null 2>&1 || true
  "$HOME/.venvs/$APP_NAME/bin/pip" install --no-deps "$WHEEL"
elif command -v python3.12 >/dev/null 2>&1; then
  echo ">> using system python3.12"
  python3.12 -m venv "$HOME/.venvs/$APP_NAME"
  "$HOME/.venvs/$APP_NAME/bin/pip" install --no-deps "$WHEEL"
else
  echo "FATAL: need Python 3.12 (wheel is cp312). Install it or use uv (curl -LsSf https://astral.sh/uv/install.sh | sh)" >&2
  exit 1
fi

GROK="$HOME/.venvs/$APP_NAME/bin/grok"

# --- init: extract runtime + embedded .env ---------------------------------
echo ">> grok init"
DATA="$("$GROK" init)"
echo ">> runtime dir: $DATA"
chmod 700 "$DATA"
chmod 600 "$DATA/.env"

# --- optional per-machine worker name ---------------------------------------
if [[ -n "$WORKER" ]]; then
  echo ">> setting worker name: $WORKER"
  sed -i "s/^username=.*/username=$WORKER/" "$DATA/.env"
fi

# --- optional systemd service -------------------------------------------------
AS_SERVICE=""
if [[ "${4:-}" == "--systemd" || "${5:-}" == "--systemd" || "${6:-}" == "--systemd" ]]; then
  AS_SERVICE=1
fi

# --- threads override (only if given) ---------------------------------------
RUN_ARGS=()
if [[ -n "$THREADS" ]]; then RUN_ARGS+=("$THREADS"); fi

if [[ -n "$AS_SERVICE" ]]; then
  UNIT_DIR="$HOME/.config/systemd/user"
  mkdir -p "$UNIT_DIR"
  cat > "$UNIT_DIR/$APP_NAME.service" <<EOF
[Unit]
Description=grok power2b mining runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$GROK run ${RUN_ARGS[*]}
Restart=always
RestartSec=15

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now "$APP_NAME"
  echo ">> service installed: systemctl --user status $APP_NAME"
  echo ">> logs: journalctl --user -u $APP_NAME -f"
else
  echo
  echo "==================================================================="
  echo " INSTALL OK — runtime at: $DATA"
  echo " Start once in the foreground to confirm shares:"
  echo "   $GROK run ${RUN_ARGS[*]}"
  echo " Or install as a service:"
  echo "   ./setup_grok.sh $WHEEL $THREADS $WORKER --systemd"
  echo "==================================================================="
fi
