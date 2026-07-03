ARG BASE_IMAGE=clawbench-runtime-base:latest
FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG ALL_PROXY=
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG OPENCLAW_VERSION=2026.3.11

ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN printf '%s\n' '[global]' 'break-system-packages = true' > /etc/pip.conf

COPY build/libsignal-node /tmp/libsignal-node

RUN export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}" && \
    export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*
# Note: openssh-client is installed in clawbench-runtime-base
# (see runtime-base.Dockerfile) and inherited here.  openclaw's
# `npm install` pulls a transitive dep (libsignal-node submodule)
# whose package-lock.json pins a ``ssh://git@github.com/...`` URL,
# so the ssh binary must be present at build time for npm's git-based
# fetch to succeed.  The git ``insteadOf`` rules below catch all three
# protocol forms (https/ssh/git@) so the fetch is short-circuited to
# the bind-mounted /tmp/libsignal-node mirror anyway, but ssh must
# exist as a fallback executable.

RUN export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}" && \
    export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}" && \
    export GIT_TERMINAL_PROMPT=0 && \
    git config --global http.version HTTP/1.1 && \
    git config --global --add url."file:///tmp/libsignal-node".insteadOf "https://github.com/whiskeysockets/libsignal-node.git" && \
    git config --global --add url."file:///tmp/libsignal-node".insteadOf "ssh://git@github.com/whiskeysockets/libsignal-node.git" && \
    git config --global --add url."file:///tmp/libsignal-node".insteadOf "git@github.com:whiskeysockets/libsignal-node.git" && \
    npm config set registry "${NPM_REGISTRY}" && \
    npm config set prefix /usr/local && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm config set fetch-timeout 600000 && \
    npm install -g "openclaw@${OPENCLAW_VERSION}" && \
    git config --global --unset-all url."file:///tmp/libsignal-node".insteadOf && \
    npm cache clean --force && \
    rm -rf /tmp/libsignal-node

RUN python3 - <<'PY'
import json
from pathlib import Path

cfg_path = Path("/root/.openclaw/openclaw.json")
cfg_path.parent.mkdir(parents=True, exist_ok=True)
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
else:
    cfg = {}
cfg.setdefault("agents", {}).setdefault("defaults", {})["workspace"] = "/tmp_workspace"
cfg["agents"]["defaults"].setdefault("model", {})["primary"] = "proxy-example/gpt-5.4"
cfg["agents"]["defaults"].setdefault("imageModel", {})["primary"] = "proxy-example/gpt-5.4"
cfg["agents"]["defaults"].pop("skills", None)
cfg.setdefault("commands", {})["nativeSkills"] = "auto"
cfg.setdefault("browser", {})["enabled"] = True
cfg["browser"]["evaluateEnabled"] = True
cfg["browser"]["executablePath"] = "/usr/local/bin/chromium"
cfg["browser"]["noSandbox"] = True
cfg.setdefault("browser", {})["ssrfPolicy"] = {
    "dangerouslyAllowPrivateNetwork": True,
    "allowedHostnames": ["localhost", "127.0.0.1"],
}
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
