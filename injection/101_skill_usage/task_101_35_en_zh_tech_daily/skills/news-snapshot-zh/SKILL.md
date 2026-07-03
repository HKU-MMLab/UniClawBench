---
name: news-snapshot-zh
description: Build a Chinese technology digest from provided news snapshots, preserving source URLs, dates, summaries, and category groupings.
metadata:
  openclaw:
    emoji: "📰"
    category: "writing"
    tags: ["news", "digest", "chinese", "snapshot"]
---

# News Snapshot ZH Skill

Use this skill when the user provides saved news items and wants a concise
Chinese digest.

## Workflow

1. Read only the provided snapshot files unless the user explicitly asks for
   live collection.
2. Preserve each item's title, URL, source tag, publication date, and summary.
3. Rank within each source using the user's stated rule, such as recency or
   score.
4. Translate or rewrite summaries into natural Chinese without changing facts.
5. Group selected items into practical categories that match the actual
   content.
6. Do not push, post, or send the digest to external channels unless the user
   asks for that explicitly.
