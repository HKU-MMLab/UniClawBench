"""
Verify/populate the Clawbench Trello board for task_101_16_trello_triage.

This script is invoked by the runner as a pre_exec hook (see
``lib/runner/pre_exec.py``) — its paths resolve against the task's
injection root (``__file__`` -> ``injection/101_skill_usage/task_101_16_trello_triage/``)
and it reads credentials from ``os.environ`` (the runner injects the
task's privacy env vars). The top-level ``ops/`` directory that used to
host populators is gone; this script ships with the task.

Deterministic shape (must stay stable for the evaluator):
  - 4 lists: Todo (todo) / Doing (in-progress) / Blocked (blocked) / Done (done)
  - 25 cards with canonical names + list assignments; 9 of them carry `due`
    timestamps anchored to today so the triage rules always fire the same
    buckets regardless of wall-clock drift.

Idempotency contract: the script always reads live state first, only
issues a PUT/POST/DELETE when the live value differs from the PLAN, and
archives orphan cards not in the PLAN.

Triage rules (must match §2 of the eval_rule and public prompt):
  urgent  — card in a non-Done list AND (due within 48h of generated_at,
            past-due, or P1/P2 client-facing with a 24/48h SLA)
  blocked — card sits in the Blocked list
  done    — card sits in the Done list
  routine — everything else
"""
from __future__ import annotations

import datetime as dt
import hashlib
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

API_KEY = os.environ.get("TRELLO_API_KEY", "")
API_TOK = os.environ.get("TRELLO_API_TOKEN", "")
# Accept either an 8-char shortLink or a 24-char hex id in the env var;
# normalize to the canonical hex id in ``main()`` because Trello's
# POST /lists rejects shortLinks in the ``idBoard`` body field even
# though GET /boards/{id} accepts either form.
BOARD_ID = os.environ.get("TRELLO_BOARD_ID", "")


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required when SNAPSHOT_MODE is not 1")
    return value

LIST_ORDER = ["Todo", "Doing", "Blocked", "Done"]
ACTIVE_LISTS = {"Todo", "Doing"}
DONE_LIST = "Done"
BLOCKED_LIST = "Blocked"
PRIORITY_WEIGHT = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}
LABEL_PLAN = {
    "P1": "red",
    "P2": "orange",
    "P3": "yellow",
    "P4": "blue",
    "client-facing": "purple",
    "internal": "green",
}
OWNERS = ["Avery", "Blair", "Casey", "Devon", "Emery", "Finley"]


# 25 canonical cards. `due_offset_h` is measured in hours from the anchor
# (today 10:00 UTC). `None` means no due date on the card.
PLAN = [
    # Todo (todo)
    {"name": "Sign client contract — Acme MSA renewal",        "list": "Todo",  "due_offset_h": 12},
    {"name": "Prepare board meeting deck (Q2 financials)",     "list": "Todo",  "due_offset_h": 36},
    {"name": "Schedule 1:1s with reports for next week",       "list": "Todo",  "due_offset_h": 120},
    {"name": "Update the team wiki landing page",              "list": "Todo",  "due_offset_h": 168},
    {"name": "Draft Q3 OKR proposal",                          "list": "Todo",  "due_offset_h": 240},
    {"name": "Clean up legacy branches on staging",            "list": "Todo",  "due_offset_h": 480},
    # Doing (in progress)
    {"name": "Review engineering hiring pipeline",             "list": "Doing", "due_offset_h": 192},
    {"name": "Refactor billing service error handling",        "list": "Doing", "due_offset_h": 240},
    {"name": "Migrate analytics dashboard to v2",              "list": "Doing", "due_offset_h": 336},
    {"name": "Audit vendor SOC2 reports",                      "list": "Doing", "due_offset_h": None},
    {"name": "Implement dark-mode toggle on settings page",    "list": "Doing", "due_offset_h": None},
    {"name": "Consolidate three Looker dashboards",            "list": "Doing", "due_offset_h": None},
    {"name": "Draft onboarding checklist for new PM",          "list": "Doing", "due_offset_h": None},
    {"name": "Write integration tests for /checkout",          "list": "Doing", "due_offset_h": None},
    # Blocked (blocked)
    {"name": "Waiting on legal review of DPA",                 "list": "Blocked",  "due_offset_h": None},
    {"name": "Blocked on AWS quota increase ticket",           "list": "Blocked",  "due_offset_h": None},
    {"name": "Need design decision from Kai on nav hierarchy", "list": "Blocked",  "due_offset_h": None},
    {"name": "Awaiting vendor response on pricing tier",       "list": "Blocked",  "due_offset_h": None},
    # Done (done)
    {"name": "Shipped feature flag for new login flow",        "list": "Done",  "due_offset_h": None},
    {"name": "Rolled out observability sampling fix",          "list": "Done",  "due_offset_h": None},
    {"name": "Closed Q1 revenue recognition review",           "list": "Done",  "due_offset_h": None},
    {"name": "Published security runbook v3",                  "list": "Done",  "due_offset_h": None},
    {"name": "Deprecated old search endpoint",                 "list": "Done",  "due_offset_h": None},
    {"name": "Completed mid-year perf calibration",            "list": "Done",  "due_offset_h": None},
    {"name": "Fixed flakey webhook retry logic",               "list": "Done",  "due_offset_h": None},
]
assert len(PLAN) == 25, f"PLAN must be 25 cards, got {len(PLAN)}"


