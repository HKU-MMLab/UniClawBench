"""EDICT-backend (三省六部) runtime helpers.

Clawbench's ``openclaw_edict`` agent system wraps the upstream edict
multi-agent framework. The tree of agents, their role soul files, and the
allowed delegation graph are expressed as static assets under
``downloads/edict/``; this module translates those assets into the
prompt-level fragments that the runtime injects when the container boots.

Kept separate from the openclaw / container buckets so single-agent
runs don't pay the import cost and so the unit tests in
``tests/test_edict_agent_builders.py`` can exercise the AGENTS.md /
TOOLS.md rendering without any runtime state.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..defaults import RESULTS_ROOT, ROOT
from ..supervision.transcripts import EDICT_AGENT_LABELS
from ..task import TaskSpec


EDICT_RUNTIME_ROOT = "/tmp_workspace/edict"
EDICT_ASSETS_ROOT = ROOT / "downloads" / "edict"
EDICT_DEMO_DATA_ROOT = EDICT_ASSETS_ROOT / "docker" / "demo_data"
EDICT_DEMO_CONFIG = EDICT_DEMO_DATA_ROOT / "openclaw.json"
EDICT_AGENTS_ROOT = EDICT_ASSETS_ROOT / "agents"
EDICT_GLOBAL_MD = EDICT_AGENTS_ROOT / "GLOBAL.md"
EDICT_GROUPS_ROOT = EDICT_AGENTS_ROOT / "groups"
EDICT_SCRIPTS_ROOT = EDICT_ASSETS_ROOT / "scripts"
EDICT_DATA_ROOT = EDICT_ASSETS_ROOT / "data"
EDICT_BACKEND_MODELS_ROOT = EDICT_ASSETS_ROOT / "edict" / "backend" / "app" / "models"

# Round 9 / B1+B3: scripts/fetch_edict.sh writes these alongside the
# extracted upstream tree.  Used by build to bake the same files into
# /opt/edict/ in the image, and by task_summary_base to label which
# upstream revision the attempt ran against.
EDICT_COMMIT_FILE = EDICT_ASSETS_ROOT / "EDICT_COMMIT"
EDICT_VERSION_FILE = EDICT_ASSETS_ROOT / "EDICT_VERSION"

# Round 9 / B3: tag for the adapter strategy.  Records that we feed
# the upstream cft0808/edict specs (SOUL.md / agents.json) into a
# single-process Clawbench orchestrator (docker/edict_orchestrator.py)
# rather than the upstream Postgres + Redis Streams Dispatcher pair.
# Surfaced in attempt summary so reviewers know what they're looking at.
EDICT_MODE = "official_specs_local_adapter"
EDICT_DEMO_SEED_FILES = [
    "agent_config.json",
    "last_model_change_result.json",
    "live_status.json",
    "model_change_log.json",
    "morning_brief.json",
    "officials_stats.json",
    "pending_model_changes.json",
    "tasks_source.json",
]


def read_edict_runtime_metadata() -> dict[str, str]:
    """Resolve the EDICT upstream commit/version metadata for summary
    fields.  Reads the host-side ``downloads/edict/EDICT_COMMIT`` and
    ``EDICT_VERSION`` files written by ``scripts/fetch_edict.sh``.

    These files are mirrored into the image at ``/opt/edict/EDICT_*``
    by ``docker/openclaw-edict.Dockerfile``, so they identify the
    upstream revision the executor actually ran against.  When the
    files are missing (older snapshot pre-Round-9-B1), returns "unknown"
    placeholders so downstream consumers don't have to special-case.
    """
    def _read(path: Path, default: str) -> str:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            return default
        return value or default

    return {
        "mode": EDICT_MODE,
        "commit": _read(EDICT_COMMIT_FILE, "unknown"),
        "version": _read(EDICT_VERSION_FILE, "unknown"),
    }


def edict_agent_specs() -> list[dict]:
    if not EDICT_DEMO_CONFIG.exists():
        return []
    payload = json.loads(EDICT_DEMO_CONFIG.read_text(encoding="utf-8"))
    agents = ((payload.get("agents") or {}).get("list")) or []
    return [item for item in agents if isinstance(item, dict) and item.get("id")]


def edict_agent_ids() -> list[str]:
    ids: list[str] = []
    for spec in edict_agent_specs():
        agent_id = str(spec.get("id") or "").strip()
        if agent_id and agent_id not in ids:
            ids.append(agent_id)
    return ids


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def edict_agent_group(agent_id: str) -> str:
    if agent_id in {"taizi", "zhongshu", "menxia", "shangshu"}:
        return "sansheng"
    if agent_id in {"hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"}:
        return "liubu"
    return ""


def edict_repo_dir_for_task(task: TaskSpec) -> str:
    sources_root = "/tmp_workspace/clawbench/sources"
    if len(task.sources) == 1:
        return f"{sources_root}/{task.sources[0]}"
    return sources_root


def render_edict_soul(agent_id: str, task: TaskSpec) -> str:
    soul_path = EDICT_AGENTS_ROOT / agent_id / "SOUL.md"
    soul = read_text_if_exists(soul_path)
    if not soul:
        return ""
    return soul.replace("__REPO_DIR__", edict_repo_dir_for_task(task))


def build_edict_tools_md(agent_id: str) -> str:
    allowed = []
    for spec in edict_agent_specs():
        if spec.get("id") == agent_id:
            allowed = [str(item).strip() for item in (((spec.get("subagents") or {}).get("allowAgents")) or []) if str(item).strip()]
            break
    lines = [
        "# TOOLS.md · EDICT Runtime",
        "",
        "## Hard Rules",
        "- 需要执行命令时，必须真实调用 `exec` 工具；不要只把 bash/python 命令写在回复里。",
        '- 需要跨 agent 传递任务时，必须真实调用 `sessions_send` 或 `sessions_spawn`；不要只写"已转交中书省/尚书省"。',
        "- 代码块、命令示例、计划说明都不算执行。",
        "",
        "## Tool Mapping",
        "- 更新看板：`exec` -> `python3 scripts/kanban_update.py ...`",
        "- 太子或六部向其他主会话转交：`sessions_send`，目标 session key 形如 `agent:<agent_id>:main`",
        "- 需要拉起子 agent 完成子任务：使用 `sessions_spawn`，**必须显式传 `mode: \"run\"`**。",
        "  - 例：`sessions_spawn(task: \"...\", agentId: \"zhongshu\", mode: \"run\")`",
        "  - **禁止**传 `thread: true` 或 `mode: \"session\"`，当前 runtime 不支持 thread 绑定。",
        "- 转交后继续检查返回结果，不要只发出一次消息就结束。",
        # Browser entry point — applies to every agent and every subagent.
        # Clawbench disables openclaw's native `browser` MCP tool, so the
        # ONLY supported way to drive a browser is the `agent-browser` CLI
        # invoked via `exec`. Upstream edict SOUL/TOOLS docs don't know
        # about this; without this block, subagents that inherit only the
        # upstream rules fall back to fabricating HTML / refusing to
        # browse, which is exactly what happened in our first edict run.
        "- 浏览 / 网页操作：`exec` -> `agent-browser <sub-command>`。**openclaw 自带的 `browser` MCP 工具已被 Clawbench 关闭，不要调用它、也不要假设它存在。**",
        "  - 常用：`agent-browser open <url>` / `click @eN` / `fill @eN <text>` / `snapshot` / `screenshot <path>` / `eval '<js>'`",
        "  - 每次 `click`/`fill` 前都要重新 `snapshot`，用最新的 `@eN` ref；不要复用过期 ref。",
        "  - 截图固定 `agent-browser screenshot /tmp_workspace/results/<name>.png`；需要整页加 `--full`，默认 viewport 即可。",
        "  - 见 `/root/skills/agent-browser-control/SKILL.md` 获得完整子命令列表。",
        '- 当你通过 `sessions_spawn` 派发子任务时，**必须在 task 文本里显式写明"浏览器走 `agent-browser` CLI，不要用 MCP `browser` 工具"**，否则子 agent 很可能错用已被禁用的原生工具。',
    ]
    if allowed:
        lines.extend(["", "## Allowed Downstream Agents", *[f"- `{agent_id}` -> `{target}`" for target in allowed]])
    return "\n".join(lines).strip() + "\n"


def build_edict_agents_md(agent_id: str, task: TaskSpec) -> str:
    label = EDICT_AGENT_LABELS.get(agent_id, agent_id)
    group_name = edict_agent_group(agent_id)
    sections = [
        f"# AGENTS.md · EDICT Runtime · {label}",
        "",
        "你运行在 Clawbench 的三省六部 runtime 中。",
        "无论是主会话还是 subagent 会话，都把本文件当作最高优先级的工作协议。",
        "",
        "## Runtime Paths",
        f"- 共享 EDICT 根目录：`{EDICT_RUNTIME_ROOT}`",
        f"- 项目源码根目录：`{edict_repo_dir_for_task(task)}`",
        f"- Benchmark 结果目录：`{RESULTS_ROOT}`",
        "- 看板 CLI：`python3 scripts/kanban_update.py ...`",
        "- 看板数据文件：`data/tasks_source.json`",
        "- 如果需要跨 agent 协作，使用 `sessions_send` 或 `sessions_spawn`，并遵守 allowAgents 权限矩阵。",
        "- 使用 `sessions_spawn` 拉起子 agent 时，**必须显式传 `mode: \"run\"`**，禁止使用 `thread: true` 或 `mode: \"session\"`。",
        "- 任何 CLI/协作动作都必须真实调用工具完成；不要把命令写成回复内容来替代执行。",
        "",
        # Clawbench-specific browser rule — upstream edict agents assume
        # a native `browser` MCP tool; Clawbench disables that tool and
        # only supports `agent-browser` CLI. Without this section,
        # subagents that get only the upstream SOUL/GLOBAL rules default
        # to the disabled MCP tool and silently fabricate evidence.
        "## Clawbench Runtime Addendum",
        "- **浏览器只走 `agent-browser` CLI**。openclaw 的原生 `browser` MCP 工具在 Clawbench 已关闭，直接调用会报 tool disabled。",
        "  - 入口：`exec` -> `agent-browser open <url>` / `agent-browser snapshot` / `agent-browser click @eN` / `agent-browser fill @eN <text>` / `agent-browser screenshot /tmp_workspace/results/<name>.png` / `agent-browser eval '<js>'`",
        "  - 使用前先读 `/root/skills/agent-browser-control/SKILL.md` 确认最新子命令。",
        '- 证据统一保存到 `/tmp_workspace/results/`（同 `Benchmark 结果目录`），文件名要描述性；**不要**把用户给的测试指令或评判规则当作"已经自己完成"。',
        "- 当你通过 `sessions_spawn` 派发执行型任务（尤其是需要浏览网页的）时，**必须在 task 文本里复述上面两条规则**，以免被派出去的子 agent 以为没有可用浏览器、转而用 `curl`/HTML 抓取拼凑假证据。",
    ]
    global_rules = read_text_if_exists(EDICT_GLOBAL_MD).strip()
    if global_rules:
        sections.extend(["", "## Shared Global Rules", "", global_rules])
    if group_name:
        group_rules = read_text_if_exists(EDICT_GROUPS_ROOT / f"{group_name}.md").strip()
        if group_rules:
            sections.extend(["", f"## Group Rules · {group_name}", "", group_rules])
    soul = render_edict_soul(agent_id, task).strip()
    if soul:
        sections.extend(["", "## Role Rules", "", soul])
    return "\n".join(part.rstrip() for part in sections if part is not None).strip() + "\n"
