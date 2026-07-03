# Hidden Evaluation Rule — Exploration v2 · MusicBrainz ws/2 API (MBID → release groups, proper UA)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** task graded by
**outcome plus mechanism evidence**.

The executor must:

- use the MusicBrainz **ws/2** web service (browse/lookup) keyed by the
  artist MBID from the page URL, with a proper **User-Agent**, to fetch the
  artist's **album-type release groups** — not scrape the musicbrainz.org HTML, and
- save auditable evidence (request URL(s) + raw JSON).

Difficulty: knowing the page id is an **MBID**, finding the ws/2 endpoint and
the correct query (`browse release-group?artist=<MBID>&type=album` or
`lookup artist/<MBID>?inc=release-groups`), requesting JSON (`fmt=json`), and
respecting the UA + rate-limit etiquette.

Grading anchors on the mechanism + **immutable historical album facts**.

## 2. Task Contract

Start from `https://musicbrainz.org/artist/5b11f4ce-a62d-471e-81fc-a69a8278c7da`.
Use ws/2 to pull this artist's album release groups; report the artist name
(from the API), the three earliest studio albums (title + year) by first-release
date, and the total album-type release-group count the API reports. Save
`musicbrainz_albums.json` and a `musicbrainz_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Target identity & endpoint

- Artist MBID: **`5b11f4ce-a62d-471e-81fc-a69a8278c7da`** = **Nirvana** (the US
  grunge band; note MusicBrainz disambiguates multiple "Nirvana" artists — this
  MBID is the correct one).
- Correct endpoints (either is fine):
  - `https://musicbrainz.org/ws/2/release-group?artist=5b11f4ce-a62d-471e-81fc-a69a8278c7da&type=album&fmt=json&limit=...`
  - or `https://musicbrainz.org/ws/2/artist/5b11f4ce-a62d-471e-81fc-a69a8278c7da?inc=release-groups&fmt=json`
- A meaningful `User-Agent` is required by MusicBrainz policy.

### 3.2 Immutable album facts (anchor here)

The three earliest studio albums by first-release date:

| title       | first-release year |
| ----------- | ------------------ |
| Bleach      | 1989               |
| Nevermind   | 1991               |
| In Utero    | 1993               |

These three studio albums and their years are historical facts and do not
change. (Order by `first-release-date` ascending: Bleach 1989-06-15, Nevermind
1991-09-24, In Utero 1993-09-21.)

### 3.3 Release-group count (tolerant)

The total album-type release-group count (`release-group-count`) is large
(hundreds — it includes compilations, live albums, reissues across the world,
not just the studio LPs). At construction it was around **650+**. This number
**grows** as the community adds entries. Grade the count as correct if it
matches the executor's **own** captured response (internal consistency), and is
plausibly in the hundreds — do **not** hardcode a fixed number. The "three
earliest studio albums" requirement is what disambiguates real exploration from
guessing, since the executor must filter the large album set by date.

## 4. Expected Artifacts

- `/tmp_workspace/results/musicbrainz_albums.json` — artist name, three earliest
  studio albums (title + year), total album release-group count.
- `/tmp_workspace/results/musicbrainz_evidence/` — request URL(s) + raw JSON.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                              | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| CP1 | Data came from the MusicBrainz ws/2 API keyed by the MBID, with a real User-Agent, evidenced by saved request URL + raw JSON (not HTML scraping).  | 0.30   |
| CP2 | Artist confirmed as Nirvana from the API.                                                                                                           | 0.15   |
| CP3 | The three earliest studio albums correctly identified: Bleach (1989), Nevermind (1991), In Utero (1993), ordered by first-release date.            | 0.30   |
| CP4 | A total album release-group count is reported and is consistent with the executor's own captured response (plausibly in the hundreds).             | 0.15   |
| CP5 | `musicbrainz_evidence/` makes the pull reproducible.                                                                                                | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the data was obtained by **scraping the musicbrainz.org
  HTML** (or a third-party site) instead of the ws/2 API.
- **cap at `0.55`** if no `musicbrainz_evidence/` is saved.
- **cap at `0.60`** if no User-Agent was sent (against MB policy) AND/OR the
  executor only fetched the bare artist record without enumerating release
  groups.
- **cap at `0.40`** if the wrong "Nirvana" artist (a different MBID) or a wrong
  artist entirely was used.
- **cap at `0.70`** if the three earliest albums are wrong (e.g. listing
  compilations/EPs ahead of the studio LPs, or wrong years).

Do **not** cap or fail merely because:

- the total count differs from any reference number — it grows; judge against
  the captured response,
- the executor used `lookup ... inc=release-groups` vs `browse release-group` —
  either is fine,
- the executor used `curl`/python/agent-browser to hit the endpoint.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4, CP5 all satisfied, no
cap fired. (CP1+CP2+CP3 are mandatory; CP4 and CP5 must also hold to clear the
0.90 threshold.)

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor located ws/2 but hasn't enumerated/ordered
release groups, or has data but no saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped HTML, used the
wrong MBID, or reported earliest albums inconsistent with the captured data.

## 8. Hidden Reference Assets

None shipped. Evaluate from `musicbrainz_albums.json`, `musicbrainz_evidence/`,
and the transcript (look for a ws/2 call with a User-Agent).

## 9. Dynamic Content Note

The studio-album facts are immutable; only the aggregate release-group count
drifts upward. Anchor on the three earliest albums + mechanism; never hardcode
the count.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the musicbrainz.org page fetch used as
  the data source instead of `/ws/2/`.
- When scoring CP3, confirm the three albums + years are derivable from the
  executor's own captured release-group list ordered by first-release date.
- Guidance tags: `mbid_keyed_ws2`, `required_user_agent`,
  `earliest_by_release_date`, `tolerant_aggregate_count`.
