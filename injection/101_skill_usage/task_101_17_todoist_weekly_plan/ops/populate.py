"""
Verify/populate the Clawbench Todoist account with a deterministic
25-task, 4-project layout for task_101_17_todoist_weekly_plan.

Invoked by the runner as a pre_exec hook; resolves its injection root
from ``__file__`` and reads credentials from ``os.environ`` (populated
by ``lib/runner/pre_exec.py`` from the task's privacy env file).

Idempotency contract:
  1. GET current projects + tasks.
  2. Diff each PLAN entry against the live state keyed by `content`.
  3. Only create / PATCH when the live side diverges, and only DELETE
     open tasks that are orphans (content not in PLAN) living in our
     projects. A second run is a pure no-op.

Todoist v2 REST was retired in late 2025; this uses the successor API
at ``/api/v1/`` with Bearer auth (docs: https://developer.todoist.com/api/v1).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import ssl
import traceback
import urllib.error
import urllib.parse
import urllib.request

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TASK_DIR = pathlib.Path(__file__).resolve().parent.parent

TOKEN = os.environ.get("TODOIST_API_TOKEN", "")
BASE = "https://api.todoist.com/api/v1"


def api(method: str, path: str, body=None, params=None):
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Todoist {method} {path} -> HTTP {e.code}: {detail[:400]}") from e


# Deterministic 25-task layout. `due_offset` is relative to ANCHOR_DATE
# (2026-04-25) which matches the prompt's hardcoded 7-day window
# "2026-04-25 through 2026-05-01". This ensures populate.py produces
# identical data regardless of when it runs.
ANCHOR_DATE = dt.date(2026, 4, 25)
PLAN = [
    {"id": 1000, "project": "Home",     "priority": 3, "content": "Pick up dry cleaning from the corner shop",                            "due_offset": 0, "estimated_minutes": 45},
    {"id": 1001, "project": "Work",     "priority": 3, "content": "Review Datadog alert-noise report from SRE",                          "due_offset": 1, "estimated_minutes": 90},
    {"id": 1002, "project": "Work",     "priority": 1, "content": "Sign off on vendor SOW — Acme MSA renewal",                           "due_offset": 2, "estimated_minutes": 30},
    {"id": 1003, "project": "Learning", "priority": 2, "content": "Work through SQL window-function exercises (Blau course, ch. 4)",     "due_offset": 3, "estimated_minutes": 45},
    {"id": 1004, "project": "Work",     "priority": 4, "content": "Triage the Linear backlog — close stale tickets (>90d)",              "due_offset": 4, "estimated_minutes": 15},
    {"id": 1005, "project": "Work",     "priority": 4, "content": "Archive the #eng-notes Slack DMs older than 2026-Q4",                 "due_offset": 5, "estimated_minutes": 30},
    {"id": 1006, "project": "Personal", "priority": 4, "content": "Pay Chase credit-card statement before the 30th",                     "due_offset": 6, "estimated_minutes": 15},
    {"id": 1007, "project": "Learning", "priority": 4, "content": "Read the Raft consensus paper (Ongaro & Ousterhout, 2014)",           "due_offset": 0, "estimated_minutes": 60},
    {"id": 1008, "project": "Work",     "priority": 3, "content": "Prepare the staging-rollout slide for engineering all-hands",         "due_offset": 1, "estimated_minutes": 45},
    {"id": 1009, "project": "Work",     "priority": 3, "content": "Review PR #4122 — billing idempotency fix (Priya)",                   "due_offset": 2, "estimated_minutes": 60},
    {"id": 1010, "project": "Work",     "priority": 3, "content": "Draft Q3 roadmap pre-read for Alex (1-pager)",                        "due_offset": 3, "estimated_minutes": 30},
    {"id": 1011, "project": "Work",     "priority": 1, "content": "Respond to Globex escalation ticket #8821 (latency regression)",     "due_offset": 4, "estimated_minutes": 30},
    {"id": 1012, "project": "Personal", "priority": 1, "content": "Call Walgreens about the prescription refill (Lisinopril)",           "due_offset": 5, "estimated_minutes": 30},
    {"id": 1013, "project": "Work",     "priority": 3, "content": "Unblock Priya on the OAuth → OIDC migration (ADR review)",            "due_offset": 6, "estimated_minutes": 30},
    {"id": 1014, "project": "Personal", "priority": 4, "content": "Return the Amazon jacket (wrong size) before the window closes",     "due_offset": 0, "estimated_minutes": 15},
    {"id": 1015, "project": "Learning", "priority": 1, "content": "Finish Chapter 7 of Designing Data-Intensive Applications",          "due_offset": 1, "estimated_minutes": 45},
    {"id": 1016, "project": "Learning", "priority": 4, "content": "Watch GopherCon 2024 — \"Tricks of the Trade\" talk",                 "due_offset": 2, "estimated_minutes": 60},
    {"id": 1017, "project": "Learning", "priority": 1, "content": "Submit the MIT 6.824 distributed-systems course quiz",                "due_offset": 3, "estimated_minutes": 60},
    {"id": 1018, "project": "Home",     "priority": 4, "content": "Water the fiddle-leaf + trim the two dead leaves",                    "due_offset": 4, "estimated_minutes": 60},
    {"id": 1019, "project": "Home",     "priority": 4, "content": "Take recycling + cardboard to the curb Tuesday night",                "due_offset": 5, "estimated_minutes": 60},
    {"id": 1020, "project": "Work",     "priority": 2, "content": "Reconcile the invoice mismatch with AR team (INV-20943)",             "due_offset": 6, "estimated_minutes": 45},
    {"id": 1021, "project": "Work",     "priority": 1, "content": "Prepare the board pre-read for Thursday's meeting",                   "due_offset": 0, "estimated_minutes": 60},
    {"id": 1022, "project": "Personal", "priority": 2, "content": "Check flight prices for parents' visit in June (LAX ↔ BOS)",         "due_offset": 1, "estimated_minutes": 30},
    {"id": 1023, "project": "Work",     "priority": 2, "content": "Write up 1:1 notes from Tuesday's session with Sam",                  "due_offset": 2, "estimated_minutes": 45},
    {"id": 1024, "project": "Personal", "priority": 3, "content": "Book a dentist cleaning for May (Dr. Chen's office)",                 "due_offset": 3, "estimated_minutes": 45},
]
assert len(PLAN) == 25
PROJECT_NAMES = ["Work", "Personal", "Learning", "Home"]


def _due_date_for(plan: dict) -> str:
    """Compute the actual YYYY-MM-DD due date from ANCHOR_DATE + due_offset."""
    return (ANCHOR_DATE + dt.timedelta(days=plan["due_offset"])).isoformat()


def paginated(path: str):
    cursor = None
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        page = api("GET", path, params=params)
        yield from page.get("results", [])
        cursor = page.get("next_cursor")
        if not cursor:
            return


def ensure_projects() -> dict:
    existing = {p["name"]: p for p in paginated("/projects")}
    ids = {}
    for name in PROJECT_NAMES:
        if name in existing:
            ids[name] = existing[name]["id"]
        else:
            print(f"[+] creating project {name!r}")
            p = api("POST", "/projects", body={"name": name})
            ids[name] = p["id"]
    return ids


def _live_due_date(task: dict) -> str | None:
    due = task.get("due")
    if not due:
        return None
    return due.get("date")


def _task_matches_plan(live: dict, plan: dict, project_id: str) -> bool:
    """True iff the live task already matches the PLAN in every field we
    care about — so the populator can skip the write entirely."""
    if live.get("project_id") != project_id:
        return False
    if int(live.get("priority") or 1) != plan["priority"]:
        return False
    if _live_due_date(live) != _due_date_for(plan):
        return False
    duration = live.get("duration") or {}
    if duration.get("unit") != "minute":
        return False
    if int(duration.get("amount") or 0) != plan["estimated_minutes"]:
        return False
    return True


def _update_body(plan: dict, project_id: str) -> dict:
    return {
        "content": plan["content"],
        "project_id": project_id,
        "priority": plan["priority"],
        "due_date": _due_date_for(plan),
        "duration": plan["estimated_minutes"],
        "duration_unit": "minute",
    }


def reconcile(project_ids: dict) -> list[dict]:
    """Diff live open tasks against PLAN and apply the minimal set of writes.

    Returns the canonical snapshot rows (keyed by the PLAN ids, so the
    snapshot stays stable across runs even though live Todoist hands out
    its own ids).
    """
    project_id_set = set(project_ids.values())
    live_tasks = list(paginated("/tasks"))
    live_by_content: dict[str, dict] = {}
    for t in live_tasks:
        if t.get("project_id") in project_id_set:
            live_by_content[t["content"]] = t

    plan_contents = {p["content"] for p in PLAN}
    snapshot_rows: list[dict] = []
    created = updated = unchanged = 0

    for plan in PLAN:
        proj_id = project_ids[plan["project"]]
        live = live_by_content.get(plan["content"])
        if live is None:
            api("POST", "/tasks", body=_update_body(plan, proj_id))
            created += 1
            print(f"  [+] {plan['id']} {plan['project']:8s} {plan['content'][:48]}")
        elif _task_matches_plan(live, plan, proj_id):
            unchanged += 1
        else:
            api("POST", f"/tasks/{live['id']}", body=_update_body(plan, proj_id))
            updated += 1
            print(f"  [~] {plan['id']} {plan['project']:8s} {plan['content'][:48]}")

        snapshot_rows.append({
            "id": plan["id"],
            "project": plan["project"],
            "priority": plan["priority"],
            "content": plan["content"],
            "due_date": _due_date_for(plan),
            "estimated_minutes": plan["estimated_minutes"],
        })

    # Archive (close) orphans — open tasks in our projects that aren't in PLAN.
    orphans_closed = 0
    for content, live in live_by_content.items():
        if content not in plan_contents:
            api("POST", f"/tasks/{live['id']}/close")
            orphans_closed += 1
            print(f"  [-] closed orphan: {content[:64]}")

    print(
        f"[=] reconcile summary: created={created} updated={updated} "
        f"unchanged={unchanged} orphans_closed={orphans_closed}"
    )
    return snapshot_rows


def write_outputs(rows: list[dict]):
    snapshot = {
        "generated_at": dt.datetime.utcnow().strftime("%Y-%m-%dT07:00:00Z"),
        "projects": PROJECT_NAMES,
        "items": rows,
    }
    # Group PLAN items by due_date to emit per-day P1/P2 expectations so
    # the supervisor can check the reverse priority constraint.
    by_day: dict[str, list[dict]] = {}
    for row in rows:
        by_day.setdefault(row["due_date"], []).append(row)
    per_day = []
    for day, day_rows in sorted(by_day.items()):
        p1p2 = sorted(
            (r for r in day_rows if r["priority"] in (1, 2)),
            key=lambda r: (r["priority"], -r["estimated_minutes"]),
        )
        per_day.append(
            {
                "date": day,
                "task_count": len(day_rows),
                "high_priority_tasks": [
                    {"id": r["id"], "priority": r["priority"], "content": r["content"]}
                    for r in p1p2
                ],
            }
        )
    total_minutes = sum(r["estimated_minutes"] for r in rows)
    ground_truth = {
        "task_id": "task_101_17_todoist_weekly_plan",
        "difficulty": "Medium",
        "schema": "a+b",
        "schema_notes": "accept-set structure + per-day priority expectations",
        "skills_declared": ["todoist", "plan-my-day"],
        "ground_truth": {
            "day_count": 7,
            "projects_min": 2,
            "projects_all": PROJECT_NAMES,
            "snapshot_task_count": len(rows),
            "snapshot_total_minutes": total_minutes,
            "blocks_per_day_max": 3,
            "per_day_high_priority": per_day,
            "output_requirements": {
                "markdown_path": "/tmp_workspace/results/weekly.md",
                "csv_path": "/tmp_workspace/results/weekly_schedule.csv",
                "ics_path": "/tmp_workspace/results/weekly.ics",
                "csv_required_columns": [
                    "date",
                    "start_time",
                    "end_time",
                    "duration_minutes",
                    "task_title",
                    "project",
                    "priority",
                    "due_date",
                    "reason",
                ],
                "ics_expectation": (
                    "VEVENT entries should match the scheduled CSV blocks; "
                    "summary includes task title and project, description "
                    "includes priority and due date."
                ),
                "no_overlap_required": True,
            },
            "notes": [
                "Accept-set rubric: 1-3 time blocks per day, >3 penalized.",
                "Reverse constraint: first block on a day with P1/P2 task "
                "due must point at a P1/P2 task, not P3/P4.",
                "Project coverage: ≥2 of 4 is sufficient; all 4 not required.",
                "Invented tasks not in snapshot trigger 0.60 cap.",
            ],
        },
    }
    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "references").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "sources/todoist_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    gt_path = TASK_DIR / "references/ground_truth.json"
    if gt_path.exists():
        # Preserve hand-edited GT fields; only update the time-dependent
        # per_day_high_priority section to stay in sync with the snapshot.
        existing = json.loads(gt_path.read_text())
        existing["ground_truth"]["per_day_high_priority"] = per_day
        existing["ground_truth"]["canonical_dates"] = sorted(by_day.keys())
        existing["ground_truth"]["snapshot_task_count"] = len(rows)
        existing["ground_truth"]["snapshot_total_minutes"] = total_minutes
        ground_truth = existing
    gt_path.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n"
    )


def main() -> str:
    global TOKEN
    try:
        if os.environ.get("SNAPSHOT_MODE") == "1":
            rows = [
                {
                    "id": p["id"],
                    "project": p["project"],
                    "priority": p["priority"],
                    "content": p["content"],
                    "due_date": _due_date_for(p),
                    "estimated_minutes": p["estimated_minutes"],
                }
                for p in PLAN
            ]
            write_outputs(rows)
            print(f"[✓] SNAPSHOT_MODE=1: wrote snapshot + ground_truth to {TASK_DIR}")
            return "ok"

        TOKEN = os.environ.get("TODOIST_API_TOKEN", "")
        if not TOKEN:
            raise RuntimeError("TODOIST_API_TOKEN is required when SNAPSHOT_MODE is not 1")

        project_ids = ensure_projects()
        rows = reconcile(project_ids)

        # Verify round-trip — re-fetch via API and confirm the full set.
        project_id_set = set(project_ids.values())
        ours = [t for t in paginated("/tasks") if t.get("project_id") in project_id_set]
        if len(ours) != 25:
            raise RuntimeError(f"expected 25 populated tasks, got {len(ours)}")

        write_outputs(rows)
        print(f"\n[✓] 25 tasks verified; snapshot + ground_truth written to {TASK_DIR}")
        return "ok"
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] todoist populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"todoist": status}))
    raise SystemExit(0 if status == "ok" else 1)
