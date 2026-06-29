#!/bin/bash
curl -O -L -J https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/redis.zip
unzip redis.zip
python3 main.py
