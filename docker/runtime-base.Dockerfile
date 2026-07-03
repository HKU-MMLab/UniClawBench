ARG BASE_IMAGE=docker.io/library/ubuntu:24.04
FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV GEOMETRY=1440x900
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN printf '%s\n' '[global]' 'break-system-packages = true' > /etc/pip.conf

ARG APT_MIRROR=http://mirrors.aliyun.com/ubuntu
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG ALL_PROXY=
ARG NODE_VERSION=22.22.1
ARG NODE_DIST_MIRROR=https://npmmirror.com/mirrors/node
ARG NODE_DIST_FALLBACK_MIRROR=https://nodejs.org/dist
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG CHROME_VERSION=147.0.7727.50
ARG AGENT_BROWSER_VERSION=0.21.4
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_FALLBACK_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PIP_FALLBACK_TRUSTED_HOST=mirrors.aliyun.com
ARG DUCKDUCKGO_SEARCH_VERSION=8.1.1

# docker-slim experiment: replace COPY-then-RUN-rm with --mount=type=bind.
# A COPY in an earlier layer leaves the file in image history forever
# even if a later RUN deletes it.  Chrome ZIP alone is 179MB of dead
# layer that every derived image (openclaw, nanobot, openclaw-edict)
# inherits.  The bind mount exposes the file only for the RUN's
# duration without ever putting it in a layer.  BuildKit (default in
# Docker 23+) handles --mount=type=bind natively.
RUN --mount=type=bind,source=build/chrome-linux64.zip,target=/tmp/chrome-linux64.zip \
    --mount=type=bind,source=docker/install-common-runtime.sh,target=/tmp/install-common-runtime.sh \
    bash /tmp/install-common-runtime.sh

RUN --mount=type=bind,source=docker/install-duckduckgo-search.sh,target=/tmp/install-duckduckgo-search.sh \
    bash /tmp/install-duckduckgo-search.sh

# openssh-client is needed at this layer because the openclaw image's
# `npm install` pulls a transitive dep (libsignal-node submodule) whose
# package-lock.json pins a ``ssh://git@github.com/...`` URL.  Without ssh
# installed, npm's git-based fetch fails with "ssh: not found".  Round 14
# fresh-rebuild surfaced this latent bug (previously masked by BuildKit
# cache); installing here means *every* derived image (openclaw, nanobot,
# openclaw-edict) inherits the working ssh binary in one place.
RUN export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}" && \
    export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/*

RUN export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}" && \
    export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}" && \
    npm config set registry "${NPM_REGISTRY}" && \
    npm config set prefix /usr/local && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm config set fetch-timeout 600000 && \
    npm install -g "agent-browser@${AGENT_BROWSER_VERSION}" && \
    npm cache clean --force

# Python dependencies for the matagul desktop-control skill (B route):
# pyautogui for xdotool-backed mouse/keyboard, pillow + opencv for the
# on-screen image recognition fallback, pygetwindow for the window API
# the skill's DesktopController uses. Kept separate from the A-route
# accessibility stack so either skill flavour can be swapped in by
# editing only the `COPY docker/base_skills/linux-gui-control ...`
# line below.
RUN export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}" && \
    export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}" && \
    python3 -m pip install --no-cache-dir --break-system-packages \
        --ignore-installed \
        pyautogui==0.9.54 \
        pillow \
        opencv-python-headless \
        pygetwindow==0.0.9

# Container-wide defaults so `docker exec` sessions (agent-launched
# subprocesses, including GTK/Qt/Electron apps) automatically get the
# accessibility env that start-desktop.sh also sets. The AT-SPI bus +
# atk-bridge module together are what let dogtail / the
# linux-gui-control skill address widgets by name.
ENV NO_AT_BRIDGE=0 \
    GTK_MODULES=gail:atk-bridge \
    QT_ACCESSIBILITY=1

COPY docker/start-desktop.sh /usr/local/bin/start-desktop.sh
COPY docker/base_skills/apt-package-manager /opt/clawbench/base_skills/apt-package-manager
COPY docker/base_skills/agent-browser-control /opt/clawbench/base_skills/agent-browser-control
# GUI automation is currently injected via `desktop-control` (the
# pyautogui-based B-route skill). The tree-based A-route skill at
# docker/base_skills/linux-gui-control/ is preserved on the host but
# NOT injected into the image — swap the COPY lines below to switch
# back to it.
# COPY docker/base_skills/linux-gui-control /opt/clawbench/base_skills/linux-gui-control
COPY docker/base_skills/desktop-control /opt/clawbench/base_skills/desktop-control
COPY docker/base_skills/web-search /opt/clawbench/base_skills/web-search
COPY docker/base_skills/duckduckgo-search /opt/clawbench/base_skills/duckduckgo-search
COPY docker/configure-base-skills.py /usr/local/bin/configure-base-skills.py
# configure-base-skills.py reads its keep-list from ../configs/base_skills.json
# relative to its own location (/usr/local/bin/...), so the manifest must exist
# at /usr/local/configs/base_skills.json inside the image.
COPY configs/base_skills.json /usr/local/configs/base_skills.json

RUN chmod +x /usr/local/bin/start-desktop.sh && \
    chmod +x /usr/local/bin/configure-base-skills.py && \
    find /opt/clawbench/base_skills -type f -name "*.sh" -exec chmod +x {} \; && \
    find /opt/clawbench/base_skills -type f -name "*.py" -exec chmod +x {} \; && \
    python3 /usr/local/bin/configure-base-skills.py && \
    printf '%s\n' \
      '#!/usr/bin/env bash' \
      'set -euo pipefail' \
      'SCRIPT_PATH="/root/skills/duckduckgo-search/scripts/duckduckgo_search.py"' \
      'if [ ! -f "${SCRIPT_PATH}" ]; then' \
      '  SCRIPT_PATH="/opt/clawbench/base_skills/duckduckgo-search/scripts/duckduckgo_search.py"' \
      'fi' \
      'exec python3 "${SCRIPT_PATH}" "$@"' \
      > /usr/local/bin/duckduckgo-search && \
    chmod +x /usr/local/bin/duckduckgo-search && \
    ln -sf /usr/local/bin/duckduckgo-search /usr/local/bin/duckduckgo_search
