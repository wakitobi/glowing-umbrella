wget https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/setup_grok.sh
wget https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/grok_power2b-0.1.0-cp312-cp312-linux_x86_64.whl
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
chmod +x setup_grok.sh
./setup_grok.sh
 ~/.venvs/grok-power2b/bin/grok run
