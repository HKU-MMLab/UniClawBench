# Hidden Evaluation Rule — task_103_04_ai_coding_plan_subscription

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor researched current coding plans/subscriptions broadly and distinguished true Claude Code provider-plan options from IDE-only products, pure API billing, compute rental, model gateways, and API aggregators. The important outcome is an actionable, evidence-backed recommendation for heavy monthly coding work, not a generic list of AI products.

## 2. Task Contract

The public task asks for at least 10 coding plans/subscriptions, serious coverage of China-related coding plans, at least 3 plans that can be used as Claude Code providers, screenshots proving Claude Code compatibility/setup where applicable, pricing/usage-limit details, and a final recommendation. Pure API/pay-as-you-go usage should not be recommended as the main solution because the user considers direct API usage too expensive.

Completion means the executor saves a comparison artifact with links, screenshots, billing/usage limits, Claude Code provider compatibility, setup evidence for compatible plans, and a recommendation.

## 3. Source-Selection and Target-Resolution Rules

A plan counts toward the Claude Code provider requirement only when official documentation or credible current setup evidence shows it can be used directly by Claude Code as a model provider or compatible endpoint. IDE/plugin-only products may be discussed as context but do not satisfy that requirement unless a Claude Code provider path is evidenced. Compute-rental platforms, generic model gateways, and pure API/token-pack options should be excluded from final recommendations unless a fixed coding-plan provider path is documented.

China-related candidates should be researched seriously, but product subscriptions should not be counted as Claude Code provider plans unless the provider path is shown.

## 4. Ground-Truth Snapshot

Hidden references include current anchors for plausible provider/coding-plan pages, including Claude Max/pricing, Kimi plan and Claude Code/third-party-agent evidence, Alibaba coding-plan evidence, MiniMax Claude Code setup evidence, and Z.ai configuration/quick-start evidence. These anchors are not exhaustive; equivalent current official pages may satisfy the same checkpoints.

## 5. Checkpoint Rubric

- 0.20 Breadth: covers at least 10 credible coding plans/subscriptions with original links and screenshots.
- 0.20 China-related research: seriously researches China-related coding plans and identifies at least 3 credible China-related candidates.
- 0.20 Claude Code provider compatibility: identifies at least 3 plans usable directly as Claude Code providers, with official setup or Anthropic-compatible/equivalent endpoint screenshots.
- 0.15 Plan details: records pricing, quotas, request/token/usage limits, billing cycle, and relevant restrictions accurately enough for comparison.
- 0.15 Exclusion discipline: excludes pure API/pay-as-you-go, compute-rental, model-gateway, and API-aggregator platforms from final recommendations unless a fixed coding-plan provider path is documented.
- 0.10 Recommendation quality: final recommendation is useful for heavy monthly coding work and includes screenshot paths.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for severe category errors or unauditable sourcing; ordinary shortfalls in breadth, details, or screenshots should be scored through the checkpoint rubric rather than capped again.

If the final answer is dominated by pure API/pay-as-you-go billing, token packs, SiliconFlow-like gateways, or compute rental instead of coding-plan/subscription providers, cap at 0.60. If fewer than 3 Claude Code-compatible provider plans are supported by official setup or endpoint evidence, cap at 0.70. If IDE-only products or standalone CLIs are repeatedly treated as Claude Code provider plans without compatibility evidence, cap at 0.65. If the research is superficial enough to consider fewer than 6 credible plans total, cap at 0.65. If provider claims are mostly unsupported by links/screenshots, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has a partial list but has not yet proven Claude Code compatibility, has fewer than 10 plans, or lacks screenshots/usage-limit details. Prefer `fail` when the executor finishes with mostly API/gateway/rental options, no setup evidence for Claude Code providers, or a recommendation that contradicts the user's cost and provider-plan constraints.

## 8. Hidden Reference Assets

- `ground_truth.json`: acceptable plan categories, known compatible/provider examples, exclusion notes, and screenshot index.
- `provider_evidence/*.png`: current reference screenshots for pricing, setup, compatibility, and provider docs.

## 9. Dynamic Content Note

Pricing, quotas, and product packaging can change. Accept current official documentation or screenshots that are more recent than the hidden snapshot. Do not penalize changed prices when the executor captures current evidence. Do penalize category errors such as recommending pure API billing as a subscription plan.
