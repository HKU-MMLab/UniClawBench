"""Runtime-context text injected into the executor's initial user prompt.

This is the text equivalent of a role template for the executor role:
``prompt_prefix()`` in ``lib.runner`` assembles the final prompt by
``.format()``-ing this tuple with runtime values (``results_root``,
``skill_lines``) and joining with ``"\\n"``.

Keep prompt text here rather than inlined in runner.py so the whole set
of role-prompt texts lives under ``lib/templates/``.
"""

# Placeholders:
#   {results_root}  → the RESULTS_ROOT path configured for this run
#   {skill_lines}   → already-formatted multi-line list of skill entrypoints
EXECUTOR_RUNTIME_PREFIX_LINES: tuple[str, ...] = (
    "Runtime context:",
    "- Task workspace: /tmp_workspace",
    "- IMPORTANT — SCREEN GEOMETRY: the virtual desktop is EXACTLY 1440 x 900 pixels. Origin (0, 0) is the top-left corner; bottom-right is (1439, 899). Every mouse coordinate you pass to any click / move / drag tool is interpreted in this 1440 x 900 frame — no other resolution.",
    "- Your vision pipeline may internally downsample the screenshot for efficiency (e.g. short-edge rescaled to 768). NEVER output coordinates in a downsampled frame. Always re-express every pixel coordinate in the full 1440 x 900 space BEFORE emitting a desktop tool call; if unsure, use the visible 100-pixel grid markers on the desktop, or call `get_screen_size()` from the desktop-control skill to confirm (1440, 900).",
    "- Concrete example: if a button visibly occupies the right-middle of the screen, its center is near x ≈ 1200 (not x ≈ 1024) and y ≈ 450 (not y ≈ 384). Treat x > 1024 and y > 640 as fully valid — do not clamp.",
    "- Results root: {results_root}",
    "- Save useful notes, screenshots, and other observable evidence under /tmp_workspace/results when they support your answer.",
    "- When you have fully completed the request, end your turn with a final text message stating your conclusion. Do not emit additional tool calls in that final turn.",
    "- For web / browser interactions, use the `agent-browser` CLI via the `exec` tool (see /root/skills/agent-browser-control/SKILL.md). agent-browser supports open / snapshot / click / fill / screenshot / eval and more.",
    "- `agent-browser screenshot <path>` saves to exactly that path, defaults to viewport-only PNG. Pass `--full` for full page. Prefer viewport unless evidence genuinely requires the full scrollable page.",
    "- Before clicking or typing into a control, take a fresh `agent-browser snapshot` and use the current `@eN` ref from that latest snapshot.",
    "- If built-in web_search returns missing_brave_api_key, do not stop. Continue with agent-browser navigation or the local duckduckgo-search skill.",
    "- The local DuckDuckGo fallback command is available as: duckduckgo-search 'query'.",
    "Installed skill entrypoints:",
    "{skill_lines}",
)


# Multi-line routing note prepended to the task body when agent_sys == "openclaw_edict".
EDICT_ROUTING_NOTE = "\n".join(
    [
        "EDICT routing note:",
        "- 你当前处在三省六部多 agent 体系中。",
        '- 把下面原始任务当作"皇上原话"处理，而不是普通单 agent 浏览器任务。',
        "- 如果它属于正式旨意/复杂任务，必须按太子分拣 -> 中书省 -> 门下省 -> 尚书省 -> 六部的流程推进。",
        "- 不要跳过转派流程；只有明确属于简单问答或闲聊时才可以由太子直接回复。",
        "- 需要更新看板或转交任务时，必须真实调用工具完成；不要只输出命令示例或转交说明。",
        "",
        "皇上原话：",
    ]
)


__all__ = ["EXECUTOR_RUNTIME_PREFIX_LINES", "EDICT_ROUTING_NOTE"]
