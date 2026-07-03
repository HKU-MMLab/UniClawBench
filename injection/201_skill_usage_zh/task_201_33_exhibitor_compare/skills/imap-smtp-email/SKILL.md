---
name: imap-smtp-email
license: MIT
description: >
  This skill should be used when the user needs to read, draft, or send emails
  programmatically. It handles IMAP inbox reading, SMTP sending, email parsing
  (headers, attachments, threading), and drafting professional messages.
  Trigger phrases include "send email", "draft email", "read inbox",
  "email summary", "forward this as email".
---

# IMAP/SMTP Email Skill

> **GitHub**: [https://github.com/nicobytes/imap-smtp-email](https://github.com/nicobytes/imap-smtp-email)

Read, draft, and send emails via standard IMAP/SMTP protocols. Parse email
threads, extract attachments, and compose professional messages with proper
formatting.

## Usage

```
"Draft an email summarizing this report for my team"
"Read the last 10 emails from marketing@"
"Forward this analysis to the stakeholders"
"Compose a follow-up email based on these meeting notes"
```

## Capabilities

1. **Draft professional emails** — compose well-structured emails from content,
   with appropriate subject lines, greetings, and signatures
2. **Parse email threads** — extract message chains, identify participants,
   summarize conversation flow
3. **Format for sending** — produce RFC-compliant email bodies (plain text and
   HTML variants) ready for SMTP delivery
4. **Attachment handling** — reference and describe attachments without
   requiring actual file transfer in offline mode

## Output Format

When drafting, produces:
- `subject` — email subject line
- `to`, `cc` — recipient lists
- `body_text` — plain text body
- `body_html` — HTML formatted body (optional)

## When to Use

Use this skill when a deliverable needs to be packaged as a professional email
for stakeholders, or when inbox triage and summarization is required.
