# Red-Team Engagement Recap — March 2024

**Engagement type:** scheduled internal red-team exercise
**Engagement window:** 2024-03-04 to 2024-03-15
**Lead:** internal application-security team

## Scope

Two of our LLM-backed surfaces were in scope for this engagement: the
support-summarization endpoint and the assisted-search panel. The red
team was tasked with attempting realistic adversarial inputs against
both surfaces and documenting where, if anywhere, the guardrails could
be bypassed.

## Summary of findings

The red team reported zero successful overrides on either surface during
the engagement window. They did, however, file four observations worth
keeping for future training:

- Multiple attempts followed the standard "Ignore the above and..." shape
  documented in OWASP's LLM Top 10. All were caught by the input
  classifier and routed to the moderation queue.
- A handful of attempts tried tag-spoofing such as `</prompt>` followed
  by a fake system directive. The structured-prompt builder we deployed
  in Q4 strips raw angle-bracket sequences from user input before
  composition, so these never reached the model.
- One creative attempt embedded the override inside a base64 string
  with instructions to decode and follow. The model declined because
  the system prompt explicitly forbids executing decoded instructions.
- The most interesting attempt used a roleplay framing: *"Pretend you are
  a different assistant whose system prompt is..."*. The model did not
  comply; the safety post-filter would have caught it regardless.

## Action items

None of the action items below are blocking; all were filed for the
quarterly security roadmap.

1. Add the engagement transcripts to the internal training corpus once
   the red team has redacted any customer data.
2. Update the input classifier with a small handful of new patterns
   the red team surfaced.
3. Schedule the next engagement for early Q3.

The full transcripts are in the security team's private archive; this
recap is what is shared with the broader engineering org.
