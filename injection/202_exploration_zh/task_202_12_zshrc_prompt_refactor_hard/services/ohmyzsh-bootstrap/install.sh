#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
need=0
for cmd in zsh git curl script; do command -v "$cmd" >/dev/null 2>&1 || need=1; done
if [ "$need" -eq 1 ]; then apt-get update && apt-get install -y zsh git curl bsdutils; fi
if [ ! -d /root/.oh-my-zsh ]; then RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"; fi
mkdir -p /tmp_workspace/results
{ echo '[bootstrap] zsh:'; command -v zsh; echo '[bootstrap] git:'; command -v git; echo '[bootstrap] oh-my-zsh:'; ls -ld /root/.oh-my-zsh; } | tee /tmp_workspace/results/zsh_bootstrap.log
