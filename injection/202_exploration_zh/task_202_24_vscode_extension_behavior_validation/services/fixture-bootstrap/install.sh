#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
need=0
for cmd in python3 curl unzip; do command -v "$cmd" >/dev/null 2>&1 || need=1; done
if [ "$need" -eq 1 ]; then apt-get update && apt-get install -y python3 curl unzip ca-certificates; fi
mkdir -p /tmp_workspace/results /tmp_workspace/sources
cp -a /tmp_workspace/injection/sources/vscode_mermaid_workspace /tmp_workspace/sources/ 2>/dev/null || true
{ echo '[bootstrap] vscode mermaid workspace fixtures'; find /tmp_workspace/sources/vscode_mermaid_workspace -maxdepth 3 -type f | sort; echo '[bootstrap] code:'; command -v code || true; } | tee /tmp_workspace/results/bootstrap.log
