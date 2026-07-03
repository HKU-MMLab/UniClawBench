ARG BASE_IMAGE=docker.io/library/ubuntu:24.04
FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ARG APT_MIRROR=http://mirrors.aliyun.com/ubuntu
ARG NODE_VERSION=22.22.1
ARG NODE_DIST_MIRROR=https://npmmirror.com/mirrors/node
ARG NODE_DIST_FALLBACK_MIRROR=https://nodejs.org/dist
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG CODEX_VERSION=0.120.0

# docker-slim: bind-mount install script so its bytes never enter image history.
RUN --mount=type=bind,source=docker/install-codex-runtime.sh,target=/tmp/install-codex-runtime.sh \
    bash /tmp/install-codex-runtime.sh

RUN npm config set registry "${NPM_REGISTRY}" && \
    npm config set prefix /usr/local && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm config set fetch-timeout 600000 && \
    npm install -g "@openai/codex@${CODEX_VERSION}" && \
    npm cache clean --force

WORKDIR /work
