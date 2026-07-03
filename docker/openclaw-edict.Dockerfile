ARG BASE_IMAGE=clawbench-openclaw:latest
FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ARG EDICT_HOME=/opt/edict

COPY downloads/edict/agents ${EDICT_HOME}/agents
COPY downloads/edict/dashboard ${EDICT_HOME}/dashboard
COPY downloads/edict/scripts ${EDICT_HOME}/scripts
COPY downloads/edict/data ${EDICT_HOME}/data
COPY downloads/edict/edict ${EDICT_HOME}/edict
COPY downloads/edict/docker/demo_data ${EDICT_HOME}/demo
COPY downloads/edict/agents.json ${EDICT_HOME}/demo/agents.json

# Round 9 / B1: bake upstream commit + version metadata into the image
# so Clawbench can report which official EDICT revision the executor
# ran (surfaced in attempt summary + WebUI badge).  Written by
# scripts/fetch_edict.sh; copied last so cache invalidation on metadata
# bump is cheap (no source tree relayer).
COPY downloads/edict/EDICT_COMMIT ${EDICT_HOME}/EDICT_COMMIT
COPY downloads/edict/EDICT_VERSION ${EDICT_HOME}/EDICT_VERSION

RUN mkdir -p ${EDICT_HOME}/logs && \
    find ${EDICT_HOME} -type f -name "*.py" -exec chmod +x {} \;

# In-container orchestrator that dispatches taizi + sub-agents via
# openclaw agent subprocesses based on kanban state. This replaces the
# external Redis-Streams-based Orchestrator + Dispatcher pair from
# cft0808/edict for our single-task-per-container benchmark case.
COPY docker/edict_orchestrator.py /usr/local/bin/edict_orchestrator.py
RUN chmod +x /usr/local/bin/edict_orchestrator.py
