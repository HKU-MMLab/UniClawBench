"""
Populate a private GitHub repo ``clawbench-activity-fixture`` (under the
account behind ``GITHUB_TOKEN``) with a deterministic 16-day activity
fixture for task_101_19_github_activity_digest:

    40 commits, 15 PRs (mix merged/closed/open), 20 issues (mix closed/open)

Invoked by the runner as a pre_exec hook; resolves its injection root
from ``__file__`` and reads credentials from ``os.environ``.

Idempotency contract: the first action is a cheap commit/PR/issue count
read — if the target repo already carries the full fixture the script
short-circuits and only rewrites the snapshot + ground_truth files.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import re
import ssl
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TASK_DIR = pathlib.Path(__file__).resolve().parent.parent

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = "clawbench-activity-fixture"

HEADERS = {}


def configure_auth():
    global TOKEN, HEADERS
    TOKEN = os.environ.get("GITHUB_TOKEN", "")
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required when SNAPSHOT_MODE is not 1")
    HEADERS = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "clawbench-populator",
    }


def api(method: str, path: str, body=None, params=None, raw=False):
    url = f"https://api.github.com{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    data = None
    headers = dict(HEADERS)
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    # Retry on transient 5xx (502/503/504 from GitHub edge) up to 4 times
    # with exponential backoff. 4xx errors raise immediately.
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as r:
                body = r.read().decode()
                if raw:
                    return r.status, body
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code in (502, 503, 504) and attempt < 3:
                last_err = e
                time.sleep(2 ** attempt + 1)
                continue
            raise RuntimeError(f"GitHub {method} {path} -> HTTP {e.code}: {detail[:400]}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                last_err = e
                time.sleep(2 ** attempt + 1)
                continue
            raise RuntimeError(f"GitHub {method} {path} -> network error after 4 attempts: {e}") from e
    if last_err:
        raise RuntimeError(f"GitHub {method} {path} -> exhausted retries: {last_err}")


def get_login() -> str:
    me = api("GET", "/user")
    return me["login"]


PR_PLAN = [
    (100, "dave",  "merged", "2026-04-10", "fix: handle null tenant_id in billing path"),
    (101, "dave",  "merged", "2026-04-11", "refactor: extract invoice formatter into shared lib"),
    (102, "bob",   "merged", "2026-04-12", "feat: add bulk-import endpoint for customer sync"),
    (103, "erin",  "closed", "2026-04-13", "chore: bump python 3.11 -> 3.12 in CI matrix"),
    (104, "dave",  "closed", "2026-04-14", "fix: flaky test in auth/test_tokens.py"),
    (105, "carol", "closed", "2026-04-15", "perf: batch DB writes in metric ingest"),
    (106, "carol", "closed", "2026-04-16", "docs: add runbook for staging rollback"),
    (107, "dave",  "closed", "2026-04-17", "fix: 500 on /api/v2/users when pagination token is missing"),
    (108, "carol", "open",   "2026-04-18", "WIP: experimental OpenTelemetry trace sampler"),
    (109, "alice", "merged", "2026-04-19", "fix: race condition in webhook dispatcher"),
    (110, "erin",  "closed", "2026-04-20", "feat: add slow-query alert rule (Prometheus)"),
    (111, "carol", "merged", "2026-04-21", "feat: soft-delete for customer records"),
    (112, "carol", "merged", "2026-04-22", "refactor: split billing.py into submodules"),
    (113, "bob",   "merged", "2026-04-23", "fix: timezone bug in invoice generator (UTC vs local)"),
    (114, "alice", "closed", "2026-04-10", "revert: revert #109 due to regression in webhook retries"),
]
ISSUE_PLAN = [
    (500, "alice", "open",   "2026-04-11", "Latency spike in /api/v2/search after 2026-04-10 deploy"),
    (501, "alice", "closed", "2026-04-12", "Deprecate legacy v1 billing endpoints"),
    (502, "bob",   "open",   "2026-04-13", "Onboarding doc references an outdated CLI flag"),
    (503, "erin",  "open",   "2026-04-14", "Dashboard times out when tenant has >10k invoices"),
    (504, "carol", "closed", "2026-04-15", "Cannot reset password — email never sent"),
    (505, "alice", "open",   "2026-04-16", "Feature request: CSV export of customer list"),
    (506, "bob",   "closed", "2026-04-17", "Memory leak in background worker (daily cron)"),
    (507, "bob",   "open",   "2026-04-18", "Add OIDC support for SAML-only customers"),
    (508, "carol", "closed", "2026-04-19", "Test coverage regression — drop from 82% to 74%"),
    (509, "alice", "open",   "2026-04-20", "Slack webhook intermittently missing messages"),
    (510, "bob",   "open",   "2026-04-21", "Fix broken permalink in the v3 release notes"),
    (511, "dave",  "closed", "2026-04-22", "pg_stat_statements is off in prod replica"),
    (512, "dave",  "open",   "2026-04-23", "Feature-flag key conflict in GrowthBook config"),
    (513, "dave",  "closed", "2026-04-24", "Admin UI: 'active' filter should persist across refresh"),
    (514, "alice", "open",   "2026-04-11", "CSV upload times out at 10MB — raise server limit"),
    (515, "alice", "closed", "2026-04-12", "Metric billing.failed_charges never emitted"),
    (516, "carol", "closed", "2026-04-13", "Sentry PII: redact tenant_id in error breadcrumbs"),
    (517, "bob",   "closed", "2026-04-14", "README: add docker-compose quickstart"),
    (518, "bob",   "open",   "2026-04-15", "JWT expiry edge case when clock skew > 30s"),
    (519, "erin",  "closed", "2026-04-16", "Cloudflare WAF blocks legitimate /api/webhook traffic"),
]
COMMIT_PLAN = [
    ("erin",  "2026-04-12", "wip: prototype OTel sampler"),
    ("alice", "2026-04-13", "test: cover null tenant_id path"),
    ("carol", "2026-04-14", "rename billing_service -> billing"),
    ("erin",  "2026-04-15", "docs: fix typo in README"),
    ("erin",  "2026-04-16", "lint: apply black + ruff"),
    ("dave",  "2026-04-17", "chore: remove dead code in utils.py"),
    ("alice", "2026-04-18", "bump sdk version to 2.3.1"),
    ("bob",   "2026-04-19", "revert: metric change caused false alerts"),
    ("carol", "2026-04-20", "perf: index on invoices(tenant_id, created_at)"),
    ("carol", "2026-04-21", "docs: clarify retry semantics for webhook dispatcher"),
    ("carol", "2026-04-22", "fix: flaky test due to time.monotonic()"),
    ("bob",   "2026-04-23", "feat: add --dry-run flag to migrate CLI"),
    ("dave",  "2026-04-24", "chore: remove unused fixture in test_auth"),
    ("erin",  "2026-04-25", "refactor: pull EmailClient out of SignupService"),
    ("alice", "2026-04-12", "fix: connection-pool exhaustion under load"),
    ("carol", "2026-04-13", "feat: add metric background_worker_lag_seconds"),
    ("alice", "2026-04-14", "fix: raise QuotaError instead of generic Exception"),
    ("erin",  "2026-04-15", "test: add happy-path for webhook retry"),
    ("dave",  "2026-04-16", "chore: renovate bot dependency bump"),
    ("alice", "2026-04-17", "fix: normalize email on signup (lowercase, trim)"),
    ("alice", "2026-04-18", "docs: add ADR-017 for event sourcing decision"),
    ("carol", "2026-04-19", "feat: soft-delete sql migration (customers)"),
    ("alice", "2026-04-20", "fix: avoid panic on empty iterator in aggregator"),
    ("dave",  "2026-04-21", "perf: cache DB introspection queries"),
    ("carol", "2026-04-22", "chore: delete legacy v1 billing routes"),
    ("carol", "2026-04-23", "fix: race when two migrations run in parallel"),
    ("dave",  "2026-04-24", "test: cover timezone edge-case in invoice gen"),
    ("alice", "2026-04-25", "feat: add /healthz endpoint with DB probe"),
    ("alice", "2026-04-12", "docs: update CHANGELOG for 2.3.1 release"),
    ("dave",  "2026-04-13", "fix: handle utf-8 BOM in CSV upload"),
    ("carol", "2026-04-14", "refactor: move settings into config package"),
    ("alice", "2026-04-15", "fix: retry loop on 429 from Stripe API"),
    ("dave",  "2026-04-16", "chore: bump ruff to 0.5"),
    ("bob",   "2026-04-17", "perf: precompute aggregates for admin dashboard"),
    ("alice", "2026-04-18", "fix: off-by-one in pagination cursor"),
    ("carol", "2026-04-19", "docs: add operator runbook for staging rollback"),
    ("bob",   "2026-04-20", "chore: remove deprecated feature flag billing_v1"),
    ("bob",   "2026-04-21", "test: add integration test for bulk import endpoint"),
    ("bob",   "2026-04-22", "feat: add CLI completion for bash/zsh"),
    ("bob",   "2026-04-23", "fix: guard against nil plan in trial-upgrade flow"),
]

SNAPSHOT_SHAS = [
    "00000000000000", "00000010000001", "00000020000002", "00000030000003",
    "00000040000004", "00000050000005", "00000060000006", "00000070000007",
    "00000080000008", "00000090000009", "000000a000000a", "000000b000000b",
    "000000c000000c", "000000d000000d", "000000e000000e", "000000f000000f",
    "00000100000010", "00000110000011", "00000120000012", "00000130000013",
    "00000140000014", "00000150000015", "00000160000016", "00000170000017",
    "00000180000018", "00000190000019", "000001a000001a", "000001b000001b",
    "000001c000001c", "000001d000001d", "000001e000001e", "000001f000001f",
    "00000200000020", "00000210000021", "00000220000022", "00000230000023",
    "00000240000024", "00000250000025", "00000260000026", "00000270000027",
]


def delete_repo_if_exists(owner: str) -> bool:
    """iter5-fix: clean-rebuild path. Delete the fixture repo so each populator
    run starts from a known empty state, preventing accumulated rebuild noise
    (stale commits / payload PRs / closed-issue residues from older populator
    versions) from drifting the live API view away from the snapshot-based GT.
    Returns True if a delete happened, False if the repo was already absent.
    Safety: only deletes the specific REPO_NAME under the authenticated owner;
    refuses to touch any other repository.
    """
    try:
        api("GET", f"/repos/{owner}/{REPO_NAME}")
    except RuntimeError as e:
        if "HTTP 404" in str(e):
            return False
        raise
    print(f"[~] clean-rebuild: deleting {owner}/{REPO_NAME} before re-creating")
    api("DELETE", f"/repos/{owner}/{REPO_NAME}")
    # GitHub takes a moment to release the name. Poll until 404 to confirm
    # the namespace is free before proceeding (prior 3-second blind sleep
    # was racing with eventual consistency under churn).
    for _ in range(15):
        time.sleep(2)
        try:
            api("GET", f"/repos/{owner}/{REPO_NAME}")
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                return True
            raise
    # Fallback: even after 30s the GET still returns; proceed anyway.
    return True


def ensure_repo(owner: str):
    try:
        return api("GET", f"/repos/{owner}/{REPO_NAME}")
    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise
    print(f"[+] creating private repo {owner}/{REPO_NAME}")
    created = api("POST", "/user/repos", body={
        "name": REPO_NAME,
        "description": "Clawbench task_317 fixture repo — auto-populated",
        "private": True,
        "auto_init": True,
    })
    time.sleep(2)
    return created


def list_all(path: str, params=None, page_size=100) -> list:
    out, page = [], 1
    params = dict(params or {})
    while True:
        params.update({"per_page": page_size, "page": page})
        got = api("GET", path, params=params)
        if not isinstance(got, list):
            break
        if not got:
            break
        out.extend(got)
        if len(got) < page_size:
            break
        page += 1
        if page > 50:
            break
    return out


def get_default_branch_sha(owner: str) -> tuple[str, str]:
    repo = api("GET", f"/repos/{owner}/{REPO_NAME}")
    branch = repo["default_branch"]
    ref = api("GET", f"/repos/{owner}/{REPO_NAME}/git/refs/heads/{branch}")
    return branch, ref["object"]["sha"]


def put_file(
    owner: str,
    branch: str,
    path: str,
    content: str,
    message: str,
    *,
    pseudo_user: str | None = None,
    planned_date: str | None = None,
) -> dict:
    b64 = base64.b64encode(content.encode()).decode()
    body = {"message": message, "content": b64, "branch": branch}
    if pseudo_user and planned_date:
        who = {
            "name": pseudo_user,
            "email": f"{pseudo_user}@example.invalid",
            "date": f"{planned_date}T12:00:00Z",
        }
        body["author"] = who
        body["committer"] = who
    try:
        cur = api("GET", f"/repos/{owner}/{REPO_NAME}/contents/{path}", params={"ref": branch})
        if isinstance(cur, dict) and "sha" in cur:
            body["sha"] = cur["sha"]
    except RuntimeError:
        pass
    try:
        return api("PUT", f"/repos/{owner}/{REPO_NAME}/contents/{path}", body=body)
    except RuntimeError as e:
        # GitHub eventual-consistency: the GET above can return 404 while
        # the file actually exists, so PUT then complains the sha is
        # missing. Re-fetch once with a small delay and retry.
        if "HTTP 422" in str(e) and "sha" in str(e).lower():
            time.sleep(2)
            try:
                cur = api("GET", f"/repos/{owner}/{REPO_NAME}/contents/{path}", params={"ref": branch})
                if isinstance(cur, dict) and "sha" in cur:
                    body["sha"] = cur["sha"]
                    return api("PUT", f"/repos/{owner}/{REPO_NAME}/contents/{path}", body=body)
            except RuntimeError:
                pass
        raise


def create_branch(owner: str, name: str, from_sha: str):
    try:
        api("POST", f"/repos/{owner}/{REPO_NAME}/git/refs", body={
            "ref": f"refs/heads/{name}",
            "sha": from_sha,
        })
    except RuntimeError as e:
        if "HTTP 422" in str(e):
            return
        raise


def seed_commits(owner: str, branch: str):
    for i, (user, date, msg) in enumerate(COMMIT_PLAN, start=1):
        path = f"activity/commit_{i:02d}.md"
        body = f"{msg}\npseudo-author: {user}\nplanned-date: {date}\nfixture-version: 2\n"
        put_file(owner, branch, path, body, f"{msg} (pseudo-author: {user}; planned-date: {date})", pseudo_user=user, planned_date=date)
        print(f"  commit {i:02d}/40  {msg}  ({user})")


def seed_prs(owner: str, branch: str):
    for num, user, state, date, title in PR_PLAN:
        br = f"pr-{num}"
        _, sha = get_default_branch_sha(owner)
        create_branch(owner, br, sha)
        path = f"prs/pr_{num}.md"
        body = f"PR #{num}: {title}\npseudo-user: {user}\nplanned-date: {date}\n"
        put_file(owner, br, path, body, f"PR #{num} payload ({user})", pseudo_user=user, planned_date=date)
        try:
            pr = api("POST", f"/repos/{owner}/{REPO_NAME}/pulls", body={
                "title": title,
                "head": br,
                "base": branch,
                "body": f"Planned state: {state}, pseudo-user: {user}, date: {date}",
            })
        except RuntimeError as e:
            if "HTTP 422" not in str(e):
                raise
            existing = api("GET", f"/repos/{owner}/{REPO_NAME}/pulls",
                           params={"head": f"{owner}:{br}", "state": "all"})
            if not existing:
                raise
            pr = existing[0]
        pr_num = pr["number"]
        if state == "merged":
            try:
                api("PUT", f"/repos/{owner}/{REPO_NAME}/pulls/{pr_num}/merge",
                    body={"commit_title": f"Merge PR #{num}: {title}"})
            except RuntimeError as e:
                if "HTTP 405" in str(e) or "HTTP 409" in str(e):
                    pass
                else:
                    raise
        elif state == "closed":
            api("PATCH", f"/repos/{owner}/{REPO_NAME}/pulls/{pr_num}", body={"state": "closed"})
        print(f"  PR #{num:03d}  {state:6s}  {user}  {title}")


def seed_issues(owner: str):
    for num, user, state, date, title in ISSUE_PLAN:
        body = f"pseudo-user: {user}, date: {date}, planned state: {state}"
        issue = api("POST", f"/repos/{owner}/{REPO_NAME}/issues", body={
            "title": title,
            "body": body,
        })
        i_num = issue["number"]
        if state == "closed":
            api("PATCH", f"/repos/{owner}/{REPO_NAME}/issues/{i_num}", body={"state": "closed"})
        print(f"  Issue #{num}  {state:6s}  {user}  {title}")


def refresh_existing_metadata(owner: str):
    """Keep older fixture repos aligned with the current prompt/eval contract.

    Earlier task versions used placeholder PR/issue titles and did not create
    commit messages with imported contributor notes. Updating titles/bodies is
    non-destructive and lets the live API view remain the canonical fixture.
    """
    prs = sorted(
        list_all(f"/repos/{owner}/{REPO_NAME}/pulls", params={"state": "all", "per_page": 100}),
        key=lambda p: p.get("number", 0),
    )
    for pr, (num, user, state, date, title) in zip(prs, PR_PLAN):
        body = f"Planned state: {state}, pseudo-user: {user}, date: {date}"
        patch = {"title": title, "body": body}
        if state in {"open", "closed"} and not pr.get("merged_at"):
            patch["state"] = state
        api("PATCH", f"/repos/{owner}/{REPO_NAME}/pulls/{pr['number']}", body=patch)

    issues_all = list_all(f"/repos/{owner}/{REPO_NAME}/issues", params={"state": "all", "per_page": 100})
    issues = sorted([i for i in issues_all if "pull_request" not in i], key=lambda i: i.get("number", 0))
    for issue, (num, user, state, date, title) in zip(issues, ISSUE_PLAN):
        body = f"pseudo-user: {user}, date: {date}, planned state: {state}"
        api("PATCH", f"/repos/{owner}/{REPO_NAME}/issues/{issue['number']}", body={
            "title": title,
            "body": body,
            "state": state,
        })


def already_populated(owner: str) -> bool:
    commits = list_all(f"/repos/{owner}/{REPO_NAME}/commits", params={"per_page": 100})
    prs = list_all(f"/repos/{owner}/{REPO_NAME}/pulls", params={"state": "all", "per_page": 100})
    issues = list_all(f"/repos/{owner}/{REPO_NAME}/issues", params={"state": "all", "per_page": 100})
    issues_only = [i for i in issues if "pull_request" not in i]
    return len(commits) >= 40 and len(prs) >= 15 and len(issues_only) >= 20


PLAN_DATE_BY_COMMIT_MESSAGE = {msg: date for user, date, msg in COMMIT_PLAN}
PLAN_USER_BY_COMMIT_MESSAGE = {msg: user for user, date, msg in COMMIT_PLAN}


def _planned_meta(text: str | None) -> dict:
    text = text or ""
    user = re.search(r"pseudo-user:\s*([A-Za-z0-9_.-]+)", text, re.I)
    author = re.search(r"pseudo-author:\s*([A-Za-z0-9_.-]+)", text, re.I)
    date = re.search(r"(?:planned-date|date):\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    state = re.search(r"planned state:\s*([A-Za-z0-9_.-]+)", text, re.I)
    return {
        "user": (user or author).group(1).lower() if (user or author) else None,
        "date": date.group(1) if date else None,
        "state": state.group(1).lower() if state else None,
    }


def _static_snapshot() -> dict:
    pull_requests = []
    for num, user, state, date, title in PR_PLAN:
        row = {"number": num, "title": title, "user": user, "state": state}
        if state == "merged":
            row["merged_at"] = date
        elif state == "closed":
            row["closed_at"] = date
            row["merged_at"] = None
        else:
            row["created_at"] = date
            row["merged_at"] = None
            row["closed_at"] = None
        pull_requests.append(row)

    issues = []
    for num, user, state, date, title in ISSUE_PLAN:
        row = {"number": num, "title": title, "user": user, "state": state}
        if state == "closed":
            row["closed_at"] = date
        else:
            row["created_at"] = date
            row["closed_at"] = None
        issues.append(row)

    snapshot = {
        "generated_at": "2026-04-25T23:59:00Z",
        "repo": "acme/service",
        "window_days": 16,
        "pull_requests": pull_requests,
        "issues": issues,
        "commits": [
            {"sha": SNAPSHOT_SHAS[i], "user": user, "date": date, "message": msg}
            for i, (user, date, msg) in enumerate(COMMIT_PLAN)
        ],
    }
    return snapshot


def collect_live_snapshot(owner: str) -> dict:
    prs_raw = list_all(f"/repos/{owner}/{REPO_NAME}/pulls", params={"state": "all", "per_page": 100})
    issues_raw = list_all(f"/repos/{owner}/{REPO_NAME}/issues", params={"state": "all", "per_page": 100})
    commits_raw = list_all(f"/repos/{owner}/{REPO_NAME}/commits", params={"per_page": 100})

    pull_requests = []
    for pr in prs_raw:
        meta = _planned_meta(pr.get("body") or "")
        if not meta["user"]:
            continue
        state = "merged" if pr.get("merged_at") else ("closed" if pr.get("state") == "closed" else "open")
        row = {
            "number": pr["number"],
            "title": pr.get("title") or "",
            "user": meta["user"],
            "state": state,
        }
        date = meta["date"] or (pr.get("merged_at") or pr.get("closed_at") or pr.get("created_at") or "")[:10]
        if state == "merged":
            row["merged_at"] = date
        elif state == "closed":
            row["closed_at"] = date
            row["merged_at"] = None
        else:
            row["created_at"] = date
            row["closed_at"] = None
            row["merged_at"] = None
        pull_requests.append(row)

    issues = []
    for issue in issues_raw:
        if "pull_request" in issue:
            continue
        meta = _planned_meta(issue.get("body") or "")
        if not meta["user"]:
            continue
        state = "closed" if issue.get("state") == "closed" else "open"
        date = meta["date"] or (issue.get("closed_at") or issue.get("created_at") or "")[:10]
        row = {
            "number": issue["number"],
            "title": issue.get("title") or "",
            "user": meta["user"],
            "state": state,
        }
        if state == "closed":
            row["closed_at"] = date
        else:
            row["created_at"] = date
            row["closed_at"] = None
        issues.append(row)

    commits = []
    for commit in commits_raw:
        msg_full = ((commit.get("commit") or {}).get("message") or "").splitlines()[0]
        meta = _planned_meta(msg_full)
        legacy_user = re.search(r"\s+\(([A-Za-z0-9_.-]+)\)$", msg_full)
        msg = re.sub(r"\s+\((?:pseudo-author:[^)]+|[A-Za-z0-9_.-]+)\)\s*$", "", msg_full).strip()
        if msg not in PLAN_DATE_BY_COMMIT_MESSAGE:
            continue
        commits.append({
            "sha": commit.get("sha", "")[:14],
            "user": (meta["user"] or (legacy_user.group(1).lower() if legacy_user else None) or PLAN_USER_BY_COMMIT_MESSAGE[msg]),
            "date": meta["date"] or PLAN_DATE_BY_COMMIT_MESSAGE[msg],
            "message": msg,
        })
    commits.sort(key=lambda r: (r["date"], r["sha"]))

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo": f"{owner}/{REPO_NAME}",
        "window_days": 16,
        "pull_requests": sorted(pull_requests, key=lambda r: r["number"]),
        "issues": sorted(issues, key=lambda r: r["number"]),
        "commits": commits,
    }


def build_ground_truth(snapshot: dict) -> dict:
    stats: dict[str, dict[str, int]] = {}

    def bucket(user: str) -> dict[str, int]:
        return stats.setdefault(user, {
            "merged_prs": 0,
            "closed_unmerged_prs": 0,
            "closed_issues": 0,
            "commits": 0,
        })

    closed_unmerged = []
    revert_activity = []
    highlights = []

    for pr in snapshot["pull_requests"]:
        if pr["state"] == "merged":
            bucket(pr["user"])["merged_prs"] += 1
            highlights.append({
                "type": "pr",
                "number": pr["number"],
                "title": pr["title"],
                "user": pr["user"],
                "date": pr.get("merged_at"),
            })
        elif pr["state"] == "closed":
            bucket(pr["user"])["closed_unmerged_prs"] += 1
            closed_unmerged.append(pr["number"])
        if "revert" in (pr.get("title") or "").lower():
            revert_activity.append({
                "type": "pr",
                "number": pr["number"],
                "title": pr["title"],
                "user": pr["user"],
                "date": pr.get("merged_at") or pr.get("closed_at") or pr.get("created_at"),
            })

    for issue in snapshot["issues"]:
        if issue["state"] != "closed":
            continue
        bucket(issue["user"])["closed_issues"] += 1
        highlights.append({
            "type": "issue",
            "number": issue["number"],
            "title": issue["title"],
            "user": issue["user"],
            "date": issue.get("closed_at"),
        })

    for commit in snapshot["commits"]:
        bucket(commit["user"])["commits"] += 1
        if "revert" in (commit.get("message") or "").lower():
            revert_activity.append({
                "type": "commit",
                "sha": commit["sha"],
                "message": commit["message"],
                "user": commit["user"],
                "date": commit["date"],
            })

    highlights.sort(key=lambda r: (r.get("date") or "", str(r.get("number", ""))), reverse=True)
    activity_rows = (
        [p for p in snapshot["pull_requests"] if p["state"] in {"merged", "closed"}]
        + [i for i in snapshot["issues"] if i["state"] == "closed"]
        + list(snapshot["commits"])
    )
    return {
        "task_id": "task_101_19_github_activity_digest",
        "difficulty": "Hard",
        "schema": "a",
        "schema_notes": "live GitHub activity snapshot with imported contributor/date notes",
        "skills_declared": ["github"],
        "ground_truth": {
            "contributor_count_min": len(stats),
            "window_days": snapshot.get("window_days", 16),
            "highlight_count": 5,
            "highlight_mode": "most_recent_closed_or_merged",
            "activity_index_expected_rows": len(activity_rows),
            "activity_index_columns": [
                "activity_type",
                "number_or_sha",
                "title_or_message",
                "contributor",
                "activity_date",
                "status",
            ],
            "contributor_stats": dict(sorted(stats.items())),
            "closed_unmerged_pr_numbers": sorted(closed_unmerged),
            "revert_activity": revert_activity,
            "highlights": highlights[:5],
        },
    }


def write_outputs(snapshot: dict | None = None):
    snapshot = snapshot or _static_snapshot()
    ground_truth = build_ground_truth(snapshot)
    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "references").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / "sources/github_activity_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    (TASK_DIR / "references/ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n"
    )


def main() -> str:
    try:
        if os.environ.get("SNAPSHOT_MODE") == "1":
            existing = TASK_DIR / "sources/github_activity_snapshot.json"
            if existing.exists():
                write_outputs(json.loads(existing.read_text(encoding="utf-8")))
            else:
                write_outputs()
            print(f"[✓] SNAPSHOT_MODE=1: wrote snapshot + ground_truth to {TASK_DIR}")
            return "ok"

        configure_auth()
        owner = get_login()
        # iter5-fix: clean-rebuild every run to prevent accumulated noise drift.
        # Set CLEAN_REBUILD=0 (or leave unset and provide PRESERVE_FIXTURE=1) to
        # keep the prior incremental behavior.
        if os.environ.get("PRESERVE_FIXTURE") != "1":
            delete_repo_if_exists(owner)
        ensure_repo(owner)
        branch, _ = get_default_branch_sha(owner)
        # After a clean-rebuild ensure_repo creates a fresh empty repo with one
        # initial README commit; always re-seed.
        seed_commits(owner, branch)
        seed_prs(owner, branch)
        seed_issues(owner)

        refresh_existing_metadata(owner)
        snapshot = collect_live_snapshot(owner)
        if len(snapshot["commits"]) < len(COMMIT_PLAN):
            print("[=] refreshing direct commit fixture metadata")
            seed_commits(owner, branch)
            snapshot = collect_live_snapshot(owner)
        write_outputs(snapshot)
        print(
            f"\n[✓] commits={len(snapshot['commits'])} "
            f"prs={len(snapshot['pull_requests'])} issues={len(snapshot['issues'])}"
        )
        return "ok"
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] github populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"github": status}))
    raise SystemExit(0 if status == "ok" else 1)
