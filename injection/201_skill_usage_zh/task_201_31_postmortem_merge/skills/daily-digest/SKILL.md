---
name: daily-digest
description: Generates a daily digest from stored memory files, summarizing decisions, lessons, actions, and questions into a dated journal entry.
metadata:
  {
    "openclaw":
      {
        "version": "1.0.0",
        "author": "pmaeter",
        "license": "MIT-0",
        "tags": ["digest", "journal", "summary", "decisions", "lessons", "actions"],
        "category": "knowledge-consolidation"
      }
  }
---

# Daily Digest

## Purpose

Generate a digest from a set of dated source files. The output is a
single Markdown document organized by:

* **Decisions** — concrete choices the source files committed to.
* **Lessons** — what was learned (from a mistake, a near-miss, or an
  unexpected outcome).
* **Actions** — concrete steps that should be taken (or were taken) as a
  follow-up.
* **Questions** — open questions or unresolved threads.

Each section is grounded in source-file references so any line can be
traced back to the file that motivated it.

## Inputs

* A directory (or list) of dated source files. Canonical naming format
  is ISO `YYYY-MM-DD.md`, but the digest workflow accepts any filename
  containing a date.

## Output

* `digest-YYYY-MM-DD.md` (one digest per run) with the four sections
  above. Each bullet ends with a citation in the form `(<source-file>)`.

## Workflow

1. List the source files; sort them chronologically.
2. For each file, scan for cues:
   * **Decisions:** "we decided", "we'll go with", "approved", "ship it".
   * **Lessons:** "we learned", "in retrospect", "next time", "root cause was".
   * **Actions:** "TODO", "next step", "owner:", "ETA", "follow-up".
   * **Questions:** "?", "open question", "still unclear", "TBD".
3. Bucket the extractions into the four sections, dedup by meaning
   (not exact string), and keep the original wording where possible.
4. For multi-source synthesis, group bullets that recur in ≥ 2 source
   files (this is your "common patterns" view) and call out single-
   source items separately.
5. Output the digest as Markdown, one bullet per finding, with the
   source filename appended to each bullet.

## Application to incident postmortems

When the source files are incident postmortems rather than daily memory
files, the same four sections still apply:

* **Decisions** ↔ commitments / mitigations / accepted risk in the
  postmortem.
* **Lessons** ↔ contributing factors / "what we learned" sections.
* **Actions** ↔ action items / preventative measures.
* **Questions** ↔ open follow-ups / unresolved root-cause threads.

The "common pattern" multi-source grouping is what turns a digest into a
cross-incident insights view.

## Runtime

The workspace injects this skill at `/root/skills/daily-digest` as an
instruction-only skill. There is nothing to install. Apply the workflow
above directly to the source files indicated by the user.
