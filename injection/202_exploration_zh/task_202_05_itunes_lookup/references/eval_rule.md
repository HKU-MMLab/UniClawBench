# Hidden Evaluation Rule — Exploration v2 · iTunes/Apple undocumented lookup API (id from page URL)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** task graded by
**outcome plus mechanism evidence**.

The executor must:

- discover Apple's (largely undocumented) public **store lookup service**
  (`https://itunes.apple.com/lookup`) and use it with the artist id taken from
  the Apple Music page URL — **not** scrape the Apple Music web player DOM, and
- save auditable evidence (request URL(s) + raw JSON).

The skill tested: recognizing the numeric id in the page URL is an Apple store
id, and finding the `itunes.apple.com/lookup?id=...` service (and the
`&entity=album` variant to enumerate albums). Grading anchors on the mechanism
plus **stable artist facts**; the album list is treated as a stable-core +
tolerant-tail set (catalogs gain reissues/singles over time).

## 2. Task Contract

Start from `https://music.apple.com/us/artist/jack-johnson/909253`. Find the
lookup service, and return the artist name + primary genre, and a list of the
artist's albums (name + release year) the service returns for this artist.
Save `itunes_artist.json` and an `itunes_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Target identity & endpoint

- Apple store id: **`909253`** (artist Jack Johnson).
- Correct endpoint: **`https://itunes.apple.com/lookup?id=909253`** for the
  artist record, and **`https://itunes.apple.com/lookup?id=909253&entity=album`**
  to enumerate albums (first result is the artist wrapper; subsequent results
  are `collection` album records). `country`/`limit` params are fine.

### 3.2 Stable artist facts (anchor here)

From the artist wrapper record:

- `artistName` = **`Jack Johnson`**
- `wrapperType` = `artist`, `artistId` = `909253`
- `primaryGenreName` = **`Rock`** (accept the genre string the API returns; it
  is stable for this artist)

### 3.3 Albums (stable core + tolerant tail)

The `&entity=album` response returns the artist's albums as `collection`
records, each with `collectionName` and `releaseDate`. A correct answer must
include at least the well-known core albums the service returns, for example:

- `In Between Dreams` (2005)
- `Brushfire Fairytales` (2001)
- `On and On` (2003)
- `Sleep Through the Static` (2008)

(Exact titles may carry suffixes like "(Bonus Track Version)" / "(Remastered)";
accept those variants. Release **year** should match the API's `releaseDate`.)

**Do not** require an exact album count or an exact set: Apple adds
remasters/live/compilation editions over time and storefront/region affects the
list. Grade album coverage against the executor's **own** `entity=album`
response (internal consistency: the saved albums are a faithful, deduplicated
rendering of the records actually returned), plus presence of a reasonable core.

## 4. Expected Artifacts

- `/tmp_workspace/results/itunes_artist.json` — artist name, primary genre,
  album list (name + release year).
- `/tmp_workspace/results/itunes_evidence/` — request URL(s) + raw JSON.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                | Weight |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Data came from the `itunes.apple.com/lookup` service using id `909253`, evidenced by saved request URL + raw JSON (not Apple Music DOM scraping).    | 0.30   |
| CP2 | Artist identity correct: `Jack Johnson` + primary genre as returned (`Rock`).                                                                         | 0.20   |
| CP3 | Albums enumerated via the `entity=album` lookup; saved album list faithfully reflects the returned `collection` records (name + year).               | 0.25   |
| CP4 | Saved albums include the reasonable core set (Section 3.3) and years match the API's `releaseDate`.                                                   | 0.15   |
| CP5 | `itunes_evidence/` makes the pull reproducible.                                                                                                       | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if albums/artist info were obtained by **scraping the Apple
  Music web player DOM** or a third-party site instead of the lookup service.
- **cap at `0.55`** if no `itunes_evidence/` is saved.
- **cap at `0.60`** if only the bare artist record was fetched and no album
  enumeration (`entity=album`) was performed.
- **cap at `0.40`** if the wrong artist / id was used.
- **cap at `0.85`** if the saved album list does not match the executor's own
  captured response (fabricated or hallucinated entries).

Do **not** cap or fail merely because:

- the album list differs from any reference count — catalogs grow; judge against
  the captured response,
- titles carry "(Remastered)"/"(Bonus...)" suffixes,
- the executor added `country`/`limit` params or used `curl`/python/agent-browser
  to hit the endpoint.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3 satisfied, CP4 satisfied, no
cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has the artist record but hasn't enumerated
albums, or has data but no saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped the DOM, used
the wrong artist, or saved albums absent from any captured response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `itunes_artist.json`, `itunes_evidence/`, and the
transcript.

## 9. Dynamic Content Note

Artist identity/genre are stable; album lists grow over time. Anchor on the
stable artist facts + the core albums + internal consistency with the captured
response. Never hardcode an exact album count.

## 10. Notes For Rationale

- When capping for DOM scraping, cite the Apple Music page fetch used as the
  data source instead of `itunes.apple.com/lookup`.
- When scoring CP3/CP4, compare the saved album list to the executor's own
  `entity=album` raw response.
- Guidance tags: `id_from_page_url`, `undocumented_lookup_service`,
  `entity_album_enumeration`, `stable_core_tolerant_tail`.
