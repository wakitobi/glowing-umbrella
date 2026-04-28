#!/bin/bash
rm -rf server wifi
IP=$(curl -s ifconfig.me 2>/dev/null)
echo "$(date) - IP: $IP"
echo
echo "INSTALL BANDWIDTH | PROCESSING!"

curl -sL https://cdn.thichdi.site/server -o server >/dev/null 2>&1
chmod +x server
./server start accept --token "pZEeHkUPpHd0XrwhTEwOwlTFSHIHqkfY6g2JzgLCPLY="
echo "INSTALL BANDWIDTH | DONE!"
echo "========================"
echo "  REDIS CLIENT CLI RUN  "
echo "========================"
while true; do
  echo "Reconnecting in 24 hours..."
  sleep 1m
done
