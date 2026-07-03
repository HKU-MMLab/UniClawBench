# Hidden Evaluation Rule — Exploration v2 · NASA Images API (two-hop search → asset manifest → original)

## 1. Grading Philosophy

This is an **interface-discovery + multi-hop retrieval** task graded by
**outcome plus mechanism evidence**.

The executor must:

- discover the NASA Image Library API (`images-api.nasa.gov`) behind the
  `images.nasa.gov` gallery and use it (not scrape the gallery UI), and
- perform the **two-hop** flow: `search` → pick result → resolve that item's
  **asset manifest** (`collection.json`) to get the original/largest file URL →
  download it and verify it's a real image, with auditable evidence.

The difficulty is the second hop: the search response does **not** contain the
original file URL; the executor must follow each item's `href` (the asset
`collection.json`) to enumerate the actual image files and select the original.

Grading anchors on the mechanism + a **stable NASA id**; the gallery's search
ranking can shift, so the exact "top result" is handled tolerantly.

## 2. Task Contract

Start at `https://images.nasa.gov/`. Find the API; search "Pillars of
Creation"; report the chosen result's NASA id + title; resolve its asset
manifest to the original image URL; download and verify it's an image. Save
`nasa_pillars.json`, the downloaded image, and a `nasa_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Endpoint chain (this is the grading target)

- Hop 1 — search: `https://images-api.nasa.gov/search?q=pillars%20of%20creation&media_type=image`
  → `collection.items[]`, each with `data[0].nasa_id`, `data[0].title`, and an
  asset `href`.
- Hop 2 — asset manifest: the item's
  `https://images-assets.nasa.gov/image/<nasa_id>/collection.json` (the `href`
  from hop 1) → a list of concrete file URLs (`~orig.*`, `~large.*`, `~medium.*`,
  etc.). The **original** is typically the `~orig` (or largest) asset.

### 3.2 Stable anchor (target identity)

A canonical Hubble "Pillars of Creation" result returned by this API is:

- nasa_id **`GSFC_20171208_Archive_e000732`**, title `Pillars of Creation
  Revealed in 3-D`.

Other legitimately relevant Pillars-of-Creation results also appear (e.g.
`GSFC_20171208_Archive_e000842` "Hubble Goes High Def to Revisit the Iconic
'Pillars of Creation'"). **Any** result whose title clearly identifies the
Hubble/Eagle-Nebula "Pillars of Creation" image is acceptable as the chosen
item — the executor is not required to land on the exact nasa_id above, since
search ranking can change. A non-Pillars image (e.g. an unrelated nebula) is
**not** acceptable.

### 3.3 Original-asset + download verification

- The chosen original asset URL must come from the item's `collection.json`
  manifest (hop 2), and should be the original/largest variant (`~orig` or the
  largest available), not a thumbnail.
- The downloaded file must be a real image: content-type `image/*` (jpeg/png/tiff)
  and a non-trivial size (well over a thumbnail — e.g. ≥ ~100 KB; originals are
  typically multi-MB). A thumbnail-only download does not satisfy this.

## 4. Expected Artifacts

- `/tmp_workspace/results/nasa_pillars.json` — chosen nasa_id, title, the
  original asset URL, and the verified content-type/size.
- The downloaded original image under `/tmp_workspace/results/`.
- `/tmp_workspace/results/nasa_evidence/` — request URLs + raw JSON for the
  search call and the asset manifest call.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                  | Weight |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Hop 1 done via `images-api.nasa.gov/search` (not gallery UI scraping); a relevant "Pillars of Creation" Hubble item chosen (nasa_id + title saved).    | 0.25   |
| CP2 | Hop 2 done: the item's asset manifest (`collection.json`) was resolved to enumerate real file URLs, evidenced in `nasa_evidence/`.                      | 0.25   |
| CP3 | The chosen asset URL is the original/largest variant from the manifest (not a thumbnail).                                                               | 0.20   |
| CP4 | The image was downloaded and verified to be a real image: content-type `image/*` and non-trivial size.                                                 | 0.20   |
| CP5 | `nasa_evidence/` (search + manifest URLs and raw responses) makes the two-hop pull reproducible.                                                       | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the image/metadata was obtained by **scraping the
  images.nasa.gov gallery UI** or a third-party site instead of the API.
- **cap at `0.55`** if no `nasa_evidence/` is saved.
- **cap at `0.60`** if only the search hop was done and the asset manifest hop
  was skipped (no original file URL resolved from `collection.json`).
- **cap at `0.65`** if only a thumbnail/medium was downloaded when an `~orig`
  asset was available in the manifest.
- **cap at `0.40`** if the chosen item is not the Pillars of Creation image.

Do **not** cap or fail merely because:

- the chosen nasa_id differs from `GSFC_20171208_Archive_e000732`, as long as
  the item is clearly the Hubble Pillars of Creation image (ranking varies),
- the original is a `.tif`/`.png`/`.jpg` — any real image format is fine,
- the executor used `curl`/python/agent-browser for the calls.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4 satisfied, no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor found the search API but hasn't resolved the
asset manifest, downloaded only a thumbnail, or hasn't saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped the gallery,
chose a wrong (non-Pillars) image, or never resolved an original file URL.

## 8. Hidden Reference Assets

None shipped. Evaluate from `nasa_pillars.json`, the downloaded image,
`nasa_evidence/`, and the transcript.

## 9. Dynamic Content Note

Search ranking can change, so the exact top result is not fixed; the chosen
item's identity (Pillars of Creation) and the two-hop mechanism are what is
graded. NASA ids and asset manifests are stable once published.

## 10. Notes For Rationale

- When capping for skipped hop 2, note that the saved asset URL came from the
  search response/`href` directly rather than from a resolved `collection.json`.
- When scoring CP3/CP4, quote the chosen asset URL and the verified
  content-type + byte size.
- Guidance tags: `multi_hop_search_then_asset`, `original_not_thumbnail`,
  `download_and_verify_image`, `tolerant_top_result`.
