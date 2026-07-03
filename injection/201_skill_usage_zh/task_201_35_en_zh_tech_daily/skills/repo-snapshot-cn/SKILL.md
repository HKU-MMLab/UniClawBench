---
name: repo-snapshot-cn
description: Summarize provided GitHub repository snapshots in Chinese, ranking by supplied stars, topics, dates, or other local metadata.
metadata:
  openclaw:
    emoji: "📈"
    category: "developer"
    tags: ["github", "repos", "snapshot", "chinese"]
---

# Repo Snapshot CN Skill

Use this skill when the user provides saved GitHub repository metadata and
wants a Chinese ranking or digest.

## Workflow

1. Read the local repository snapshot instead of fetching live GitHub data.
2. Rank repositories by the user-specified metadata, such as stars, creation
   date, language, or topics.
3. Translate English descriptions into concise Chinese while preserving names,
   URLs, star counts, and technical terms.
4. Keep enough metadata in the output for the user to verify each repository.
5. Do not call GitHub live APIs unless the prompt explicitly asks for a live
   refresh.
