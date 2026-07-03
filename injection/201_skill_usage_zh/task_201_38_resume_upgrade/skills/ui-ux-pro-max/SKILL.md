---
name: ui-ux-pro-max
license: MIT
description: >
  This skill should be used when the user needs UI/UX design analysis,
  layout evaluation, visual hierarchy assessment, or document formatting
  guidance. It evaluates readability, spacing, typography choices, and
  overall visual presentation quality. Trigger phrases include "review layout",
  "check formatting", "visual assessment", "UI feedback", "design review",
  "improve readability".
---

# UI/UX Pro Max Skill

> **GitHub**: [https://github.com/nicobytes/ui-ux-pro-max](https://github.com/nicobytes/ui-ux-pro-max)

Provides expert-level UI/UX design intelligence for evaluating and improving
visual layouts, document formatting, and readability. Works with web pages,
documents, resumes, presentations, and any visual artifact.

## Usage

```
"Review the layout of this resume for visual clarity"
"Is this document easy to scan? What would you change?"
"Evaluate the formatting and typography choices"
"How can I improve the visual hierarchy?"
"Check if this follows standard document design patterns"
```

## Capabilities

1. **Layout analysis** — evaluates whitespace, margins, section spacing,
   and overall page balance
2. **Typography assessment** — checks font choices, sizes, weight contrast,
   and readability
3. **Visual hierarchy** — ensures important information is prominent and
   the scanning path is logical
4. **Document formatting** — applies best practices for resumes, reports,
   proposals, and professional documents
5. **Accessibility** — flags contrast issues, font size problems, and
   structure that hinders screen readers

## Output Format

Produces a structured assessment with:
- `overall_score` — 1-10 rating
- `strengths[]` — what works well
- `issues[]` — each with severity, location, and suggested fix
- `recommendations[]` — prioritized improvements

## When to Use

Use this skill when evaluating or improving the visual presentation of any
document, especially when the output needs to look professional and
be easy to scan quickly (resumes, executive summaries, dashboards).
