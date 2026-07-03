---
name: runesleo-systematic-debugging
description: Four-phase debugging framework that ensures root cause investigation before attempting fixes. Never jump to solutions.
metadata:
  {
    "openclaw":
      {
        "version": "1.0.0",
        "author": "runesleo",
        "license": "MIT-0",
        "tags": ["debugging", "rca", "root-cause", "framework", "incident-analysis"],
        "category": "engineering-practice"
      }
  }
---

# Systematic Debugging

A five-phase debugging framework prioritizing root cause investigation
before fixes.

## The Iron Law

> **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**
> **NO INVESTIGATION WITHOUT CONTEXT RECALL FIRST**

"ALWAYS find root cause before attempting fixes. Symptom fixes are failure."

The framework enforces sequential completion: Phase 0 → Phase 1 → Phase 2 →
Phase 3 → Phase 4. Skipping ahead is the most common failure mode.

## Phase 0 — Context Recall

* Search prior knowledge: error keywords, documentation, git history.
* Extract recurring tokens / signals from the symptom.
* Output a recall summary BEFORE proceeding.
* Do not attempt repro yet.

## Phase 1 — Root Cause Investigation

* Read the error message **completely** — every line.
* Reproduce the issue consistently before forming hypotheses.
* Check recent changes (git log, deploy log, config drift).
* Gather diagnostic evidence at component boundaries (logs, traces, state dumps).
* Trace data flow back to the source.

## Phase 2 — Pattern Analysis

* Find a known-working example or reference implementation.
* Read the working example completely.
* Identify differences between working and broken code / state.
* Understand transitive dependencies.

## Phase 3 — Hypothesis & Testing

* Form **one** specific hypothesis at a time.
* Test minimally — change one variable, isolate the effect.
* Verify before continuing. If the test refutes the hypothesis, return to
  Phase 2 (don't escalate to a different hypothesis without analysis).

## Phase 4 — Implementation

* Create a failing test case first.
* Implement a single fix that addresses the root cause.
* Verify the fix works against the failing test and the original repro.
* If three or more fix attempts fail, **stop** and question architectural
  soundness — do not stack a fourth fix.

## Cross-incident application

When this framework is applied to multiple incident postmortems together
(the cross-incident pattern):

* Phase 0 = scan all postmortems and pull recurring keywords (e.g. "config drift",
  "WAF regex", "DB migration", "BGP", "CIDR").
* Phase 1 = for each candidate root-cause family, re-read the postmortems'
  Detection / Recovery / Contributing-Factors sections; map each incident
  to which root-cause families it touches.
* Phase 2 = compare incidents that share a family — what's common, what's
  different? Look for the same trigger surfaced through different blast
  radii.
* Phase 3 = formulate a small set of cross-incident hypotheses ("we keep
  failing at config-drift detection because X").
* Phase 4 = for each confirmed cross-incident pattern, propose a single
  preventative action with a concrete owner and signal.

## Red flags — restart at Phase 1

* "Quick fix for now, investigate later."
* "Just try changing X."
* Proposing a fix before tracing data flow.
* "One more fix" attempt after multiple failures.
* Stacking 3+ fixes without architectural review.

## Runtime

This skill is instruction-only. The workspace injects it at
`/root/skills/runesleo-systematic-debugging`. There is nothing to install.
