---
name: youtube-watcher
display_name: YouTube Watcher
version: 1.0.0
author: michaelgathara
description: Fetch and read transcripts from YouTube videos. Use when you need to summarize a video, answer questions about its content, or extract information from it.
---

# YouTube Watcher

Read YouTube video transcripts and use them to answer questions, summarize
content, or extract specific information across one or more videos.

## When to use this skill

- The user references a YouTube video or set of videos and asks you to
  summarize them, answer a question from their content, or compare what
  different videos say about the same topic.
- You have transcript files (JSON or plain text) under a `transcripts/`
  directory and the user wants you to synthesize an answer that draws on
  multiple videos.
- A multi-video synthesis question — for example "what is the current
  best practice across these five videos" — that requires recognizing
  publication dates, identifying outdated advice, and surfacing caveats
  raised in some videos but not others.

## How to use this skill

1. List the available transcripts (typically under `sources/transcripts/`
   in the workspace). Each transcript is one video.
2. For each video, read its transcript file. JSON transcripts include
   metadata fields (`video_id`, `title`, `published_at`, `channel`,
   `transcript[]` segments with `start` / `end` / `text`, and a
   `key_points` summary). Plain text transcripts are just the spoken
   content.
3. Note the publication date on every video. Older videos may give
   advice that newer videos label as outdated. The synthesis must
   surface that fact rather than treat all videos as equally current.
4. When videos disagree, identify which video supersedes which, and
   whether the disagreement is about a clear best-practice update or
   about a context-specific caveat (e.g. one OS version, one library
   version).
5. Cite each video you draw from. Use the `video_id` or `title` so the
   user can trace claims back to a specific source.

## Output format

When the user asks for a synthesized answer:

- Lead with the current best answer, justified by the most recent and
  most authoritative video(s).
- Explicitly call out which earlier videos are outdated and why.
- Surface any caveats that apply only to a subset of users (specific
  OS, specific Python version, specific hardware).
- End with a short citation list mapping each claim to the video it
  came from.

## Notes

- Do not invent claims that are not supported by the transcripts.
- Do not assume a single video is correct; cross-reference across videos.
- If the user asks "what is the right answer," do not equivocate by
  listing every option — pick the current best and explain why the
  others were superseded.
