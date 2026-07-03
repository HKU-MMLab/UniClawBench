---
name: airtable-pat-rest
description: Read Airtable bases, tables, and records with the official REST API using a provided personal access token.
metadata:
  clawdbot:
    emoji: "📊"
    requires:
      env:
        - AIRTABLE_PAT
        - AIRTABLE_BASE_ID
        - AIRTABLE_TABLE_NAME
---

# Airtable PAT REST Skill

Use the Airtable REST API directly. The credentials and target table are already provided as environment variables; do not create an OAuth connection, request new credentials, or use a third-party gateway.

## Runtime Inputs

- `AIRTABLE_PAT`: bearer token for the Airtable API.
- `AIRTABLE_BASE_ID`: target base id.
- `AIRTABLE_TABLE_NAME`: target table name.

## Read Records

```bash
python3 - <<'PY'
import json, os, urllib.parse, urllib.request

base = os.environ["AIRTABLE_BASE_ID"]
table = urllib.parse.quote(os.environ["AIRTABLE_TABLE_NAME"])
url = f"https://api.airtable.com/v0/{base}/{table}?pageSize=100"
headers = {"Authorization": f"Bearer {os.environ['AIRTABLE_PAT']}"}
records = []
while url:
    req = urllib.request.Request(url, headers=headers)
    data = json.load(urllib.request.urlopen(req, timeout=60))
    records.extend(data.get("records", []))
    offset = data.get("offset")
    url = f"https://api.airtable.com/v0/{base}/{table}?pageSize=100&offset={urllib.parse.quote(offset)}" if offset else None
print(json.dumps(records, indent=2, ensure_ascii=False))
PY
```

When a snapshot file is provided by the task, read it instead of calling the live API.
