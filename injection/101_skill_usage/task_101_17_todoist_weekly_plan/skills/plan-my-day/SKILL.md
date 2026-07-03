---
name: plan-my-day
description: Turn a dated task list into a concise weekly time-block plan, CSV schedule, and calendar-friendly event list.
metadata:
  clawdbot:
    emoji: "📅"
---

# Time Block Planner Skill

Use this skill when the user has tasks with due dates, priorities, projects,
or durations and wants a practical weekly plan.

## Planning Rules

1. Group tasks by due date and project.
2. Put P1/P2 work before lower-priority work due the same day.
3. Use supplied durations when available; otherwise choose a realistic block
   length and explain the reason briefly.
4. Keep each day concise. Do not invent filler tasks for empty days.
5. Avoid overlapping blocks in CSV or calendar output.
6. Keep Markdown, CSV, and calendar event titles aligned so the user can
   cross-check them later.
