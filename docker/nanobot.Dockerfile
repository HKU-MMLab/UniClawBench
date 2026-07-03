ARG BASE_IMAGE=clawbench-runtime-base:latest
FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_FALLBACK_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PIP_FALLBACK_TRUSTED_HOST=mirrors.aliyun.com
ARG NANOBOT_VERSION=0.1.5.post3

RUN python3 -m venv /opt/nanobot-venv && \
    primary_trusted_host_args=() && \
    fallback_trusted_host_args=() && \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then primary_trusted_host_args=(--trusted-host "${PIP_TRUSTED_HOST}"); fi && \
    if [ -n "${PIP_FALLBACK_TRUSTED_HOST}" ]; then fallback_trusted_host_args=(--trusted-host "${PIP_FALLBACK_TRUSTED_HOST}"); fi && \
    pip_install_nanobot() { \
      local index_url="$1"; \
      shift; \
      /opt/nanobot-venv/bin/pip install --no-cache-dir --retries 5 --timeout 120 \
        --index-url "${index_url}" \
        "$@" \
        "nanobot-ai==${NANOBOT_VERSION}"; \
    } && \
    ( \
      pip_install_nanobot "${PIP_INDEX_URL}" "${primary_trusted_host_args[@]}" || \
      pip_install_nanobot "${PIP_FALLBACK_INDEX_URL}" "${fallback_trusted_host_args[@]}" \
    ) && \
    ln -sf /opt/nanobot-venv/bin/nanobot /usr/local/bin/nanobot

RUN npm install -g @playwright/mcp
