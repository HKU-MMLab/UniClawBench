---
name: notion-token-api
description: Read Notion pages, blocks, and child pages through the Notion API using the provided integration token.
metadata:
  clawdbot:
    emoji: "📝"
    requires:
      env:
        - NOTION_API_TOKEN
---

# Notion Token API Skill

Use the provided `NOTION_API_TOKEN`. Do not create a new integration, write tokens to disk, or request additional credentials.

## Read Search/Page Data

```bash
python3 - <<'PY'
import json, os, urllib.request

headers = {
    "Authorization": f"Bearer {os.environ['NOTION_API_TOKEN']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
req = urllib.request.Request(
    "https://api.notion.com/v1/search",
    headers=headers,
    data=json.dumps({"page_size": 100}).encode(),
    method="POST",
)
print(json.dumps(json.load(urllib.request.urlopen(req, timeout=60)), indent=2, ensure_ascii=False))
PY
```

If the task gives you an exported Notion snapshot, read that file and preserve the supplied page ids in outputs.
