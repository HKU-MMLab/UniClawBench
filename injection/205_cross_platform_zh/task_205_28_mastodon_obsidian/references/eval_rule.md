# Hidden Evaluation Rule — task_205_28_mastodon_obsidian

## 1. Grading Philosophy

Grade on whether the executor produced a high-quality Obsidian-style
vault from 8 immutable Mastodon posts (5 from @Mastodon, 3 from @Gargron).
The platform-specific challenge is producing CARDS THAT WORK IN OBSIDIAN
— meaning each card must have valid YAML frontmatter (parseable by
Obsidian's Dataview/properties UI), the body must be readable markdown
that preserves the original post's content, hashtags should be embedded
as Obsidian-friendly `#tag` syntax in the body, and the INDEX must use
proper subsection headings + `[[wikilinks]]` so Obsidian's graph view
and backlink panel actually work. Anchor identity checks against the
8 immutable post IDs and on a per-post content keyword. Be lenient on
filenames and JSON shape beyond the minimum schema.

## 2. Task Contract

Required deliverables:

- `/tmp_workspace/results/vault/<post_id>.md` × 8 — one per post id.
  Each card MUST start with a YAML frontmatter block delimited by `---`
  lines on the first and last frontmatter lines. The frontmatter MUST
  contain at minimum `id`, `author`, `date`, `url`, `replies`, `reblogs`
  keys. Body MUST be readable markdown derived from the original
  HTML content.
- `/tmp_workspace/results/vault/INDEX.md` — markdown index with two
  level-2 headings: one matching `^##\s*@?Mastodon` and one matching
  `^##\s*@?Gargron`. Mastodon section lists the 5 post ids in date-desc
  order; Gargron section lists the 3 in date-desc order. Each post
  must appear as `[[<post_id>]]` Obsidian wiki-link.
- `/tmp_workspace/results/cards.json` — JSON with `posts` (array of 8)
  and `hashtag_freq` (object).

## 3. Source-Selection Rules

Canonical sources are LIVE APIs:
- Public read API: `curl https://mastodon.social/api/v1/statuses/<id>`
  (no auth required; these are public posts).

NO snapshot file. NO mock. Reading from any local fixture file under
`/tmp_workspace/clawbench/` is undefined behaviour.

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`. Key anchors:

- `post_ids_desc_global` — exact 8-element list (by date desc) for the
  `cards.json.posts` ordering check.
- `post_ids_desc_by_author.Mastodon` — exact 5-element ordered list.
- `post_ids_desc_by_author.Gargron` — exact 3-element ordered list.
- For each post: `id`, `author`, `url`, `created_at`, `created_date`,
  `content_keyword` (substring expected in the rendered body).
- `expected_top5_hashtags_lower_set` — the set of distinct lowercase
  hashtags across all 8 posts:
  `{mastodon, merchtodon, plushtodon, thedearhunter, gleeb}`
  (each appears exactly once across the 8 posts).

`replies_count` / `reblogs_count` are DYNAMIC — eval only checks they
are non-negative integers in cards.json.

## 5. Checkpoint Rubric

Weights sum to 1.0.

- 0.13 — `cards.json` parses; `posts` is an array of length 8; each
  element has all keys (`id`, `author`, `url`, `created_at`,
  `replies_count`, `reblogs_count`, `card_filename`); the set of `id`
  values equals the set in `post_ids_desc_global`; the array ordering
  exactly equals `post_ids_desc_global`.
- 0.18 — All 8 card files exist on disk and are non-empty AND start
  with a valid YAML frontmatter block. Frontmatter MUST contain at
  minimum the keys `id`, `author`, `date`, `url`, `replies`, `reblogs`.
  The frontmatter `id`, `author`, and `url` values MUST match the
  corresponding ground-truth post (case-sensitive). YAML must parse
  cleanly (quotes correct, no broken indentation).
- 0.18 — Card body quality: for at least 7 of 8 cards, the body text
  (everything after the closing `---`) MUST contain the per-post
  `content_keyword` substring (case-sensitive). The body must NOT
  be empty (≥ 30 characters per card after stripping whitespace).
- 0.18 — `INDEX.md` exists; contains two level-2 headings — one
  matching the regex `^##\s*@?Mastodon\b` and one matching
  `^##\s*@?Gargron\b`. Under each heading, the corresponding post-ids
  appear in date-desc order, with each post referenced as `[[<post_id>]]`
  somewhere in its line. Both sections must contain ALL their post-ids
  in the correct order (5 for Mastodon, 3 for Gargron).
- 0.09 — `cards.json.hashtag_freq` is a JSON object whose set of keys
  (compared lowercase) equals `expected_top5_hashtags_lower_set`. Every
  value MUST be a positive integer (typically 1; tolerance is on the
  set membership, not the count).
- 0.13 — INDEX summary: each `[[<post_id>]]` line in INDEX.md MUST
  also include either the post date (the `created_date` substring like
  `2026-04-30`) OR a short content snippet drawn from the post body.
  At least 6 of 8 lines must satisfy this.
- 0.11 — Language detection. Each post in `cards.json.posts` MUST have
  a `primary_language` field whose value is a short ISO 639-1 code
  string (e.g. `"en"`, `"ja"`). At least 7 of 8 must match the
  Mastodon-API-reported `language` for that status (the per-post
  `expected_language` in `ground_truth.json`). AND `cards.json` MUST
  have a top-level `language_distribution` object whose values are
  positive integers summing to 8. The `en` count must be in
  `[6, 8]` (≥6 English posts) AND the `ja` count must be ≥1 (one
  Japanese post is anchored). Tolerance ±1 on any single non-`en`
  bucket count, but `ja` must be present.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- Fewer than 6 of the 8 card files exist → 0.30.
- Output fabricates post ids / urls not in ground truth → 0.40.
- `$MASTODON_ACCESS_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero curl / toot / browser activity for the live posts
  (synthetic data only) → 0.40.
- INDEX.md missing OR missing the two-author grouping → cap 0.55.
- Card frontmatter missing on >=3 of 8 cards (i.e. plain markdown,
  no YAML block) → cap 0.50.
- `cards.json` missing → cap 0.45.

Pass requires: structural cards.json checkpoint, all-8-cards frontmatter
checkpoint, body-keyword checkpoint, INDEX two-section checkpoint,
hashtag-set checkpoint, AND language-detection checkpoint all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to fix
  the lowest-scoring deliverable (most often INDEX two-section ordering
  or a card with broken frontmatter).
- **Fail** < 0.50.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All structural anchors (`id`, `url`, `created_at`, content keyword,
`tags_lower`) are immutable — the 8 chosen posts are public and stable.
`replies_count` and `reblogs_count` ARE dynamic and intentionally NOT
part of the eval.

If the Mastodon API is temporarily unavailable, the supervisor MUST
distinguish "executor failed" from "API outage" — record `infra_error`
and avoid penalising.
