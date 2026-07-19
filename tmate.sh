#!/usr/bin/env bash
set -euo pipefail

# ── Install tmate ──────────────────────────────────────────────
install_tmate() {
    echo "==> Detecting package manager and installing tmate..."

    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y tmate
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y tmate
    elif command -v yum &>/dev/null; then
        sudo yum install -y tmate
    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm tmate
    elif command -v brew &>/dev/null; then
        brew install tmate
    elif command -v apk &>/dev/null; then
        sudo apk add tmate
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y tmate
    else
        echo "No supported package manager found. Building from source..."
        install_from_source
        return
    fi

    echo "==> tmate installed successfully."
}

install_from_source() {
    sudo apt-get install -y git build-essential cmake \
        libevent-dev libncurses-dev zlib1g-dev 2>/dev/null || true

    local builddir
    builddir=$(mktemp -d)
    git clone https://github.com/tmate-io/tmate.git "$builddir"
    cd "$builddir"
    ./autogen.sh
    ./configure
    make -j"$(nproc)"
    sudo make install
    cd -
    rm -rf "$builddir"
    echo "==> tmate built and installed from source."
}

# ── Start a tmate session ─────────────────────────────────────
start_session() {
    echo "==> Starting tmate session..."
    echo "    A read-only and read-write URL will be printed below."
    echo "    Share the RW URL with someone you trust to access your terminal."
    echo "    Press Ctrl-D or type 'exit' to close the session."
    echo ""
    tmate
}

# ── Display connection info from an existing session ───────────
show_urls() {
    echo "==> Fetching connection URLs from running tmate session..."
    tmate display -p '#{tmate_ssh}'   2>/dev/null && \
    tmate display -p '#{tmate_ssh_ro}' 2>/dev/null && \
    tmate display -p '#{tmate_web}'   2>/dev/null
}

# ── Wait until the tmate connection is established ─────────────
wait_for_connection() {
    echo "==> Waiting for tmate to connect to tmate.io..."
    local retries=30
    while (( retries-- > 0 )); do
        if tmate display -p '#{tmate_ssh}' 2>/dev/null | grep -q '@'; then
            echo "==> Connected!"
            show_urls
            return 0
        fi
        sleep 1
    done
    echo "!! Timed out waiting for connection."
    return 1
}

# ── Start a detached session (for scripts/CI) ─────────────────
start_detached() {
    echo "==> Starting detached tmate session..."
    tmate -S /tmp/tmate.sock new-session -d
    wait_for_connection
    echo ""
    echo "Session is running in the background."
    echo "Attach with:  tmate -S /tmp/tmate.sock attach"
    echo "Kill with:    tmate -S /tmp/tmate.sock kill-server"
}

# ── Kill an existing detached session ──────────────────────────
kill_session() {
    echo "==> Killing detached tmate session..."
    tmate -S /tmp/tmate.sock kill-server 2>/dev/null && \
        echo "Session killed." || echo "No running session found."
}

# ── Usage ──────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $(basename "$0") <command>

Commands:
    install       Install tmate via system package manager or source
    start         Start an interactive tmate session
    detached      Start a background session and print connection URLs
    urls          Show URLs of an already-running detached session
    kill          Kill a detached background session
    help          Show this help message

Examples:
    $(basename "$0") install           # install tmate
    $(basename "$0") start             # interactive session
    $(basename "$0") detached          # headless / CI sharing
    $(basename "$0") urls              # check current session URLs
    $(basename "$0") kill              # tear down background session
EOF
}

# ── Main ───────────────────────────────────────────────────────
main() {
    local cmd="${1:-help}"

    case "$cmd" in
        install)  install_tmate   ;;
        start)    start_session   ;;
        detached) start_detached  ;;
        urls)     show_urls       ;;
        kill)     kill_session    ;;
        help|*)   usage           ;;
    esac
}

main "$@"
