---
name: google-calendar-gcalcli
description: Install and use gcalcli for live Google Calendar read access using the provided OAuth cache.
---

# Google Calendar / gcalcli

Use this skill whenever the task asks you to inspect the user's Google Calendar. The task expects live Google Calendar read access through `gcalcli`. Do not treat a missing `gcalcli` binary as a blocker, and do not use offline calendar exports.

1. First check whether `gcalcli` is available:
   ```bash
   command -v gcalcli && gcalcli --help | head
   ```
2. If `gcalcli` is not installed, install it yourself in the current runtime. Shell commands run as root, so do not ask for privilege escalation and do not use `sudo`.
   Preferred apt route:
   ```bash
   apt-get update
   apt-get install -y gcalcli
   command -v gcalcli && gcalcli --help | head
   ```
   If the apt route fails, try the pip route:
   ```bash
   python3 -m pip install --no-cache-dir --break-system-packages gcalcli
   command -v gcalcli && gcalcli --help | head
   ```
   Save a short install/verification note under `/tmp_workspace/results/` if installation was needed or failed.
3. Use the environment variables only as runtime inputs. Do not print their values into reports or screenshots, including the account hint:
   - `GCALCLI_CLIENT_ID`
   - `GCALCLI_CLIENT_SECRET`
   - `GCALCLI_OAUTH_B64`
   - `GOOGLE_CALENDAR_ACCOUNT`
4. Before calling `gcalcli`, materialize the OAuth cache where gcalcli actually looks for it:
   ```bash
   mkdir -p "$HOME/.local/share/gcalcli"
   printf '%s' "$GCALCLI_OAUTH_B64" | base64 -d > "$HOME/.local/share/gcalcli/oauth"
   cp "$HOME/.local/share/gcalcli/oauth" "$HOME/.gcalcli_oauth"
   chmod 600 "$HOME/.local/share/gcalcli/oauth" "$HOME/.gcalcli_oauth"
   ```
5. Verify live access and then read the calendar for the trip window. Infer the trip's local timezone from the event locations and timestamps before finalizing the itinerary. If the display looks offset from the location's local time, normalize the final markdown calendar to the trip's local timezone rather than blindly copying the agenda output:
   ```bash
   gcalcli --client-id "$GCALCLI_CLIENT_ID" --client-secret "$GCALCLI_CLIENT_SECRET" list
   gcalcli --client-id "$GCALCLI_CLIENT_ID" --client-secret "$GCALCLI_CLIENT_SECRET" agenda "2026-06-03 00:00" "2026-06-10 00:00"
   ```
   Save only a short success/failure note or a redacted screenshot; do not expose token material or the account value.
6. Do not add, edit, or delete Google Calendar events for this task. The final handoff should be a markdown calendar under `/tmp_workspace/results/concert_calendar.md`, grounded in the live agenda plus ticketing screenshots.
7. Keep calendar conclusions grounded in visible live calendar entries, then combine them with ticketing screenshots.
