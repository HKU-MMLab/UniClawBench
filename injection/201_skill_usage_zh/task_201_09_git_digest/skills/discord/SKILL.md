---
name: discord
license: MIT
description: >
  This skill should be used when the user needs to interact with Discord —
  posting messages, reading channel history, formatting content for Discord's
  Markdown dialect, or managing webhooks. Trigger phrases include "post to
  Discord", "Discord message", "format for Discord", "Discord channel",
  "send to Discord".
---

# Discord Skill

> **GitHub**: [https://github.com/CyberTimon/discord](https://github.com/CyberTimon/discord)

Interact with Discord servers — post messages, read channel history, format
content for Discord's specific Markdown flavor, and manage webhook
integrations.

## Usage

```
"Post this summary to our #dev-updates channel"
"Format this report for Discord"
"Read the last 20 messages from #general"
"Send a webhook notification with these build results"
```

## Capabilities

1. **Format for Discord Markdown** — converts standard Markdown to Discord's
   dialect (code blocks, embeds, mentions, max 2000 chars per message,
   multi-message splitting)
2. **Post messages** — sends formatted messages to specified channels via
   bot token or webhook
3. **Read channel history** — retrieves and parses recent messages from
   a channel
4. **Embed creation** — builds rich embeds with titles, fields, colors,
   and footers for structured announcements

## Discord Markdown Notes

- Max message length: 2000 characters (split longer content)
- Code blocks: triple backtick with language hint
- Bold: `**text**`, Italic: `*text*`
- Headings not supported in messages (use bold + newlines)
- Embeds support richer formatting (fields, colors, thumbnails)

## Output Format

When formatting for Discord, produces:
- `messages[]` — array of message strings, each <=2000 chars
- `embeds[]` — optional rich embed objects for structured content

## When to Use

Use this skill when content needs to be posted to Discord or formatted
for Discord's specific constraints (character limits, markdown dialect,
embed structure).