def enrich_plan(plan: dict, index: int) -> dict:
    item = dict(plan)
    name = item["name"].lower()
    list_name = item["list"]
    if "contract" in name or "board meeting" in name or "aws quota" in name or "legal" in name:
        priority = "P1"
    elif list_name == "Blocked" or "checkout" in name or "soc2" in name or "billing" in name:
        priority = "P2"
    elif list_name == "Done":
        priority = "P4"
    elif "wiki" in name or "legacy branches" in name or "dark-mode" in name:
        priority = "P4"
    else:
        priority = "P3"
    client_facing = any(token in name for token in ["client", "contract", "vendor", "pricing", "checkout", "login"])
    owner = OWNERS[index % len(OWNERS)]
    blocker = ""
    if list_name == "Blocked":
        if "legal" in name:
            blocker = "Legal must approve the DPA language"
        elif "aws" in name:
            blocker = "AWS Support quota ticket is pending"
        elif "design" in name:
            blocker = "Kai needs to choose the nav hierarchy"
        else:
            blocker = "Vendor has not confirmed pricing tier"
    sla_hours = 24 if priority == "P1" else 48 if priority == "P2" else 168 if priority == "P3" else None
    labels = [priority, "client-facing" if client_facing else "internal"]
    item.update({
        "priority": priority,
        "owner": owner,
        "client_facing": client_facing,
        "blocker": blocker,
        "sla_hours": sla_hours,
        "labels": labels,
    })
    return item


def card_description(plan: dict) -> str:
    lines = [
        f"Owner: {plan['owner']}",
        f"Priority: {plan['priority']}",
        f"SLA hours: {plan['sla_hours'] if plan['sla_hours'] is not None else 'none'}",
        f"Workstream: {'client-facing' if plan['client_facing'] else 'internal'}",
    ]
    if plan["blocker"]:
        lines.append(f"Blocked by: {plan['blocker']}")
    return "\n".join(lines)


def api(method: str, path: str, body=None):
    q = {"key": API_KEY, "token": API_TOK}
    url = f"https://api.trello.com/1/{path}"
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}{urllib.parse.urlencode(q)}"
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, headers=hdr, data=data, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            txt = r.read().decode() or "null"
            return json.loads(txt) if txt and txt != "null" else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Trello {method} {path} -> HTTP {e.code}: {detail[:400]}") from e


def resolve_board_id(raw: str) -> str:
    board = api("GET", f"boards/{raw}")
    full_id = (board or {}).get("id")
    if not full_id:
        raise RuntimeError(f"Trello /boards/{raw} returned no id field: {board!r}")
    return full_id


def list_lists() -> list:
    return api("GET", f"boards/{BOARD_ID}/lists")


def list_cards() -> list:
    return api("GET", f"boards/{BOARD_ID}/cards")


def ensure_lists() -> dict:
    live = list_lists()
    by_name = {l["name"]: l["id"] for l in live if not l.get("closed")}
    for name in LIST_ORDER:
        if name not in by_name:
            resp = api("POST", "lists", body={"name": name, "idBoard": BOARD_ID})
            by_name[name] = resp["id"]
            print(f"  [+] list '{name}' created")
    return by_name


def ensure_labels() -> dict:
    live = api("GET", f"boards/{BOARD_ID}/labels?limit=1000") or []
    by_name = {l.get("name"): l for l in live if l.get("name")}
    for name, color in LABEL_PLAN.items():
        if name not in by_name:
            resp = api("POST", "labels", body={"name": name, "color": color, "idBoard": BOARD_ID})
            by_name[name] = resp
            print(f"  [+] label '{name}' created")
    return {name: label["id"] for name, label in by_name.items() if name in LABEL_PLAN}


