#!/usr/bin/env python3
"""Ensure the live Google Calendar fixture for task 103_06.

This script is host-only. It decodes a gcalcli-compatible OAuth cache from
privacy env, validates access, removes stale task recommendation events, and
ensures the deterministic trip events exist before the executor starts. The
normal path is read-only after the one-time fixture is present, so parallel
runs can share the same calendar without repeatedly deleting/reinserting it.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path


TASK_ID = "task_103_08_hk_jpop_calendar_ticketing"
LOCK_PATH = Path("/tmp/clawbench_task_103_06_calendar.lock")
TIME_MIN = "2026-06-03T00:00:00+08:00"
TIME_MAX = "2026-06-10T00:00:00+08:00"
CLEANUP_MIN = "2026-01-01T00:00:00+08:00"
CLEANUP_MAX = "2027-01-01T00:00:00+08:00"
TZ = "Asia/Hong_Kong"
EVENTS = [
    ("2026-06-03T09:00:00+08:00", "2026-06-03T13:30:00+08:00", "Flight: SIN to HKG", "Singapore Changi Airport to Hong Kong International Airport", "Departing Singapore, arriving Hong Kong."),
    ("2026-06-03T15:00:00+08:00", "2026-06-03T16:00:00+08:00", "Check-in: SkyCity hotel", "SkyCity, Chek Lap Kok, Hong Kong", "Staying near the airport / SkyCity area for this business trip."),
    ("2026-06-04T09:00:00+08:00", "2026-06-04T12:00:00+08:00", "Client workshop", "AsiaWorld-Expo, Chek Lap Kok", "Hong Kong regional lead, morning meeting."),
    ("2026-06-04T14:00:00+08:00", "2026-06-04T17:30:00+08:00", "Partner meetings", "Tung Chung / Lantau", "Afternoon near Tung Chung."),
    ("2026-06-05T09:30:00+08:00", "2026-06-05T17:00:00+08:00", "Regional planning offsite", "Central, Hong Kong", "Full-day work schedule, not suitable for a concert."),
    ("2026-06-06T13:00:00+08:00", "2026-06-06T15:00:00+08:00", "Free time: Citygate", "Citygate Outlets, Tung Chung", "Afternoon in Tung Chung, evening available for activities."),
    ("2026-06-06T16:00:00+08:00", "2026-06-06T23:00:00+08:00", "Open evening for local music", "Near Lantau / Airport Express", "free/transparent, no work conflicts."),
    ("2026-06-07T10:00:00+08:00", "2026-06-07T12:00:00+08:00", "Expense report", "SkyCity hotel", "Still in Hong Kong."),
    ("2026-06-08T09:00:00+08:00", "2026-06-08T11:30:00+08:00", "QBR", "West Kowloon", "Hong Kong regional lead."),
    ("2026-06-08T15:00:00+08:00", "2026-06-08T17:30:00+08:00", "Wrap-up meeting", "Central", "Hong Kong regional lead."),
    ("2026-06-09T11:00:00+08:00", "2026-06-09T15:30:00+08:00", "Flight: HKG to SIN", "Hong Kong International Airport to Singapore Changi Airport", "End of trip, returning to Singapore."),
]
EXPECTED_TITLES = [event[2] for event in EVENTS]
TASK_CLEANUP_QUERIES = [
    "concert",
    "J-pop",
    "J-rock",
    "Japanese music",
    "concert (zh)",
    "Live Nation",
]


def fail(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("__") or "TODO" in value or "placeholder" in value.lower():
        fail(f"{name} is missing or still a placeholder; provide a real Google Calendar OAuth value.")
    return value


def optional_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("__") or "TODO" in value or "placeholder" in value.lower():
        return ""
    return value


def ensure_google_deps() -> None:
    try:
        import google.auth.transport.requests  # noqa: F401
        import google.oauth2.credentials  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get("CLAWBENCH_GCAL_POPULATE_DEPS_READY") == "1":
        fail("Google Calendar Python dependencies are unavailable even after installing the task venv.")
    venv = Path("/tmp/clawbench-gcal-populate-venv")
    python = venv / "bin" / "python"
    if not python.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    subprocess.check_call([
        str(python),
        "-m",
        "pip",
        "install",
        "-q",
        "google-api-python-client",
        "google-auth",
        "google-auth-oauthlib",
    ])
    env = dict(os.environ)
    env["CLAWBENCH_GCAL_POPULATE_DEPS_READY"] = "1"
    os.execve(str(python), [str(python), __file__], env)


def load_credentials():
    from google.oauth2.credentials import Credentials

    client_id = require_env("GCALCLI_CLIENT_ID")
    client_secret = optional_env("GCALCLI_CLIENT_SECRET")
    token_b64 = require_env("GCALCLI_OAUTH_B64")
    try:
        raw = base64.b64decode(token_b64, validate=True)
    except Exception as exc:
        fail(f"GCALCLI_OAUTH_B64 is not valid base64: {exc}")

    try:
        creds = pickle.loads(raw)
    except Exception:
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            fail(f"GCALCLI_OAUTH_B64 is neither a gcalcli oauth pickle nor legacy JSON: {exc}")
        token = data.get("token") or data.get("access_token")
        creds = Credentials(
            token=token,
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=data.get("client_id") or client_id,
            client_secret=data.get("client_secret") or client_secret or None,
            scopes=data.get("scopes") or ["https://www.googleapis.com/auth/calendar"],
        )

    token_client_id = getattr(creds, "client_id", None)
    if token_client_id and token_client_id != client_id:
        fail("OAuth token client_id does not match GCALCLI_CLIENT_ID.")
    if not getattr(creds, "refresh_token", None):
        fail("OAuth token has no refresh_token; it will not be reusable across task runs.")
    if not getattr(creds, "client_secret", None) and client_secret:
        creds._client_secret = client_secret
    return creds


def calendar_id_for(service) -> str:
    account = require_env("GOOGLE_CALENDAR_ACCOUNT")
    calendars = service.calendarList().list().execute().get("items", [])
    for item in calendars:
        if item.get("primary"):
            return item["id"]
    for item in calendars:
        if account in {item.get("id"), item.get("summary")}:
            return item["id"]
    return "primary"


def delete_event(service, calendar_id: str, event_id: str) -> None:
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as exc:
        print(f"warning: failed to delete stale event {event_id}: {exc}", file=sys.stderr)


def list_window_events(service, calendar_id: str) -> list[dict]:
    return service.events().list(
        calendarId=calendar_id,
        timeMin=TIME_MIN,
        timeMax=TIME_MAX,
        singleEvents=True,
        maxResults=250,
    ).execute().get("items", [])


def is_seed_event(event: dict) -> bool:
    private = event.get("extendedProperties", {}).get("private", {})
    return private.get("clawbench_task_id") == TASK_ID


def is_stale_recommendation_event(event: dict) -> bool:
    summary = str(event.get("summary", ""))
    text = " ".join(str(event.get(k, "")) for k in ("summary", "location", "description")).lower()
    if summary.lower().startswith(("concert:", "recommended concert:", "calendar recommendation:")):
        return True
    if ("recommended" in text or "recommendation" in text or "clawbench" in text) and any(
        token in text for token in ("concert", "j-pop", "j-rock", "japanese music", "concert (zh)")
    ):
        return True
    return False


def cleanup_stale_recommendations(service, calendar_id: str) -> list[str]:
    removed: list[str] = []

    for query in TASK_CLEANUP_QUERIES:
        events = service.events().list(
            calendarId=calendar_id,
            timeMin=CLEANUP_MIN,
            timeMax=CLEANUP_MAX,
            singleEvents=True,
            q=query,
            maxResults=50,
        ).execute().get("items", [])
        for event in events:
            if not is_seed_event(event) and is_stale_recommendation_event(event):
                delete_event(service, calendar_id, event["id"])
                removed.append(event.get("summary", event["id"]))
    return removed


def ensure_calendar(service, calendar_id: str) -> tuple[list[str], list[str], bool]:
    removed: list[str] = []
    inserted: list[str] = []
    with LOCK_PATH.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        removed.extend(cleanup_stale_recommendations(service, calendar_id))
        seeded = [event for event in list_window_events(service, calendar_id) if is_seed_event(event)]
        seed_titles = sorted(event.get("summary", "") for event in seeded)
        expected_titles = sorted(EXPECTED_TITLES)
        fixture_ready = len(seeded) == len(EVENTS) and seed_titles == expected_titles
        if fixture_ready:
            return removed, inserted, True

        for event in seeded:
            delete_event(service, calendar_id, event["id"])
            removed.append(event.get("summary", event["id"]))
        inserted.extend(insert_seed_events(service, calendar_id))
        return removed, inserted, False


def insert_seed_events(service, calendar_id: str) -> list[str]:
    inserted: list[str] = []
    for start, end, title, location, description in EVENTS:
        body = {
            "summary": title,
            "location": location,
            "description": f"{description}\n\nclawbench seed fixture for {TASK_ID}",
            "start": {"dateTime": start, "timeZone": TZ},
            "end": {"dateTime": end, "timeZone": TZ},
            "extendedProperties": {"private": {"clawbench_task_id": TASK_ID}},
        }
        created = service.events().insert(calendarId=calendar_id, body=body).execute()
        inserted.append(created.get("id", title))
    return inserted


def main() -> None:
    for key in ("GCALCLI_CLIENT_ID", "GCALCLI_OAUTH_B64", "GOOGLE_CALENDAR_ACCOUNT"):
        require_env(key)
    ensure_google_deps()
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = load_credentials()
    if not creds.valid:
        try:
            creds.refresh(Request())
        except Exception as exc:
            if "invalid_grant" in str(exc).lower():
                fail(
                    "OAuth token refresh failed: GCALCLI_OAUTH_B64 has been revoked "
                    "or expired (invalid_grant).\n"
                    "→ Rotate it interactively before re-running this task:\n"
                    "    python3 scripts/dev/refresh_tokens.py --provider gcalcli\n"
                    "Then re-dispatch task_103_08_hk_jpop_calendar_ticketing."
                )
            fail(f"OAuth token refresh failed; token is not usable for Google Calendar: {exc}")

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    calendar_id = calendar_id_for(service)
    removed, inserted, reused_existing = ensure_calendar(service, calendar_id)

    probe = service.events().list(
        calendarId=calendar_id,
        timeMin=TIME_MIN,
        timeMax=TIME_MAX,
        singleEvents=True,
        q="Open evening for local music",
        maxResults=10,
    ).execute().get("items", [])
    if not probe:
        fail("Calendar seed verification failed: inserted trip event was not readable.")

    manifest = Path("/tmp") / f"clawbench_{TASK_ID}_live_calendar_seed_manifest.json"
    manifest.write_text(json.dumps({
        "task_id": TASK_ID,
        "calendar_id": calendar_id,
        "time_min": TIME_MIN,
        "time_max": TIME_MAX,
        "removed_count": len(removed),
        "inserted_count": len(inserted),
        "reused_existing_fixture": reused_existing,
        "verification_count": len(probe),
    }, indent=2), encoding="utf-8")
    print(
        f"calendar fixture ready calendar_id={calendar_id} "
        f"inserted={len(inserted)} removed={len(removed)} reused={reused_existing}"
    )


if __name__ == "__main__":
    main()
