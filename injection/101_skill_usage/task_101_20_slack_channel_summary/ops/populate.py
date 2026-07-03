"""
Populate (or READ) a Slack channel for task_101_20_slack_channel_summary.

Invoked by the runner as a pre_exec hook; resolves its injection root
from ``__file__`` and reads credentials from ``os.environ``.

Flow:
  - In SNAPSHOT_MODE=1: write the pre-built snapshot + keep existing GT.
  - In live mode:
    1. Purge all existing messages from #general (prevents stale data).
    2. Post the 206-message fixture from the committed snapshot.
    3. Read back with real ts values assigned by Slack.
    4. Identify the 8 budget-thread messages by their unique text content.
    5. Update ground_truth.json with the live ts values so the eval matches.
    6. Write the snapshot with live ts values.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import ssl
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TASK_DIR = pathlib.Path(__file__).resolve().parent.parent

TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

SNAPSHOT_FILE = TASK_DIR / "sources/slack_snapshot.json"
GT_FILE = TASK_DIR / "references/ground_truth.json"

# The 8 budget-thread messages are identified by unique text prefixes.
# These are stable across runs (we control the fixture text).
BUDGET_THREAD_TEXT_SIGNATURES = [
    ("kickoff", "kicking off the Q3 budget planning thread"),
    ("infra_ask", "re: Q3 budget — quoting Carol's $1.85M target above, infra is asking for $620K"),
    ("headcount_ask", "re Dave's $620K infra ask — that's tight. headcount needs $980K"),
    ("deferral_proposal", "Bob's $250K residual won't cover marketing+ops+travel"),
    ("ops_savings", "re Alice's deferral idea — ops can also trim $40K"),
    ("risk_callout", "great signals from Erin. one risk: the clickhouse migration"),
    ("revised_proposal", "putting Carol's $75K Acme SOW in the contingency line"),
    ("final_decision", "decision: Q3 budget locked at $1.85M with Bob's split"),
]


def api(method: str, path: str, body=None, params=None, _retry: int = 3):
    url = f"https://slack.com/api/{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429 and _retry > 0:
            retry_after = int(e.headers.get("Retry-After") or "2")
            print(f"  [~] slack 429 on {path}, sleeping {retry_after}s (retries left={_retry-1})")
            time.sleep(retry_after)
            return api(method, path, body=body, params=params, _retry=_retry - 1)
        raise


def load_committed_snapshot() -> list[dict]:
    """Load the 206 messages from the committed snapshot file."""
    if not SNAPSHOT_FILE.exists():
        raise RuntimeError(f"Snapshot file not found: {SNAPSHOT_FILE}")
    data = json.loads(SNAPSHOT_FILE.read_text())
    msgs = data.get("messages", [])
    if len(msgs) < 150:
        raise RuntimeError(f"Snapshot has only {len(msgs)} messages, expected ~206")
    return msgs


def list_channels_bot_in() -> list:
    out, cursor = [], None
    while True:
        params = {"types": "public_channel", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = api("GET", "conversations.list", params=params)
        if not resp.get("ok"):
            raise RuntimeError(f"conversations.list failed: {resp.get('error')}")
        out.extend(resp.get("channels", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return out


def try_join(channel_id: str) -> bool:
    try:
        resp = api("POST", "conversations.join", body={"channel": channel_id})
        return bool(resp.get("ok"))
    except urllib.error.HTTPError:
        return False


def ensure_general_channel() -> dict | None:
    """Pick or create a public channel named ``general`` with the bot as member."""
    channels = list_channels_bot_in()
    existing = next((c for c in channels if c.get("name") == "general"), None)
    if existing is not None:
        if not existing.get("is_member"):
            try_join(existing["id"])
            existing["is_member"] = True
        return existing
    try:
        resp = api("POST", "conversations.create", body={"name": "general"})
    except urllib.error.HTTPError:
        return None
    if resp.get("ok") and resp.get("channel"):
        chan = resp["channel"]
        if not chan.get("is_member"):
            try_join(chan["id"])
            chan["is_member"] = True
        return chan
    if resp.get("error") == "name_taken":
        return next((c for c in list_channels_bot_in() if c.get("name") == "general"), None)
    return None


def purge_channel(channel_id: str) -> int:
    """Delete ALL messages from the channel. Returns count deleted."""
    deleted = 0
    while True:
        resp = api("GET", "conversations.history", params={
            "channel": channel_id, "limit": 200
        })
        if not resp.get("ok"):
            print(f"  [!] conversations.history failed during purge: {resp.get('error')}")
            break
        messages = resp.get("messages", [])
        if not messages:
            break
        for m in messages:
            ts = m.get("ts")
            if not ts:
                continue
            del_resp = api("POST", "chat.delete", body={
                "channel": channel_id, "ts": ts
            })
            if del_resp.get("ok"):
                deleted += 1
            elif del_resp.get("error") == "message_not_found":
                pass  # already deleted
            elif del_resp.get("error") == "cant_delete_message":
                # Bot can't delete other users' messages; try admin method
                # or just skip — in our workspace the bot posted everything
                pass
            else:
                print(f"  [!] chat.delete failed for ts={ts}: {del_resp.get('error')}")
            # Rate limit: chat.delete is Tier 3 (~50/min).
            # Use 0.8s spacing (~75/min); api() retries on 429.
            time.sleep(0.8)
        if deleted % 50 == 0 and deleted > 0:
            print(f"  [~] purged {deleted} messages so far...")
    print(f"  [✓] purge complete: {deleted} messages deleted")
    return deleted


def post_fixture(channel_id: str, messages: list[dict]) -> list[dict]:
    """Post all fixture messages and return the live messages with real ts."""
    posted = []
    for i, m in enumerate(messages):
        text = m.get("text", "")
        if not text:
            continue
        resp = api("POST", "chat.postMessage", body={
            "channel": channel_id,
            "text": text,
        })
        if not resp.get("ok"):
            raise RuntimeError(f"chat.postMessage failed at #{i}: {resp.get('error')}")
        posted.append({
            "ts": resp.get("ts"),
            "user": resp.get("message", {}).get("user", m.get("user", "UNKNOWN")),
            "channel": channel_id,
            "text": text,
        })
        if (i + 1) % 50 == 0:
            print(f"  posted {i+1}/{len(messages)}")
        # Slack chat.postMessage is Tier 4 for some apps (~100/min).
        # 0.7s spacing → ~86/min with api() 429 retry as safety net.
        time.sleep(0.7)
    return posted


def read_channel_history(channel_id: str, limit: int = 1000) -> list:
    out, cursor = [], None
    while len(out) < limit:
        params = {"channel": channel_id, "limit": min(200, limit - len(out))}
        if cursor:
            params["cursor"] = cursor
        resp = api("GET", "conversations.history", params=params)
        if not resp.get("ok"):
            raise RuntimeError(f"conversations.history failed: {resp.get('error')}")
        out.extend(resp.get("messages", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return out


def identify_budget_thread_ts(live_messages: list[dict]) -> dict[str, str]:
    """
    Match the 8 budget-thread messages by their unique text prefixes.
    Returns {role_in_thread: live_ts} mapping.
    """
    ts_map = {}
    for role, signature in BUDGET_THREAD_TEXT_SIGNATURES:
        for m in live_messages:
            text = m.get("text", "")
            if text.startswith(signature):
                ts_map[role] = m.get("ts")
                break
        if role not in ts_map:
            print(f"  [!] WARNING: could not find budget thread msg: {role}")
    return ts_map


def update_ground_truth_ts(ts_map: dict[str, str]):
    """
    Update ground_truth.json with live ts values for the 8 budget thread messages.
    The GT schema uses ordered ts lists and per-number source_ts references.
    """
    if not GT_FILE.exists():
        print("  [!] ground_truth.json not found, cannot update ts")
        return

    gt = json.loads(GT_FILE.read_text())
    ground_truth = gt.get("ground_truth", {})
    thread_messages = ground_truth.get("thread_messages", [])

    # Build old_ts → new_ts mapping from role_in_thread
    old_to_new = {}
    for tm in thread_messages:
        role = tm.get("role_in_thread")
        if role in ts_map:
            old_ts = tm["ts"]
            new_ts = ts_map[role]
            old_to_new[old_ts] = new_ts

    if len(old_to_new) < 8:
        print(f"  [!] WARNING: only mapped {len(old_to_new)}/8 ts values")

    # Update thread_messages ts
    for tm in thread_messages:
        old_ts = tm["ts"]
        if old_ts in old_to_new:
            tm["ts"] = old_to_new[old_ts]

    # Update expected_thread_ts (ordered list)
    expected_ts = ground_truth.get("expected_thread_ts", [])
    ground_truth["expected_thread_ts"] = [
        old_to_new.get(ts, ts) for ts in expected_ts
    ]

    # Update thread_root_ts
    root_ts = ground_truth.get("thread_root_ts")
    if root_ts and root_ts in old_to_new:
        ground_truth["thread_root_ts"] = old_to_new[root_ts]

    # Update expected_specific_numbers source_ts
    for item in ground_truth.get("expected_specific_numbers", []):
        src = item.get("source_ts")
        if src and src in old_to_new:
            item["source_ts"] = old_to_new[src]

    # Update expected_specific_dates source_ts
    for item in ground_truth.get("expected_specific_dates", []):
        src = item.get("source_ts")
        if src and src in old_to_new:
            item["source_ts"] = old_to_new[src]

    # Update expected_final_decision decision_message_ts
    final = ground_truth.get("expected_final_decision", {})
    dts = final.get("decision_message_ts")
    if dts and dts in old_to_new:
        final["decision_message_ts"] = old_to_new[dts]

    gt["ground_truth"] = ground_truth
    GT_FILE.write_text(json.dumps(gt, ensure_ascii=False, indent=2) + "\n")
    print(f"  [✓] ground_truth.json updated with {len(old_to_new)} live ts values")


def write_snapshot(channel_label: str, messages: list[dict]):
    """Write the snapshot file from live messages (for executor to read)."""
    # Drop Slack's own rate-limit notice messages
    messages = [m for m in messages if "Due to a high volume of activity" not in (m.get("text") or "")]

    max_ts = None
    for m in messages:
        try:
            max_ts = max(max_ts or 0.0, float(str(m.get("ts", "0"))))
        except (TypeError, ValueError):
            continue
    if max_ts:
        generated_at = (
            dt.datetime.fromtimestamp(max_ts, tz=dt.timezone.utc)
            + dt.timedelta(minutes=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    else:
        generated_at = "2026-04-24T14:10:11Z"

    snapshot = {
        "generated_at": generated_at,
        "channel": channel_label,
        "messages": messages,
    }
    (TASK_DIR / "sources").mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"  [✓] snapshot written: {len(messages)} messages")


def main() -> str:
    global TOKEN
    try:
        if os.environ.get("SNAPSHOT_MODE") == "1":
            # In snapshot mode, the committed snapshot is already correct.
            # Verify it exists, has the budget thread, and ensure GT ts
            # values match the snapshot (in case a prior live run updated them).
            msgs = load_committed_snapshot()
            ts_map = identify_budget_thread_ts(msgs)
            if len(ts_map) == 8:
                update_ground_truth_ts(ts_map)
            print(f"[✓] SNAPSHOT_MODE=1: snapshot has {len(msgs)} messages, GT synced")
            return "ok"

        TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
        if not TOKEN:
            raise RuntimeError("SLACK_BOT_TOKEN is required when SNAPSHOT_MODE is not 1")

        auth = api("GET", "auth.test")
        if not auth.get("ok"):
            raise RuntimeError(f"auth.test failed: {auth}")

        target = ensure_general_channel()
        if target is None:
            channels = list_channels_bot_in()
            if not channels:
                print("[=] bot sees zero channels; keeping pre-existing snapshot")
                return "skipped_no_channels"
            target = next((c for c in channels if c.get("is_member")), None)
            if target is None:
                for c in channels:
                    if try_join(c["id"]):
                        c["is_member"] = True
                        target = c
                        break
            if target is None:
                print("[=] could not join any channel; keeping pre-existing snapshot")
                return "skipped_cannot_join"

        channel_id = target["id"]
        channel_name = f"#{target['name']}"
        print(f"[*] using channel {channel_name} (id={channel_id})")

        # Step 1: Post the 206-message fixture fresh.
        # We do NOT purge old messages — the executor only fetches the latest
        # 200, and our freshly posted messages will be newest. Old stale
        # messages get pushed out of view. This avoids a costly purge that
        # would exceed the 600s pre_exec timeout.
        fixture_msgs = load_committed_snapshot()
        # Post in chronological order (snapshot is newest-first, reverse it).
        # Oldest message posted first → gets lowest live ts.
        # Newest message posted last → gets highest live ts.
        # conversations.history returns newest-first, so readback order
        # matches the committed snapshot's ordering.
        fixture_msgs_chrono = list(reversed(fixture_msgs))

        print(f"[+] posting {len(fixture_msgs_chrono)}-message fixture...")
        posted = post_fixture(channel_id, fixture_msgs_chrono)

        # Step 2: Read back the most recent messages (newest-first).
        # Since we just posted 206 messages, they're the newest in the channel.
        # The executor also fetches "up to 200" newest, so what we read here
        # is what the executor will see.
        print("[*] reading back channel history...")
        live_msgs = read_channel_history(channel_id, limit=len(fixture_msgs))
        # The top N messages should be exactly what we just posted.
        live_msgs = live_msgs[:len(fixture_msgs)]

        # Step 4: Identify the 8 budget-thread messages by text content
        ts_map = identify_budget_thread_ts(live_msgs)
        if len(ts_map) == 8:
            print(f"[✓] all 8 budget thread messages identified with live ts")
        else:
            print(f"[!] only found {len(ts_map)}/8 budget thread messages")

        # Step 5: Update ground_truth.json with live ts values
        update_ground_truth_ts(ts_map)

        # Step 6: Write snapshot with live messages, restoring original user IDs.
        # In live mode all messages are posted by the bot, so the Slack API
        # returns the bot's user ID for every message. We restore the original
        # user IDs from the fixture by matching on text content, so the
        # executor's snapshot looks identical to the committed one (except for
        # ts values).
        text_to_user = {m.get("text", ""): m.get("user", "UNKNOWN") for m in fixture_msgs}
        live_normalized = []
        for m in live_msgs:
            text = m.get("text") or ""
            original_user = text_to_user.get(text, m.get("user") or m.get("bot_id") or "UNKNOWN")
            live_normalized.append({
                "ts": m.get("ts"),
                "user": original_user,
                "channel": channel_id,
                "text": text,
            })
        write_snapshot(channel_name, live_normalized)

        return "ok"

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[!] slack populator failed: {e}\n{tb}")
        return f"skipped_{type(e).__name__}"


if __name__ == "__main__":
    status = main()
    print(json.dumps({"slack": status}))
    raise SystemExit(0 if status.startswith("ok") else 1)