def _due_iso(anchor: dt.datetime, offset_h):
    if offset_h is None:
        return None
    return (anchor + dt.timedelta(hours=offset_h)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _dues_equal(live_due, want_due):
    if live_due is None and want_due is None:
        return True
    if live_due is None or want_due is None:
        return False
    def norm(s):
        s = s.replace("Z", "+00:00")
        try:
            return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc).isoformat()
        except ValueError:
            return s
    return norm(live_due) == norm(want_due)


def set_card_labels(card: dict, wanted_label_ids: set[str]) -> None:
    current = set(card.get("idLabels") or [])
    for label_id in sorted(current - wanted_label_ids):
        api("DELETE", f"cards/{card['id']}/idLabels/{label_id}")
    for label_id in sorted(wanted_label_ids - current):
        api("POST", f"cards/{card['id']}/idLabels", body={"value": label_id})


def upsert_plan(anchor, list_by_name, label_by_name):
    cards = list_cards()
    by_name = {c["name"]: c for c in cards}
    plan_names = {p["name"] for p in PLAN}

    for index, raw_plan in enumerate(PLAN):
        plan = enrich_plan(raw_plan, index)
        want_list_id = list_by_name[plan["list"]]
        want_due = _due_iso(anchor, plan["due_offset_h"])
        want_desc = card_description(plan)
        want_label_ids = {label_by_name[name] for name in plan["labels"] if name in label_by_name}
        live = by_name.get(plan["name"])
        if live:
            need_patch = (
                live.get("idList") != want_list_id
                or not _dues_equal(live.get("due"), want_due)
                or (live.get("desc") or "") != want_desc
            )
            if need_patch:
                body = {"idList": want_list_id, "due": want_due or "", "desc": want_desc}
                api("PUT", f"cards/{live['id']}", body=body)
                print(f"  [~] {plan['name'][:48]:48s} list→{plan['list']} due→{want_due}")
            set_card_labels(live, want_label_ids)
        else:
            body = {"name": plan["name"], "idList": want_list_id, "pos": "bottom", "desc": want_desc}
            if want_due:
                body["due"] = want_due
            created = api("POST", "cards", body=body)
            if created:
                set_card_labels(created, want_label_ids)
            print(f"  [+] created: {plan['name']}")

    for c in cards:
        if c["name"] not in plan_names:
            api("PUT", f"cards/{c['id']}", body={"closed": True})
            print(f"  [-] archived orphan: {c['name']}")


def compute_bucket(item, anchor_iso):
    if item["list_name"] == DONE_LIST:
        return "done"
    if item["list_name"] == BLOCKED_LIST:
        return "blocked"
    priority = item.get("priority")
    if item["list_name"] in ACTIVE_LISTS and item.get("due"):
        anchor = dt.datetime.fromisoformat(anchor_iso.replace("Z", "+00:00"))
        due = dt.datetime.fromisoformat(item["due"].replace("Z", "+00:00"))
        if (due - anchor) <= dt.timedelta(hours=48):
            return "urgent"
    if item["list_name"] in ACTIVE_LISTS and priority in {"P1", "P2"} and item.get("client_facing") and item.get("sla_hours") in {24, 48}:
        return "urgent"
    return "routine"


def work_score(item, bucket):
    if bucket == "done":
        return -999
    score = PRIORITY_WEIGHT.get(item.get("priority"), 0)
    if bucket == "urgent":
        score += 3
    if item.get("client_facing"):
        score += 1
    if bucket == "blocked":
        score += 0.5
    return score


def _committed_id_map() -> dict:
    """Load id/short_link by canonical card name from the committed snapshot.

    SNAPSHOT_MODE=1 must produce IDs that match the committed
    sources/trello_snapshot.json (24-char hex Trello IDs) so that
    references/ground_truth.json (per_card_bucket, top_work_order,
    expected_unblockers) and the CHASE_ACTIONS lookup keep working
    after a regeneration. If the file does not exist (fresh build)
    or is malformed, we fall back to a deterministic md5-derived hex
    in snapshot_items_from_plan.
    """
    snap_path = TASK_DIR / "sources/trello_snapshot.json"
    if not snap_path.exists():
        return {}
    try:
        data = json.loads(snap_path.read_text())
    except Exception:
        return {}
    out = {}
    for it in (data.get("items") or []):
        name = it.get("name")
        if not name:
            continue
        out[name] = {"id": it.get("id"), "short_link": it.get("short_link")}
    return out


