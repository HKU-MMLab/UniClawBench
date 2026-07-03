"""Default task_instructions string for the answer supervisor role.

Used when a task YAML does not override ``supervisor.instructions``. Kept
in the templates package alongside the role prompt itself so a future
prompt revision only touches one directory.

Scope discipline
----------------
The supervisor TEMPLATE in ``answer_supervisor.py`` already enforces the
hard contract: schema, attempt-state enum, verdict enum (``pass / continue
/ fail``), strict no-rule-invention scoring, and the framework-handles-
infra boundary. Repeating that contract here adds prompt length without
strengthening the model's behaviour and risks drift between two sources.

This default carries only the *posture supplements* the TEMPLATE doesn't
cover:

  - rationale-style guidance (focus on what is right/wrong/missing rather
    than the executor's private thinking);
  - the public/hidden boundary for ``missing_artifacts`` and rationale
    fields (no secrets, no hidden-reference verbatim copies).

Task-level overrides (``codex.supervisor.instructions``) should likewise
only supplement task-specific scoring focus — they must not redeclare the
schema / verdict enum / public-vs-hidden boundary, both because that's
the TEMPLATE's job and because task overrides drifting from the TEMPLATE
silently rewrite the contract.
"""

DEFAULT_SUPERVISOR_INSTRUCTIONS = (
    "Use `rationale` to state concrete evidence gaps, mismatches, and "
    "correctness checks. Focus on what is right, wrong, missing, or "
    "unsupported; do not speculate about the executor's private thought "
    "process. Put only safe, publicly actionable evidence gaps in "
    "`missing_artifacts`. Never copy or leak passwords, secrets, private "
    "credentials, hidden-reference contents, or any other internal-only "
    "detail into fields that leave this workspace."
)

__all__ = ["DEFAULT_SUPERVISOR_INSTRUCTIONS"]
