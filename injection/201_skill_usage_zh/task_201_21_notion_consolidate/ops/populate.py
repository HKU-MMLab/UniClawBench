"""
Populate Notion with an 8-page project fixture for
task_101_21_notion_consolidate.

Invoked by the runner as a pre_exec hook; resolves its injection root
from ``__file__`` and reads credentials from ``os.environ``.

Notion API requires an existing shared *parent* page — internal
integrations cannot create workspace-level pages. This script:

  1. searches for any page/database the integration can see.
  2. if nothing is shared, keeps the pre-existing synthetic snapshot.
  3. otherwise, upserts 8 child pages under the first shared container
     with deterministic titles and block contents. A second run finds
     the pages by title and skips creation.
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

TOKEN = os.environ.get("NOTION_API_TOKEN", "")
HDR = {}
DEFAULT_ROOT_PAGE_ID = "34808720-dfd4-8081-b333-d54b7fc54025"
DEFAULT_ROOT_PAGE_URL = "https://www.notion.so/ClawBench-34808720dfd48081b333d54b7fc54025?pvs=12"


def configure_auth():
    global TOKEN, HDR
    TOKEN = os.environ.get("NOTION_API_TOKEN", "")
    if not TOKEN:
        raise RuntimeError("NOTION_API_TOKEN is required when SNAPSHOT_MODE is not 1")
    HDR = {
        "Authorization": f"Bearer {TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


PAGE_PLAN = [
    {
        "page_id": "p-001",
        "title": "Kickoff",
        "blocks": [
            {"type": "heading", "text": "Kickoff — 2026-02-10"},
            {"type": "text", "text": "Attendees: Alice (TL), Bob (PM), Carol (infra), Dave (staff eng), Erin (SRE)."},
            {"type": "text", "text": "Goal: migrate the existing Python ingestion monolith to a set of Go microservices over the next two quarters, without regressing on end-to-end latency (p95 < 800ms)."},
            {"type": "bullet", "text": "Scope: ingest-api, dedup-worker, routing-service. Downstream consumers stay on the existing Kafka topics."},
            {"type": "bullet", "text": "Non-goals: replacing the object-storage layer, moving off Postgres, rewriting the Python CLI."},
            {"type": "bullet", "text": "Timeline: alpha by end of March, beta cut in mid-April, GA by mid-May."},
            {"type": "text", "text": "Risks flagged: team has limited Go experience (mitigation: pair with platform team for first month); existing Python monolith carries undocumented behavior (mitigation: shadow-traffic mirror during beta)."},
            {"type": "bullet", "text": "Initial proposal — observability ownership: Erin owns building all GA dashboards single-handed; she's our SRE so the dashboard suite naturally falls to her. (Cross-doc anchor: this proposal is later revisited in p-005 and superseded in p-007.)"},
            {"type": "bullet", "text": "Initial proposal — dedup window: a 10-minute LRU window should be enough given current re-delivery patterns. (Cross-doc anchor: revised in p-004 design draft and finalized in p-007.)"},
        ],
    },
    {
        "page_id": "p-002",
        "title": "Weekly Sync — Feb",
        "blocks": [
            {"type": "heading", "text": "Weekly Sync — 2026-02-17"},
            {"type": "text", "text": "Attendees: Alice, Bob, Carol, Dave."},
            {"type": "bullet", "text": "Agenda: queue choice, service boundaries, staffing for sprint 1."},
            {"type": "bullet", "text": "Decision: adopt Kafka as the event backbone for the new pipeline (vs. NATS or RabbitMQ) — aligns with existing downstream consumers and avoids a second operational surface."},
            {"type": "bullet", "text": "Decision: split ingest-api and dedup-worker into separate services from day 1, even though it's tempting to start with a monolith."},
            {"type": "bullet", "text": "Initial proposal — schema evolution: lean toward JSON-Schema for the on-wire event envelope; the team is already using JSON elsewhere, easier to debug. Marked tentative pending Carol's benchmark. (Cross-doc anchor: re-opened on p-005, finalized differently on p-008.)"},
            {"type": "text", "text": "Action items: Carol to spike Kafka client library choice by 2026-02-24; Dave to draft the ingest-api service contract."},
            {"type": "heading", "text": "Weekly Sync — 2026-02-24"},
            {"type": "text", "text": "Attendees: Alice, Bob, Dave, Erin."},
            {"type": "bullet", "text": "Carol's Kafka spike: recommend franz-go over confluent-kafka-go (better context.Context support, fewer cgo headaches)."},
            {"type": "bullet", "text": "Decision: use franz-go."},
        ],
    },
    {
        "page_id": "p-003",
        "title": "Weekly Sync — Mar",
        "blocks": [
            {"type": "heading", "text": "Weekly Sync — 2026-03-03"},
            {"type": "text", "text": "Attendees: Alice, Bob, Carol, Dave, Erin."},
            {"type": "bullet", "text": "Prototype ingest-api hitting 1.2k RPS on a single pod in staging — headroom to 2x with the current CPU request."},
            {"type": "bullet", "text": "Decision: use Go (golang 1.23) as the primary language for ingester and all downstream services in this workstream."},
            {"type": "bullet", "text": "Decision: deploy as a statefulset with local SSD for the dedup LRU cache (alternatives: Redis sidecar, in-memory only) — picked statefulset for cost + latency."},
            {"type": "heading", "text": "Weekly Sync — 2026-03-17"},
            {"type": "text", "text": "Attendees: Alice, Bob, Carol, Dave."},
            {"type": "bullet", "text": "Alpha rollout is a week behind; two load-test crashes tied to the franz-go batch reclaim path."},
            {"type": "bullet", "text": "Action item: Dave to open upstream issue + work around with manual flush; ship alpha 2026-03-25."},
            {"type": "bullet", "text": "Staffing: Erin rotating off for two weeks, Priya backfilling."},
        ],
    },
    {
        "page_id": "p-004",
        "title": "Design Doc: Ingester",
        "blocks": [
            {"type": "heading", "text": "Design Doc — Ingester — v2 draft"},
            {"type": "text", "text": "Author: Dave. Reviewers: Alice, Carol."},
            {"type": "bullet", "text": "Goal: accept up to 10k events/sec per region, dedup on (tenant_id, event_id), route to the right downstream topic."},
            {"type": "bullet", "text": "Architecture: HTTP/2 ingress behind an Envoy gateway → ingest-api (stateless) → dedup-worker (statefulset with a bounded LRU, 15-minute window) → router → Kafka."},
            {"type": "bullet", "text": "Revision — dedup window: superseding the 10-minute proposal from kickoff (p-001), this draft adopts a 15-minute LRU window after observing the alpha re-delivery tail. Still subject to retro feedback once beta data is in. (Cross-doc anchor: this 15-minute number is itself superseded in p-007.)"},
            {"type": "bullet", "text": "Backpressure: ingest-api returns 429 when dedup-worker lag > 5s, gateway retries with jitter."},
            {"type": "bullet", "text": "Decision: reject in-flight events older than the dedup window instead of silently letting duplicates through — safer default, callers already retry with their own idempotency keys."},
            {"type": "text", "text": "Open questions see page p-005."},
        ],
    },
    {
        "page_id": "p-005",
        "title": "Open Questions",
        "blocks": [
            {"type": "heading", "text": "Open Questions"},
            {"type": "bullet", "text": "Backpressure policy: should we drop or retry on sustained overload? Current prototype retries up to 3×, but that masks real capacity issues."},
            {"type": "bullet", "text": "Schema evolution revisit: p-002's tentative JSON-Schema lean is no longer the working assumption. Carol's benchmark shows protobuf wins on payload size and decode speed; final call deferred to a beta retro. (Cross-doc anchor: confirmed on p-008.)"},
            {"type": "bullet", "text": "Multi-region dedup: do we dedup per-region only, or is there a global guarantee we need? Currently per-region."},
            {"type": "bullet", "text": "Observability ownership revisit: p-001 said Erin alone owns dashboards; the alpha showed that's not realistic given her on-call load. Pending decision on whether to share ownership. (Cross-doc anchor: resolved on p-007.)"},
            {"type": "bullet", "text": "Runtime config: Feature flags via GrowthBook vs. env-vars-only — no decision yet."},
        ],
    },
    {
        "page_id": "p-006",
        "title": "References",
        "blocks": [
            {"type": "heading", "text": "References"},
            {"type": "link", "url": "https://kafka.apache.org/documentation/#design"},
            {"type": "link", "url": "https://github.com/twmb/franz-go"},
            {"type": "link", "url": "https://cloud.google.com/architecture/distributed-queue-patterns"},
            {"type": "link", "url": "https://aws.amazon.com/builders-library/reliability-and-constant-work/"},
            {"type": "text", "text": "Internal: the existing Python monolith lives in github.com/internal/ingestor-legacy; architecture notes in that repo's docs/ directory."},
        ],
    },
    {
        "page_id": "p-007",
        "title": "Retro — Alpha",
        "blocks": [
            {"type": "heading", "text": "Retro — Alpha (2026-03-31)"},
            {"type": "heading", "text": "What went well"},
            {"type": "bullet", "text": "Alpha shipped only one week late, despite the franz-go flush bug."},
            {"type": "bullet", "text": "Load tests caught the statefulset eviction issue before any customer traffic."},
            {"type": "bullet", "text": "Pairing with platform team for Go reviews unblocked us multiple times."},
            {"type": "heading", "text": "What to improve"},
            {"type": "bullet", "text": "We underestimated operational readiness — SRE asked for dashboards we hadn't built."},
            {"type": "bullet", "text": "Design reviews ran too long (2+ hrs) because the design doc was still in draft during review."},
            {"type": "heading", "text": "Decisions"},
            {"type": "bullet", "text": "Final decision — observability ownership: supersedes p-001 (Erin solo) and the p-005 open question. Dave and Erin co-own the GA dashboard set; Erin keeps SLO/error-budget dashboards, Dave owns ingest-pipeline saturation and franz-go internals. This is the working ownership model going into GA."},
            {"type": "bullet", "text": "Final decision — dedup window size: supersedes p-001 (10 min) and p-004 (15 min). Adopt a 20-minute LRU window for GA based on the alpha re-delivery distribution; the 15-minute draft cut off ~3% of legitimate retries. The 20-minute number is the binding GA value."},
            {"type": "heading", "text": "Actions"},
            {"type": "bullet", "text": "Dave to partner with Erin on the GA dashboard set by 2026-04-14."},
            {"type": "bullet", "text": "Alice to enforce the 'design doc fully written before review' rule for beta."},
        ],
    },
    {
        "page_id": "p-008",
        "title": "Retro — Beta",
        "blocks": [
            {"type": "heading", "text": "Retro — Beta (2026-04-18)"},
            {"type": "heading", "text": "What went well"},
            {"type": "bullet", "text": "Beta hit the performance target (p95 ingest latency: 710ms under 2x load)."},
            {"type": "bullet", "text": "Shadow-traffic diff against legacy Python ingester found only 0.03% mismatch — mostly timestamp rounding."},
            {"type": "heading", "text": "What to improve"},
            {"type": "bullet", "text": "The dedup LRU needs a proper persistence story before GA (pod restarts lose ~20 min of dedup state under the new window)."},
            {"type": "bullet", "text": "Runbook still incomplete — SRE escalated once during the first weekend."},
            {"type": "heading", "text": "Decisions"},
            {"type": "bullet", "text": "Final decision — schema evolution: supersedes p-002 (tentative JSON-Schema) and resolves the p-005 open question. Adopt protobuf for the on-wire event envelope. Carol's beta benchmark showed ~38% smaller payloads and ~2.4x faster decode versus JSON-Schema; tooling cost (codegen) is a one-time investment. This is the binding GA decision."},
            {"type": "heading", "text": "Action items"},
            {"type": "bullet", "text": "Carol to propose a snapshot-to-S3 approach for dedup LRU by 2026-04-28."},
            {"type": "bullet", "text": "Dave + Erin to close out the runbook before GA."},
        ],
    },
]


def api(method: str, path: str, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, headers=HDR, data=data, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion {method} {path} -> HTTP {e.code}: {detail[:400]}") from e


def search(filter_val: str) -> list:
    resp = api("POST", "/search", body={
        "filter": {"property": "object", "value": filter_val},
        "page_size": 50,
    })
    return resp.get("results", [])


def normalize_page_id(value: str) -> str:
    matches = re.findall(r"[0-9a-fA-F]{32}", value or "")
    if matches:
        raw = matches[-1].lower()
    else:
        raw = "".join(ch for ch in (value or "") if ch in "0123456789abcdefABCDEF").lower()
    if len(raw) != 32:
        return value
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def configured_root_parent() -> tuple[str, str] | None:
    root_id = normalize_page_id(os.environ.get("NOTION_ROOT_PAGE_ID", DEFAULT_ROOT_PAGE_ID))
    if not root_id:
        return None
    try:
        api("GET", f"/pages/{root_id}")
        return "page_id", root_id
    except Exception as exc:
        print(f"[=] configured Notion root page not usable ({root_id}): {exc}")
        return None


def first_shared_parent() -> tuple[str, str] | None:
    configured = configured_root_parent()
    if configured is not None:
        return configured
    pages = search("page")
    if pages:
        return "page_id", pages[0]["id"]
    dbs = search("database")
    if dbs:
        return "database_id", dbs[0]["id"]
    return None


def block_spec(block: dict) -> dict:
    t = block["type"]
    if t == "heading":
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
        }
    if t == "text":
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
        }
    if t == "bullet":
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
        }
    if t == "link":
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{
                "type": "text",
                "text": {"content": block["url"], "link": {"url": block["url"]}},
            }]},
        }
    raise ValueError(f"unknown block type {t}")


def ensure_pages(parent_kind: str, parent_id: str) -> list:
    existing_by_title = {}
    resp = api("POST", "/search", body={
        "filter": {"property": "object", "value": "page"},
        "page_size": 100,
    })
    for p in resp.get("results", []):
        parent = p.get("parent", {})
        if parent.get(parent_kind) != parent_id:
            continue
        title = ""
        for prop in p.get("properties", {}).values():
            if prop.get("type") == "title":
                rt = prop.get("title", [])
                if rt:
                    title = rt[0].get("plain_text", "")
        existing_by_title[title] = p["id"]

    live = []
    for plan in PAGE_PLAN:
        if plan["title"] in existing_by_title:
            page_id = existing_by_title[plan["title"]]
        else:
            parent_body = {parent_kind: parent_id}
            children = [block_spec(b) for b in plan["blocks"]]
            page = api("POST", "/pages", body={
                "parent": parent_body,
                "properties": {"title": [{"text": {"content": plan["title"]}}]},
                "children": children,
            })
            page_id = page["id"]
            print(f"  [+] {plan['title']}  ({len(children)} blocks)  -> {page_id}")
        live.append({"synthetic_id": plan["page_id"], "live_id": page_id,
                     "title": plan["title"], "blocks": plan["blocks"]})
    return live


def write_outputs(live_pages: list, root_page_id: str | None = None):
    id_map = {p["synthetic_id"]: p["live_id"] for p in live_pages}

    def remap_source_ids(value):
        if isinstance(value, dict):
            return {
                k: id_map.get(v, v) if k == "source_page_id" else remap_source_ids(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [remap_source_ids(v) for v in value]
        return value

    snapshot = {
        "generated_at": "2026-04-19T18:00:00Z",
        "project": "Platform Rewrite",
        "root": {
            "page_id": root_page_id or "snapshot-root",
            "url": DEFAULT_ROOT_PAGE_URL if root_page_id else "",
            "title": "ClawBench",
        },
        "pages": [
            {
                "page_id": p["live_id"],
                "fixture_id": p["synthetic_id"],
                "title": p["title"],
                "blocks": p["blocks"],
            }
            for p in live_pages
        ],
    }
    existing_gt = json.loads((TASK_DIR / "references/ground_truth.json").read_text(encoding="utf-8"))
    ground_truth = remap_source_ids(existing_gt)
    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "references").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "sources/notion_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    (TASK_DIR / "references/ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n"
    )


def main() -> str:
    try:
        if os.environ.get("SNAPSHOT_MODE") == "1":
            live = [
                {
                    "synthetic_id": plan["page_id"],
                    "live_id": plan["page_id"],
                    "title": plan["title"],
                    "blocks": plan["blocks"],
                }
                for plan in PAGE_PLAN
            ]
            write_outputs(live)
            print(f"[✓] SNAPSHOT_MODE=1: wrote snapshot + ground_truth to {TASK_DIR}")
            return "ok"

        configure_auth()
        parent = first_shared_parent()
        if parent is None:
            print("[=] integration has zero shared pages/databases; keeping synthetic snapshot")
            return "skipped_no_shared_parent"

        parent_kind, parent_id = parent
        print(f"[*] using shared {parent_kind}={parent_id}")
        live = ensure_pages(parent_kind, parent_id)
        write_outputs(live, parent_id if parent_kind == "page_id" else None)
        return "ok"
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] notion populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"notion": status}))
    raise SystemExit(0 if status == "ok" else 1)