def _canonical_id(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:24]


def _canonical_short_link(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:8]


def snapshot_items_from_plan(anchor):
    id_map = _committed_id_map()
    items = []
    for idx, raw_plan in enumerate(PLAN):
        planned = enrich_plan(raw_plan, idx)
        committed = id_map.get(planned["name"], {})
        card_id = committed.get("id") or _canonical_id(planned["name"])
        short_link = committed.get("short_link") or _canonical_short_link(planned["name"])
        items.append({
            "id": card_id,
            "short_link": short_link,
            "name": planned["name"],
            "list_name": planned["list"],
            "due": _due_iso(anchor, planned["due_offset_h"]),
            "labels": planned["labels"],
            "priority": planned["priority"],
            "owner": planned["owner"],
            "client_facing": planned["client_facing"],
            "sla_hours": planned["sla_hours"],
            "blocker": planned["blocker"],
            "description": card_description(planned),
        })
    return items


def write_outputs(anchor, items=None):
    anchor_iso = anchor.strftime("%Y-%m-%dT%H:%M:%SZ")

    if items is None:
        cards = list_cards()
        lists = list_lists()
        list_by_id = {l["id"]: l["name"] for l in lists}
        items = []
        planned_by_name = {p["name"]: enrich_plan(p, idx) for idx, p in enumerate(PLAN)}
        for c in cards:
            list_name = list_by_id.get(c["idList"], "?")
            planned = planned_by_name.get(c["name"], {})
            label_names = [l.get("name") for l in c.get("labels", []) if l.get("name")]
            items.append({
                "id": c["id"],
                "short_link": c.get("shortLink"),
                "name": c["name"],
                "list_name": list_name,
                "due": c.get("due"),
                "labels": label_names or planned.get("labels", []),
                "priority": planned.get("priority"),
                "owner": planned.get("owner"),
                "client_facing": planned.get("client_facing"),
                "sla_hours": planned.get("sla_hours"),
                "blocker": planned.get("blocker", ""),
                "description": c.get("desc") or card_description(planned) if planned else c.get("desc", ""),
            })
    items.sort(
        key=lambda i: (
            LIST_ORDER.index(i["list_name"]) if i["list_name"] in LIST_ORDER else 99,
            i["name"],
        )
    )

    snapshot = {
        "board_id": BOARD_ID,
        "generated_at": anchor_iso,
        "items": items,
    }

    per_card = {}
    priority_by_card = {}
    counts = {"urgent": 0, "routine": 0, "blocked": 0, "done": 0}
    owner_load = {}
    for item in items:
        b = compute_bucket(item, anchor_iso)
        per_card[item["id"]] = b
        priority_by_card[item["id"]] = item.get("priority")
        counts[b] += 1
        owner = item.get("owner") or "Unassigned"
        owner_load.setdefault(owner, {"active": 0, "urgent": 0, "blocked": 0})
        if b != "done":
            owner_load[owner]["active"] += 1
        if b == "urgent":
            owner_load[owner]["urgent"] += 1
        if b == "blocked":
            owner_load[owner]["blocked"] += 1
    # v8 round 8: split into actionable top_work_order vs unblockers chase list.
    # top_work_order is the 8 highest-scoring cards drawn ONLY from urgent/routine
    # (so blocked cards never displace actionable items). expected_unblockers
    # carries the blocked cards separately, each with a chase_action template
    # (matched by card id below) so the executor knows what outreach to plan.
    top_work_order = [
        {
            "id": item["id"],
            "name": item["name"],
            "bucket": compute_bucket(item, anchor_iso),
            "priority": item.get("priority"),
            "score": work_score(item, compute_bucket(item, anchor_iso)),
        }
        for item in sorted(
            [i for i in items if compute_bucket(i, anchor_iso) in ("urgent", "routine")],
            key=lambda i: (
                -work_score(i, compute_bucket(i, anchor_iso)),
                i.get("due") or "9999-12-31T00:00:00.000Z",
                i["name"],
            ),
        )[:8]
    ]

    # Chase-action templates for each blocked card, keyed by card id. Kept in
    # sync with references/ground_truth.json so a fresh SNAPSHOT_MODE=1
    # regeneration produces the same expected_unblockers as the committed GT.
    CHASE_ACTIONS = {
        "69e52b39f0e2779d42fea58f": "Bump AWS Support quota ticket; CC infra lead; ask for ETA on quota grant by EOW",
        "69e52b38e877c6a9cba92472": "Email legal counsel; CC Casey; request marked-up DPA back by Friday or escalate to GC",
        "69e52b3bd87f6eec667b9dfa": "Email vendor account exec; CC procurement; request confirmed pricing tier by Friday",
        "69e52b3ac27a4bc7d6e7ba50": "Slack Kai with two nav-hierarchy options; ask for a pick by tomorrow standup or default to option A",
    }
    _priority_rank = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, None: 9}
    expected_unblockers = [
        {
            "id": item["id"],
            "name": item["name"],
            "bucket": "blocked",
            "priority": item.get("priority"),
            "chase_action": CHASE_ACTIONS.get(
                item["id"],
                f"Identify the blocker on '{item['name']}', name the owner and the unstick action, and add it to today's outreach list",
            ),
        }
        for item in sorted(
            [i for i in items if compute_bucket(i, anchor_iso) == "blocked"],
            key=lambda i: (
                _priority_rank.get(i.get("priority"), 9),
                i.get("due") or "9999-12-31T00:00:00.000Z",
                i["name"],
            ),
        )
    ]

    # Fields the populator computes / owns. These are the ONLY keys we are
    # allowed to overwrite on the inner ground_truth payload — every other
    # key (the v8 hand-authored fields like min_chase_action_chars,
    # top_4_urgent_canonical_ids, urgent_card_required_fields,
    # adversarial_urgent_card_names, etc.) must be preserved verbatim from
    # the committed references/ground_truth.json.
    populator_owned = {
        "expected_count": 25,
        "bucket_set": ["urgent", "routine", "blocked", "done"],
        "bucket_counts": counts,
        "per_card_bucket": per_card,
        "priority_by_card": priority_by_card,
        "blocked_list_name": BLOCKED_LIST,
        "done_list_name": DONE_LIST,
        "urgent_window_hours": 48,
        "top_work_order": top_work_order,
        "expected_unblockers": expected_unblockers,
    }

    # Top-level GT envelope keys this script writes. Any other top-level
    # key already on disk is preserved.
    envelope_owned = {
        "task_id": "task_101_16_trello_triage",
        "difficulty": "Medium",
        "schema": "a",
        "schema_notes": "concept-level booleans with evidence pointers (must-hit findings)",
        "skills_declared": ["trello", "summarize-pro"],
    }

    gt_path = TASK_DIR / "references/ground_truth.json"
    existing = {}
    if gt_path.exists():
        try:
            existing = json.loads(gt_path.read_text())
        except Exception:
            existing = {}

    merged_inner = dict(existing.get("ground_truth") or {})
    merged_inner.update(populator_owned)
    # Defensive: Fix C — never re-emit the stale v7 workbook_requirements
    # block. v8 dropped the xlsx requirement; references/eval_rule.md no
    # longer references it. If a previous run wrote it, drop it on merge.
    merged_inner.pop("workbook_requirements", None)

    ground_truth = dict(existing)
    ground_truth.update(envelope_owned)
    ground_truth["ground_truth"] = merged_inner

    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "references").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "sources/trello_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    gt_path.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n"
    )

    print(f"[✓] snapshot written: {len(items)} cards, anchor={anchor_iso}")
    print(f"     bucket counts: {counts}")


def main():
    global API_KEY, API_TOK, BOARD_ID
    try:
        today = dt.datetime.now(dt.timezone.utc).date()
        anchor = dt.datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=dt.timezone.utc)
        if os.environ.get("SNAPSHOT_MODE") == "1":
            BOARD_ID = "snapshot-board"
            write_outputs(anchor, snapshot_items_from_plan(anchor))
            print(f"[✓] SNAPSHOT_MODE=1: wrote snapshot + ground_truth to {TASK_DIR}")
            return "ok"

        API_KEY = require_env("TRELLO_API_KEY")
        API_TOK = require_env("TRELLO_API_TOKEN")
        BOARD_ID = require_env("TRELLO_BOARD_ID")
        BOARD_ID = resolve_board_id(BOARD_ID)

        list_by_name = ensure_lists()
        label_by_name = ensure_labels()
        upsert_plan(anchor, list_by_name, label_by_name)
        write_outputs(anchor)
        return "ok"
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] trello populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"trello": status}))
    raise SystemExit(0 if status == "ok" else 1)
