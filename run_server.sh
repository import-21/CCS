#!/bin/bash
exec 2>>/tmp/context-server.log
echo "=== START $(date) ===" >&2
echo "ENV: HOME=$HOME PATH=$PATH" >&2

# tee で stdin を記録しつつ python3 に渡す
tee /tmp/context-server-stdin.log | python3 /home/kmnas/claude-context-server/server.py
echo "=== EXIT code=$? ===" >&2
