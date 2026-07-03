"""
Verify/populate the Clawbench Airtable ``Deals`` table for
task_101_22_airtable_crm.

Invoked by the runner as a pre_exec hook; resolves its injection root
from ``__file__`` and reads credentials from ``os.environ``.

Deterministic schema (must stay stable for the task evaluator):
  deal_id (string), stage (string), days_in_stage (int), value_usd (number),
  account_name (string), owner (string), contact (string)

Idempotency contract:
  1. list records via REST API.
  2. For each PLAN row, PATCH only if any tracked field diverges from
     the live record; POST when the record does not exist.
  3. Delete records with a deal_id outside PLAN.
Second run with converged state emits no writes.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import ssl
import traceback
import urllib.error
import urllib.parse
import urllib.request

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TASK_DIR = pathlib.Path(__file__).resolve().parent.parent

PAT = os.environ.get("AIRTABLE_PAT", "")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "")
TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "")

HDR = {}
TABLE_URL = ""


def configure_auth():
    global PAT, BASE_ID, TABLE_NAME, HDR, TABLE_URL
    PAT = os.environ.get("AIRTABLE_PAT", "")
    BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "")
    TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "")
    missing = [name for name, value in {
        "AIRTABLE_PAT": PAT,
        "AIRTABLE_BASE_ID": BASE_ID,
        "AIRTABLE_TABLE_NAME": TABLE_NAME,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} required when SNAPSHOT_MODE is not 1")
    HDR = {
        "Authorization": f"Bearer {PAT}",
        "Content-Type": "application/json",
    }
    TABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{urllib.parse.quote(TABLE_NAME)}"


SNAPSHOT_DATE = dt.date(2026, 4, 19)

# 64 total deals. Designed so the top-7 priority queue is obviously
# discoverable by inspection: each top-7 risk_score is materially higher
# than any non-top-7 stuck deal (smallest top-7 risk = 3360.0 vs largest
# non-top-7 stuck risk ~2400). Top-7 share the trifecta: high value
# (>=75k), late stage (Proposal/Negotiation/Qualified), and many days
# (>=42 days_in_stage).
PLAN = [
    # ===== Original anchor deals (D0001..D0033). Top-7 risk anchors
    # have been amplified so their risk_score visibly leads the pack. =====
    {"deal_id": "D0001", "stage": "Negotiation", "days_in_stage": 42, "value_usd": 80000.00, "account_name": "Acme Logistics",      "owner": "Alice P.", "contact": "Jordan Singh"},   # rank 7 risk=3360.0
    {"deal_id": "D0002", "stage": "Negotiation", "days_in_stage": 35, "value_usd": 29165.76, "account_name": "Globex Media",        "owner": "Bob K.",   "contact": "Taylor Chen"},
    {"deal_id": "D0003", "stage": "Negotiation", "days_in_stage": 18, "value_usd": 11781.15, "account_name": "Initech Retail",      "owner": "Carol M.", "contact": "Morgan Nguyen"},
    {"deal_id": "D0004", "stage": "Won",         "days_in_stage": 46, "value_usd": 64011.05, "account_name": "Hooli Fintech",       "owner": "Dave R.",  "contact": "Riley Patel"},
    {"deal_id": "D0005", "stage": "Proposal",    "days_in_stage": 50, "value_usd": 75000.00, "account_name": "Umbrella Health",     "owner": "Erin Y.",  "contact": "Casey Garcia"},   # rank 6 risk=3750.0
    {"deal_id": "D0006", "stage": "Won",         "days_in_stage": 49, "value_usd": 40982.69, "account_name": "Dunder Paper",        "owner": "Frank L.", "contact": "Avery Kim"},
    {"deal_id": "D0007", "stage": "Qualified",   "days_in_stage": 32, "value_usd": 41042.96, "account_name": "Stark Industries",    "owner": "Grace T.", "contact": "Drew O'Brien"},
    {"deal_id": "D0008", "stage": "Negotiation", "days_in_stage": 14, "value_usd": 6773.62,  "account_name": "Wayne Capital",       "owner": "Alice P.", "contact": "Sam Rossi"},
    {"deal_id": "D0009", "stage": "Lost",        "days_in_stage": 48, "value_usd": 18812.54, "account_name": "Monsters Coffee",     "owner": "Bob K.",   "contact": "Jordan Singh"},
    {"deal_id": "D0010", "stage": "Qualified",   "days_in_stage": 17, "value_usd": 46404.77, "account_name": "Pied Piper Labs",     "owner": "Carol M.", "contact": "Taylor Chen"},
    {"deal_id": "D0011", "stage": "Proposal",    "days_in_stage": 45, "value_usd": 92000.00, "account_name": "Massive Dynamic",     "owner": "Dave R.",  "contact": "Morgan Nguyen"},  # rank 5 risk=4140.0
    {"deal_id": "D0012", "stage": "Lead",        "days_in_stage": 11, "value_usd": 14404.30, "account_name": "Soylent Foods",       "owner": "Erin Y.",  "contact": "Riley Patel"},
    {"deal_id": "D0013", "stage": "Lead",        "days_in_stage": 37, "value_usd": 38130.21, "account_name": "Vandelay Imports",    "owner": "Frank L.", "contact": "Casey Garcia"},
    {"deal_id": "D0014", "stage": "Lost",        "days_in_stage": 31, "value_usd": 75018.59, "account_name": "Gekko Partners",      "owner": "Grace T.", "contact": "Avery Kim"},
    {"deal_id": "D0015", "stage": "Won",         "days_in_stage": 30, "value_usd": 55822.32, "account_name": "Cyberdyne Robotics",  "owner": "Alice P.", "contact": "Drew O'Brien"},
    {"deal_id": "D0016", "stage": "Lost",        "days_in_stage": 40, "value_usd": 32826.04, "account_name": "Tyrell Systems",      "owner": "Bob K.",   "contact": "Sam Rossi"},
    {"deal_id": "D0017", "stage": "Qualified",   "days_in_stage": 25, "value_usd": 6085.05,  "account_name": "Nakatomi Plaza",      "owner": "Carol M.", "contact": "Jordan Singh"},
    {"deal_id": "D0018", "stage": "Qualified",   "days_in_stage": 29, "value_usd": 29205.95, "account_name": "Oscorp Biotech",      "owner": "Dave R.",  "contact": "Taylor Chen"},
    {"deal_id": "D0019", "stage": "Lead",        "days_in_stage": 24, "value_usd": 23472.17, "account_name": "Wonka Confections",   "owner": "Erin Y.",  "contact": "Morgan Nguyen"},
    {"deal_id": "D0020", "stage": "Negotiation", "days_in_stage": 2,  "value_usd": 62083.15, "account_name": "Spacely Sprockets",   "owner": "Frank L.", "contact": "Riley Patel"},
    {"deal_id": "D0021", "stage": "Negotiation", "days_in_stage": 31, "value_usd": 43890.60, "account_name": "Prestige Worldwide",  "owner": "Grace T.", "contact": "Casey Garcia"},
    {"deal_id": "D0022", "stage": "Negotiation", "days_in_stage": 1,  "value_usd": 76947.00, "account_name": "Los Pollos Grp",      "owner": "Alice P.", "contact": "Avery Kim"},
    {"deal_id": "D0023", "stage": "Qualified",   "days_in_stage": 55, "value_usd": 78000.00, "account_name": "Parr Technologies",   "owner": "Bob K.",   "contact": "Drew O'Brien"},   # rank 4 risk=4290.0
    {"deal_id": "D0024", "stage": "Won",         "days_in_stage": 17, "value_usd": 48461.10, "account_name": "Hammer Industrial",   "owner": "Carol M.", "contact": "Sam Rossi"},
    {"deal_id": "D0025", "stage": "Negotiation", "days_in_stage": 22, "value_usd": 58983.17, "account_name": "Vought Media",        "owner": "Dave R.",  "contact": "Jordan Singh"},
    {"deal_id": "D0026", "stage": "Negotiation", "days_in_stage": 55, "value_usd": 88000.00, "account_name": "Sirius Cybernetics",  "owner": "Erin Y.",  "contact": "Taylor Chen"},   # rank 3 risk=4840.0
    {"deal_id": "D0027", "stage": "Qualified",   "days_in_stage": 65, "value_usd": 85000.00, "account_name": "Cogswell Cogs",       "owner": "Frank L.", "contact": "Morgan Nguyen"}, # rank 2 risk=5525.0
    {"deal_id": "D0028", "stage": "Proposal",    "days_in_stage": 70, "value_usd": 95000.00, "account_name": "Zorg Industries",     "owner": "Grace T.", "contact": "Riley Patel"},   # rank 1 risk=6650.0
    {"deal_id": "D0029", "stage": "Won",         "days_in_stage": 10, "value_usd": 74771.78, "account_name": "Rekall Travel",       "owner": "Alice P.", "contact": "Casey Garcia"},
    {"deal_id": "D0030", "stage": "Won",         "days_in_stage": 51, "value_usd": 43096.67, "account_name": "Tessier-Ashpool",     "owner": "Bob K.",   "contact": "Avery Kim"},
    {"deal_id": "D0031", "stage": "Negotiation", "days_in_stage": 22, "value_usd": 38000.00, "account_name": "Borealis Foods",      "owner": "Alice P.", "contact": "Sam Wei"},
    {"deal_id": "D0032", "stage": "Proposal",    "days_in_stage": 21, "value_usd": 27500.00, "account_name": "Hadley Logistics",    "owner": "Bob H.",   "contact": "Riya Mehta"},
    {"deal_id": "D0033", "stage": "Qualified",   "days_in_stage": 25, "value_usd": 41200.00, "account_name": "Quanta Materials",    "owner": "Diana K.", "contact": "Iris Wong"},
    # ===== New deals D0034..D0064 (31 added). Mix of moving / stuck /
    # terminal-aged / terminal-fresh. None reach top-7 risk thresholds. =====
    {"deal_id": "D0034", "stage": "Negotiation", "days_in_stage": 27, "value_usd": 24500.00, "account_name": "Helix Bio",           "owner": "Alice P.", "contact": "Priya Banerjee"},
    {"deal_id": "D0035", "stage": "Qualified",   "days_in_stage": 30, "value_usd": 33150.50, "account_name": "Lumon Industries",    "owner": "Bob K.",   "contact": "Marco Costa"},
    {"deal_id": "D0036", "stage": "Lead",        "days_in_stage": 8,  "value_usd": 7250.00,  "account_name": "Nimbus Cloud",        "owner": "Carol M.", "contact": "Hana Sato"},
    {"deal_id": "D0037", "stage": "Proposal",    "days_in_stage": 26, "value_usd": 39880.10, "account_name": "Aperture Science",    "owner": "Dave R.",  "contact": "Lena Volkov"},
    {"deal_id": "D0038", "stage": "Won",         "days_in_stage": 12, "value_usd": 28910.00, "account_name": "Veidt Enterprises",   "owner": "Erin Y.",  "contact": "Theo Park"},
    {"deal_id": "D0039", "stage": "Negotiation", "days_in_stage": 28, "value_usd": 47210.40, "account_name": "Octan Energy",        "owner": "Frank L.", "contact": "Mira Solberg"},
    {"deal_id": "D0040", "stage": "Lost",        "days_in_stage": 38, "value_usd": 22444.20, "account_name": "Wernham Hogg",        "owner": "Grace T.", "contact": "Naoki Endo"},
    {"deal_id": "D0041", "stage": "Lead",        "days_in_stage": 19, "value_usd": 15300.00, "account_name": "Bluth Bananas",       "owner": "Alice P.", "contact": "Sasha Ivanov"},
    {"deal_id": "D0042", "stage": "Qualified",   "days_in_stage": 13, "value_usd": 21785.00, "account_name": "Sterling Cooper",     "owner": "Bob K.",   "contact": "Yara Faruk"},
    {"deal_id": "D0043", "stage": "Negotiation", "days_in_stage": 35, "value_usd": 51220.00, "account_name": "Genco Pura Olive",    "owner": "Carol M.", "contact": "Devon Hart"},
    {"deal_id": "D0044", "stage": "Proposal",    "days_in_stage": 6,  "value_usd": 18620.00, "account_name": "Yoyodyne Propulsion",  "owner": "Dave R.",  "contact": "Eli Romano"},
    {"deal_id": "D0045", "stage": "Won",         "days_in_stage": 42, "value_usd": 36888.50, "account_name": "Cyberdyne Defense",   "owner": "Erin Y.",  "contact": "Anya Werner"},
    {"deal_id": "D0046", "stage": "Qualified",   "days_in_stage": 24, "value_usd": 27440.00, "account_name": "Pawnee Public",       "owner": "Frank L.", "contact": "Ravi Gupta"},
    {"deal_id": "D0047", "stage": "Negotiation", "days_in_stage": 4,  "value_usd": 33500.00, "account_name": "Vehement Capital",    "owner": "Grace T.", "contact": "Mei Lin"},
    {"deal_id": "D0048", "stage": "Lead",        "days_in_stage": 33, "value_usd": 19960.00, "account_name": "Pinwheel Toys",       "owner": "Diana K.", "contact": "Owen Brady"},
    {"deal_id": "D0049", "stage": "Proposal",    "days_in_stage": 23, "value_usd": 44100.00, "account_name": "Macrosoft Cloud",     "owner": "Bob H.",   "contact": "Lina Khalil"},
    {"deal_id": "D0050", "stage": "Lost",        "days_in_stage": 55, "value_usd": 27345.00, "account_name": "Bluestar Airlines",   "owner": "Alice P.", "contact": "Ines Ortega"},
    {"deal_id": "D0051", "stage": "Negotiation", "days_in_stage": 9,  "value_usd": 19620.00, "account_name": "Buy n Large",         "owner": "Bob K.",   "contact": "Tariq Hassan"},
    {"deal_id": "D0052", "stage": "Qualified",   "days_in_stage": 38, "value_usd": 40220.30, "account_name": "InGen Biological",    "owner": "Carol M.", "contact": "Pia Schwarz"},
    {"deal_id": "D0053", "stage": "Won",         "days_in_stage": 5,  "value_usd": 31100.00, "account_name": "Hephaestus Forge",    "owner": "Dave R.",  "contact": "Felix Andersen"},
    {"deal_id": "D0054", "stage": "Proposal",    "days_in_stage": 33, "value_usd": 36750.00, "account_name": "Wormwood & Sons",     "owner": "Erin Y.",  "contact": "Sora Hayashi"},
    {"deal_id": "D0055", "stage": "Lead",        "days_in_stage": 16, "value_usd": 12880.00, "account_name": "Plumbus Plastics",    "owner": "Frank L.", "contact": "Aiyana Chen"},
    {"deal_id": "D0056", "stage": "Negotiation", "days_in_stage": 26, "value_usd": 53420.00, "account_name": "Krusty Krab Foods",   "owner": "Grace T.", "contact": "Nikolai Petrov"},
    {"deal_id": "D0057", "stage": "Lost",        "days_in_stage": 23, "value_usd": 16200.00, "account_name": "Krusty Studios",      "owner": "Diana K.", "contact": "Beatriz Lima"},
    {"deal_id": "D0058", "stage": "Qualified",   "days_in_stage": 7,  "value_usd": 18460.00, "account_name": "Reynholm Industries", "owner": "Bob H.",   "contact": "Liam O'Connor"},
    {"deal_id": "D0059", "stage": "Won",         "days_in_stage": 25, "value_usd": 47215.00, "account_name": "Mom Friendly Robot",  "owner": "Alice P.", "contact": "Greta Halvorsen"},
    {"deal_id": "D0060", "stage": "Proposal",    "days_in_stage": 32, "value_usd": 41110.00, "account_name": "Globo Gym Fitness",   "owner": "Bob K.",   "contact": "Hans Ziegler"},
    {"deal_id": "D0061", "stage": "Negotiation", "days_in_stage": 20, "value_usd": 22980.00, "account_name": "Caldwell Brothers",   "owner": "Carol M.", "contact": "Selma Diaz"},
    {"deal_id": "D0062", "stage": "Lead",        "days_in_stage": 12, "value_usd": 9425.00,  "account_name": "Rylatech Robotics",   "owner": "Dave R.",  "contact": "Quinn Morales"},
    {"deal_id": "D0063", "stage": "Qualified",   "days_in_stage": 36, "value_usd": 30420.00, "account_name": "Tessen Galleries",    "owner": "Erin Y.",  "contact": "Jamal Idris"},
    {"deal_id": "D0064", "stage": "Lost",        "days_in_stage": 60, "value_usd": 21500.00, "account_name": "Black Mesa Research", "owner": "Frank L.", "contact": "Camille Royer"},
]
assert len(PLAN) == 64
PLAN_FIELDS = ("deal_id", "stage", "days_in_stage", "value_usd",
               "account_name", "owner", "contact")
CORE_FIELDS = {"deal_id", "stage", "days_in_stage", "value_usd"}
ACTIVE_STAGES = {"Lead", "Qualified", "Proposal", "Negotiation"}
TERMINAL_STAGES = {"Won", "Lost"}

ABSENT_FIELDS: set[str] = set()


def api(method: str, url: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, headers=HDR, data=data, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Airtable {method} -> HTTP {e.code}: {detail[:400]}") from e


def _write_record(method: str, url: str, plan_fields: dict):
    fields = {k: v for k, v in plan_fields.items() if k not in ABSENT_FIELDS}
    while True:
        try:
            return api(method, url, body={"fields": fields})
        except RuntimeError as e:
            msg = str(e)
            if "UNKNOWN_FIELD_NAME" not in msg:
                raise
            m = re.search(r'Unknown field name:\s*"([^"]+)"', msg)
            if not m:
                raise
            bad = m.group(1)
            if bad in CORE_FIELDS:
                raise
            if bad not in fields:
                raise
            del fields[bad]
            ABSENT_FIELDS.add(bad)
            print(f"  [!] Airtable table lacks column '{bad}' — "
                  f"dropping from live writes (snapshot still carries it from PLAN)")
            if not (CORE_FIELDS & set(fields)):
                raise


def list_all_records() -> list:
    out, offset = [], None
    while True:
        url = f"{TABLE_URL}?pageSize=100"
        if offset:
            url = f"{url}&offset={offset}"
        resp = api("GET", url)
        out.extend(resp.get("records", []))
        offset = resp.get("offset")
        if not offset:
            break
    return out


def fields_match(live: dict, want: dict) -> bool:
    for k in PLAN_FIELDS:
        if k in ABSENT_FIELDS:
            continue
        if live.get(k) != want.get(k):
            return False
    return True


def upsert_plan(existing: list):
    by_id = {r["fields"].get("deal_id"): r for r in existing}
    for plan in PLAN:
        rec = by_id.get(plan["deal_id"])
        if rec and fields_match(rec["fields"], plan):
            continue
        if rec:
            _write_record("PATCH", f"{TABLE_URL}/{rec['id']}", plan)
            print(f"  [~] {plan['deal_id']} updated")
        else:
            _write_record("POST", TABLE_URL, plan)
            print(f"  [+] {plan['deal_id']} created")
    plan_ids = {p["deal_id"] for p in PLAN}
    orphans = [r for r in existing if r["fields"].get("deal_id") not in plan_ids]
    for r in orphans:
        try:
            api("DELETE", f"{TABLE_URL}/{r['id']}")
            print(f"  [-] orphan {r['fields'].get('deal_id')} deleted")
        except RuntimeError as e:
            print(f"  [!] failed to delete orphan {r['id']}: {e}")


def write_outputs(rows: list):
    rows_sorted = sorted(rows, key=lambda r: r["deal_id"])
    for r in rows_sorted:
        last = SNAPSHOT_DATE - dt.timedelta(days=int(r["days_in_stage"]))
        r["last_contact_date"] = last.isoformat()
    active_pipeline_value = round(
        sum(r["value_usd"] for r in rows_sorted if r["stage"] in ACTIVE_STAGES), 2
    )
    terminal_value = round(
        sum(r["value_usd"] for r in rows_sorted if r["stage"] in TERMINAL_STAGES), 2
    )
    active_stuck = [
        r for r in rows_sorted
        if r["stage"] in ACTIVE_STAGES and int(r["days_in_stage"]) > 21
    ]
    moving_active = [
        r for r in rows_sorted
        if r["stage"] in ACTIVE_STAGES and int(r["days_in_stage"]) <= 21
    ]
    terminal_aged = [
        r for r in rows_sorted
        if r["stage"] in TERMINAL_STAGES and int(r["days_in_stage"]) > 21
    ]
    stage_counts = {}
    for r in rows_sorted:
        stage_counts[r["stage"]] = stage_counts.get(r["stage"], 0) + 1

    owner_followups = {}
    for r in active_stuck:
        owner = r["owner"]
        item = owner_followups.setdefault(owner, {
            "active_stuck_count": 0,
            "active_stuck_value_usd": 0.0,
            "oldest_active_stuck_deal": "",
            "oldest_days_in_stage": -1,
        })
        item["active_stuck_count"] += 1
        item["active_stuck_value_usd"] += float(r["value_usd"])
        if int(r["days_in_stage"]) > item["oldest_days_in_stage"]:
            item["oldest_days_in_stage"] = int(r["days_in_stage"])
            item["oldest_active_stuck_deal"] = r["deal_id"]
    for item in owner_followups.values():
        item["active_stuck_value_usd"] = round(item["active_stuck_value_usd"], 2)
    priority_queue = []
    for r in active_stuck:
        priority_queue.append({
            "deal_id": r["deal_id"],
            "account": r["account_name"],
            "owner": r["owner"],
            "stage": r["stage"],
            "value_usd": round(float(r["value_usd"]), 2),
            "days_in_stage": int(r["days_in_stage"]),
            "risk_score": round(float(r["value_usd"]) * int(r["days_in_stage"]) / 1000, 1),
        })
    priority_queue = sorted(
        priority_queue,
        key=lambda r: (-r["risk_score"], -r["days_in_stage"], r["deal_id"]),
    )[:7]
    for idx, item in enumerate(priority_queue, start=1):
        item["rank"] = idx

    snapshot = {
        "generated_at": f"{SNAPSHOT_DATE.isoformat()}T00:00:00Z",
        "table": "Deals",
        "items": rows_sorted,
        "active_pipeline_value_usd": active_pipeline_value,
        "terminal_value_usd": terminal_value,
        "total_pipeline_usd": round(active_pipeline_value + terminal_value, 2),
    }
    # Auto-derive sla_marker_required_owners as the top-2 owners by
    # oldest_days_in_stage (anchors evaluation precision on the most
    # visibly-aged stuck deals).
    sla_marker_owners = [
        owner for owner, _ in sorted(
            owner_followups.items(),
            key=lambda kv: -kv[1]["oldest_days_in_stage"],
        )[:2]
    ]
    top_priority_risk_scores = {
        item["deal_id"]: item["risk_score"]
        for item in priority_queue[:3]
    }
    ground_truth = {
        "task_id": "task_101_22_airtable_crm",
        "difficulty": "Hard",
        "schema": "a",
        "schema_notes": "concept-level booleans with evidence pointers (must-hit findings)",
        "skills_declared": ["airtable-pat-rest", "database-operations"],
        "ground_truth": {
            "total_deals": len(rows_sorted),
            "stage_stuck_threshold_days": 21,
            "active_stages": sorted(ACTIVE_STAGES),
            "terminal_stages": sorted(TERMINAL_STAGES),
            "expected_active_stuck_deal_ids": [r["deal_id"] for r in active_stuck],
            "expected_moving_active_deal_ids": [r["deal_id"] for r in moving_active],
            "expected_terminal_aged_deal_ids": [r["deal_id"] for r in terminal_aged],
            "stage_counts": stage_counts,
            "active_pipeline_value_usd": active_pipeline_value,
            "terminal_value_usd": terminal_value,
            "owner_followups_columns": [
                "owner",
                "active_stuck_count",
                "active_stuck_value_usd",
                "oldest_active_stuck_deal",
                "oldest_days_in_stage",
                "next_action",
            ],
            "expected_owner_followups": owner_followups,
            "expected_priority_queue": priority_queue,
            "topic_dimensions": [
                "active_stuck_deals",
                "owner_workload_imbalance",
                "stage_flow_bottlenecks",
                "value_at_risk_concentration",
                "lapsed_terminal_accounts",
            ],
            "min_dimensions_covered": 4,
            "sla_marker_required_owners": sla_marker_owners,
            "top_priority_risk_scores": top_priority_risk_scores,
            "moving_active_required_velocity_fields": [
                "last_stage_change_days_ago",
                "velocity_class",
            ],
            "velocity_class_thresholds": {"fast_max_days": 5, "slow_min_days": 14},
            "moving_active_min_with_velocity": 5,
            "next_action_canonical_verbs": [
                "Email", "Call", "Schedule", "Send", "Submit",
                "Review", "Confirm", "Escalate", "Follow-up", "Follow up",
            ],
            "min_owners_with_verb_action": 5,
            "min_stuck_deals_with_stage_history_length": 4,
            "min_owners_in_followups": 5,
            "min_priority_queue_match_count": 6,
        },
    }
    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "references").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "sources/airtable_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    (TASK_DIR / "references/ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n"
    )


def main() -> str:
    try:
        if os.environ.get("SNAPSHOT_MODE") == "1":
            write_outputs([dict(row) for row in PLAN])
            print(f"[✓] SNAPSHOT_MODE=1: wrote snapshot + ground_truth to {TASK_DIR}")
            return "ok"

        configure_auth()
        existing = list_all_records()
        print(f"[*] {len(existing)} existing records in {BASE_ID}/{TABLE_NAME}")
        upsert_plan(existing)

        live = list_all_records()
        if len(live) != len(PLAN):
            raise RuntimeError(f"after upsert: expected {len(PLAN)} rows, got {len(live)}")
        plan_by_id = {p["deal_id"]: p for p in PLAN}
        rows = []
        for r in live:
            f = r["fields"]
            deal_id = f["deal_id"]
            plan = plan_by_id.get(deal_id, {})
            rows.append({
                "deal_id": deal_id,
                "stage": f.get("stage", plan.get("stage")),
                "days_in_stage": int(f.get("days_in_stage", plan.get("days_in_stage"))),
                "value_usd": float(f.get("value_usd", plan.get("value_usd"))),
                "account_name": f.get("account_name", plan.get("account_name")),
                "owner": f.get("owner", plan.get("owner")),
                "contact": f.get("contact", plan.get("contact")),
            })

        write_outputs(rows)
        print(f"[✓] {len(PLAN)} rows verified and snapshot regenerated")
        return "ok"
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] airtable populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"airtable": status}))
    raise SystemExit(0 if status == "ok" else 1)
