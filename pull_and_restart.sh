#!/bin/bash
set -e
cd "$(dirname "$0")"

git fetch origin main
if ! git diff --quiet HEAD origin/main; then
    git reset --hard origin/main
    systemctl restart gigibot.service
    systemctl restart gigiwebhook.service
fi
