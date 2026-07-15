// Leaderboard page — pass rate / avg score across two dimensions.
//
// Layout: each row stacks a deep-color pass-rate bar over a soft-color
// avg-score bar, model name on the left, values on the right. Each row
// gets its own theme color, indexed by rank so the visual order matches
// the descending pass-rate sort.
//
// Scope control (ALL / EN / ZH): restricts every stat to a suite family —
// EN = 1xx suites, ZH = 2xx (_zh) suites, ALL = everything. When not ALL
// we re-aggregate client-side from data.rows so totals + per-category
// detail reflect only the chosen family.
//
// "Model" tab: click any row to expand per-category bars for that row only
// (per-row, lazily built). "Backend" tab adds ``?models=on``
// (per-(backend,model) rows), ``?coverage=all`` (common tasks) and
// ``?common=models``.
// Categories are derived from the live data, never hardcoded, so renamed
// suites and new ones appear automatically.

import { getJSON, invalidate } from "../lib/api.js";
import { h, clear } from "../lib/dom.js";
import { pct, score, categoryLabel, tokens, duration, displayModelName } from "../lib/format.js";
import { writeHash } from "../lib/router.js";
import { registerPageRefresh } from "../lib/refresh.js";
import { getTextOnlyTaskIds, isTextOnlyEnabled } from "../lib/text-only.js";

// ALL / EN / ZH scope: which suite family to include.
const SCOPES = [
  { id: "all", label: "ALL", match: () => true },
  { id: "en", label: "EN", match: (c) => (c || "").startsWith("1") },
  { id: "zh", label: "ZH", match: (c) => (c || "").startsWith("2") },
];

// Six-tone palette tuned to sit alongside the sage-green page theme.
const PALETTE = [
  ["#1f6f5f", "rgba(31,111,95,0.42)", "rgba(31,111,95,0.1)"],
  ["#b97a2c", "rgba(185,122,44,0.4)", "rgba(185,122,44,0.1)"],
  ["#2c6f8a", "rgba(44,111,138,0.4)", "rgba(44,111,138,0.1)"],
  ["#7a4f8a", "rgba(122,79,138,0.4)", "rgba(122,79,138,0.1)"],
  ["#a44a3f", "rgba(164,74,63,0.42)", "rgba(164,74,63,0.1)"],
  ["#4a6a52", "rgba(74,106,82,0.45)", "rgba(74,106,82,0.1)"],
];

let lastRoute = null;

// Static-export mode: when this page is served as a backend-free bundle
// from a static HTTP host, there is no /api/aggregate endpoint. The
// export_static.py CLI writes a slim compatible JSON file and sets
// ``window.CLAWBENCH_STATIC_DATA`` on the page. Read that file instead.
// Live-server behaviour is unchanged (this returns "/api/aggregate").
function aggregateUrl() {
  const staticFile =
    typeof window !== "undefined" &&
    window.CLAWBENCH_STATIC_DATA;
  return staticFile || "/api/aggregate";
}

export async function mount(root, route) {
  lastRoute = route;
  const dim = route.sub === "backend" ? "backend" : "model";
  const scope = SCOPES.some((s) => s.id === route.query.scope) ? route.query.scope : "all";
  const state = {
    dim,
    scope,
    textOnly: isTextOnlyEnabled(route.query),
    showModels: route.query.models === "on",
    // Common tasks + common models is the default selected comparison mode
    // for fair cross-harness comparisons.
    coverageAll: route.query.coverage !== "off",
    commonModels: route.query.common !== "off",
  };

  clear(root);
  const page = h("div.results-page", [
    h("div.results-header", [
      h("h2", "Leaderboard"),
      h("span.results-note", "Pass rate and checkpoint score by model and harness"),
    ]),
    buildControls(state),
    h("div.results-list#results-list", h("div.loading-stub", "Loading…")),
  ]);
  root.appendChild(page);

  const list = page.querySelector("#results-list");
  try {
    let data = prepareAggregate(await getJSON(aggregateUrl()));
    if (scope !== "all") data = applyScope(data, scope);
    if (state.textOnly) data = applyTaskSet(data, await getTextOnlyTaskIds());
    renderList(list, data, state);
  } catch (err) {
    clear(list);
    list.appendChild(h("div.error-stub", `Failed to load aggregate data: ${err.message || err}`));
  }
}

registerPageRefresh("leaderboard", async () => {
  const url = aggregateUrl();
  invalidate(url);
  // Static bundles have no server-side cache to bust; force a fresh HTTP
  // fetch so browser/CDN caches do not make the FAB look like a no-op.
  const isStatic = url !== "/api/aggregate";
  await getJSON(url, isStatic ? { refresh: true, noStore: true } : { refresh: true });
  if (lastRoute) await mount(document.getElementById("page-root"), lastRoute);
});

// ── Static-export row-label hydration ────────────────────────────────
// The static bundle (export_static.py) drops the per-row ``model_label`` —
// it is one of only ~10 distinct values yet was duplicated across every row
// (~330 KB / ~16% of results.json). Instead it ships a compact
// ``model_labels`` lookup ({ "backend::model_slug": model_label }). Backfill
// the rows from it so all downstream client re-aggregation (EN/ZH scope,
// Backend-tab filters) sees a label exactly as it did from the live
// /api/aggregate.
// Live mode is a no-op: rows already carry ``model_label`` and there is no
// ``model_labels`` map, so nothing is touched.
function hydrateRowLabels(data) {
  const labels = data && data.model_labels;
  if (!labels || !Array.isArray(data.rows)) return;
  for (const r of data.rows) {
    if (r && r.model_label == null && r.model_slug != null) {
      const scopedKey = `${r.backend || ""}::${r.model_slug}`;
      r.model_label = labels[scopedKey] ?? labels[r.model_slug] ?? r.model_slug;
    }
  }
}

// Static export ships a deliberately slim schema:
//   { schema, rows, model_labels, all_backends, task_count }
// Rebuild the live aggregate's derived arrays in-browser so the rest of the
  // Leaderboard page can stay shared with /api/aggregate.
function prepareAggregate(data) {
  if (!data || !Array.isArray(data.rows)) return data || {};
  hydrateRowLabels(data);
  data.categories = knownCategories(data);
  if (!Array.isArray(data.all_backends)) {
    data.all_backends = [...new Set(data.rows.map((r) => r.backend).filter(Boolean))].sort();
  }
  if (data.task_count == null) {
    data.task_count = data.task_backends
      ? Object.keys(data.task_backends).length
      : countTasks(data.rows);
  }
  if (!Array.isArray(data.models)) {
    data.models = aggregateClient(
      data.rows.filter((r) => r.backend === "openclaw"), "model_slug", "model_label", true,
      null,
      data.categories,
    );
  }
  if (!Array.isArray(data.backends)) {
    data.backends = aggregateClient(data.rows, "backend", "backend", false, null, data.categories);
  }
  if (!Array.isArray(data.model_backend_pairs)) {
    data.model_backend_pairs = aggregateClient(
      data.rows, "_pair_key", "model_label", true, (r) => `${r.backend}::${r.model_slug}`, data.categories,
    );
  }
  return data;
}

function knownCategories(data, rows = data?.rows || []) {
  if (Array.isArray(data?.categories) && data.categories.length) {
    return [...new Set(data.categories.filter(Boolean))].sort();
  }
  const categories = new Set();
  for (const groupName of ["models", "backends", "model_backend_pairs"]) {
    for (const entry of data?.[groupName] || []) {
      const by = entry?.byCategory || {};
      Object.keys(by).forEach((cat) => { if (cat) categories.add(cat); });
    }
  }
  for (const row of rows || []) {
    if (row.category) categories.add(row.category);
  }
  return [...categories].sort();
}

function countTasks(rows) {
  return new Set(
    (rows || [])
      .filter((r) => r.category && r.task_id)
      .map((r) => `${r.category}::${r.task_id}`),
  ).size;
}

// ── Re-aggregate over a suite family (EN/ZH) ─────────────────────────
function applyScope(data, scope) {
  const sc = SCOPES.find((s) => s.id === scope) || SCOPES[0];
  const rows = (data.rows || []).filter((r) => sc.match(r.category));
  const categories = knownCategories(data).filter((cat) => sc.match(cat));
  return reaggregateRows(data, rows, categories);
}

function applyTaskSet(data, taskIds) {
  const rows = (data.rows || []).filter((row) => taskIds.has(row.task_id));
  const categories = knownCategories(data).filter((cat) => rows.some((row) => row.category === cat));
  return reaggregateRows(data, rows, categories);
}

function reaggregateRows(data, rows, categories) {
  const allBackends = [...new Set(rows.map((r) => r.backend).filter(Boolean))].sort();
  return {
    ...data,
    rows,
    all_backends: allBackends,
    categories,
    task_count: countTasks(rows),
    // Model tab is openclaw-only (one row per model) — mirror the server's
    // ALL-scope ``models`` aggregate (aggregate.py restricts to openclaw rows).
    // Without this filter the EN/ZH re-aggregation summed all harnesses, so a
    // shared model showed a count LARGER in EN than in ALL — EN is a subset of
    // ALL, so that was wrong.
    models: aggregateClient(
      rows.filter((r) => r.backend === "openclaw"), "model_slug", "model_label", true, null, categories,
    ),
    backends: aggregateClient(rows, "backend", "backend", false, null, categories),
    model_backend_pairs: aggregateClient(
      rows, "_pair", "model_label", true, (r) => `${r.backend}::${r.model_slug}`, categories,
    ),
  };
}

function buildControls(state) {
  const { dim, scope, textOnly } = state;

  // Build a query object from the current state, applying overrides. This
  // makes every control carry the others (scope survives a mode change,
  // comparison mode survives a scope change, etc.).
  const queryFrom = (over = {}) => {
    const s = { ...state, ...over };
    const q = {};
    if (s.showModels) q.models = "on";
    if (!s.coverageAll) q.coverage = "off";
    if (!s.commonModels) q.common = "off";
    if (s.scope && s.scope !== "all") q.scope = s.scope;
    if (s.textOnly) q.text = "only";
    return q;
  };

  // Dimension tabs (Model / Backend). Switching clears comparison mode but
  // keeps scope.
  const tabs = h("div.results-tabs");
  for (const value of ["model", "backend"]) {
    const link = h("a.results-tab", {
      href: `#/leaderboard/${value}`,
      onclick: (event) => {
        event.preventDefault();
        writeHash({ page: "leaderboard", sub: value, query: queryFrom({ showModels: false, coverageAll: true, commonModels: true }) });
      },
    }, value === "model" ? "Model" : "Harness");
    if (value === dim) link.classList.add("active");
    tabs.appendChild(link);
  }

  // Scope tabs (ALL / EN / ZH). Preserves the current comparison mode.
  const scopeTabs = h("div.results-tabs.results-scope");
  for (const s of SCOPES) {
    const link = h("a.results-tab", {
      href: `#/leaderboard/${dim}`,
      onclick: (event) => {
        event.preventDefault();
        writeHash({ page: "leaderboard", sub: dim, query: queryFrom({ scope: s.id }) });
      },
    }, s.label);
    if (s.id === scope) link.classList.add("active");
    scopeTabs.appendChild(link);
  }

  const taskScopeTabs = h("div.results-tabs.results-task-scope", { role: "group", "aria-label": "Task capability scope" });
  for (const option of [
    { textOnly: false, label: "All tasks" },
    { textOnly: true, label: "Text-only" },
  ]) {
    const link = h("a.results-tab", {
      href: `#/leaderboard/${dim}`,
      onclick: (event) => {
        event.preventDefault();
        writeHash({ page: "leaderboard", sub: dim, query: queryFrom(option) });
      },
    }, option.label);
    if (option.textOnly === textOnly) link.classList.add("active");
    taskScopeTabs.appendChild(link);
  }

  // Per-category/detail expansion is per-card. Backend/Harness comparison
  // filters are mode buttons rather than on/off switches so the interaction
  // language stays aligned with the expandable metric cards.
  const modeWrap = h("div.results-modes-wrap");
  if (dim === "backend") {
    modeWrap.appendChild(buildComparisonModes(state, (next) => {
      writeHash({ page: "leaderboard", sub: dim, query: queryFrom(next) });
    }));
  }

  return h("div.results-controls", [tabs, scopeTabs, taskScopeTabs, modeWrap]);
}

function buildComparisonModes(state, onChange) {
  const modes = [
    { id: "all", label: "All rows", next: { coverageAll: false, commonModels: false } },
    { id: "tasks", label: "Common tasks", next: { coverageAll: true, commonModels: false } },
    { id: "models", label: "Common models", next: { coverageAll: false, commonModels: true } },
    { id: "tasks-models", label: "Common tasks + models", next: { coverageAll: true, commonModels: true } },
  ];
  const active = modes.find((mode) =>
    mode.next.coverageAll === state.coverageAll &&
    mode.next.commonModels === state.commonModels
  )?.id || "tasks-models";
  const wrap = h("div.results-mode-tabs", { role: "group", "aria-label": "Harness comparison scope" });
  for (const mode of modes) {
    const btn = h("button.results-mode-tab", { type: "button" }, mode.label);
    if (mode.id === active) btn.classList.add("active");
    btn.addEventListener("click", () => onChange(mode.next));
    wrap.appendChild(btn);
  }
  return wrap;
}

function renderList(list, data, state) {
  const { dim, showModels, coverageAll, commonModels } = state;
  clear(list);
  if (dim === "model") {
    const entries = sortEntries(data.models || []);
    if (!entries.length) {
      list.appendChild(h("div.results-empty", "No runs aggregated yet."));
      return;
    }
    entries.forEach((entry, idx) => {
      list.appendChild(buildModelRow(entry, idx, { indented: false }));
    });
    return;
  }
  // Backend tab.
  let backends = sortEntries(data.backends || []);
  let pairs = data.model_backend_pairs || [];
  const banners = [];

  if (coverageAll || commonModels) {
    const filtered = filterRows(data, { coverageAll, commonModels });
    backends = sortEntries(filtered.backends);
    pairs = filtered.pairs;
    const allBeN = (data.all_backends || []).length;
    if (coverageAll) {
      const totalTasks = Number.isFinite(Number(data.task_count))
        ? Number(data.task_count)
        : Object.keys(data.task_backends || {}).length;
      banners.push(h("div.results-coverage-banner",
        `Common tasks — ${filtered.taskCount}/${totalTasks} tasks present on all ${allBeN} harnesses.`));
    }
    if (commonModels) {
      banners.push(h("div.results-coverage-banner",
        `Common models — ${filtered.modelCount}/${filtered.totalModels} models present on all ${allBeN} harnesses.`));
    }
  }

  if (!backends.length) {
    list.appendChild(h("div.results-empty", "No runs aggregated yet."));
    return;
  }

  banners.forEach((b) => list.appendChild(b));

  const modelOrderRows = data.models || [];
  const sortedModelsForRank = sortEntries(modelOrderRows);
  const modelRank = new Map(sortedModelsForRank.map((m, i) => [m.key, i]));

  backends.forEach((entry, idx) => {
    list.appendChild(buildBackendRow(entry, idx, { pairs, modelRank, initiallyExpanded: showModels }));
  });
}

// ── Client-side filters (Backend tab) ────────────────────────────────
function filterRows(data, { coverageAll, commonModels }) {
  const allBackends = data.all_backends || [];
  let rows = data.rows || [];

  let allowedModels = null;
  let totalModels = 0;
  if (commonModels) {
    const modelBackends = new Map();
    for (const r of rows) {
      if (!modelBackends.has(r.model_slug)) modelBackends.set(r.model_slug, new Set());
      modelBackends.get(r.model_slug).add(r.backend);
    }
    totalModels = modelBackends.size;
    allowedModels = new Set();
    for (const [m, bs] of modelBackends.entries()) {
      if (allBackends.every((b) => bs.has(b))) allowedModels.add(m);
    }
    rows = rows.filter((r) => allowedModels.has(r.model_slug));
  }

  let allowedTasks = null;
  let totalTasks = 0;
  if (coverageAll) {
    const taskBackends = new Map();
    for (const r of rows) {
      const ck = `${r.category}::${r.task_id}`;
      if (!taskBackends.has(ck)) taskBackends.set(ck, new Set());
      taskBackends.get(ck).add(r.backend);
    }
    totalTasks = taskBackends.size;
    allowedTasks = new Set();
    for (const [t, bs] of taskBackends.entries()) {
      if (allBackends.every((b) => bs.has(b))) allowedTasks.add(t);
    }
    rows = rows.filter((r) => allowedTasks.has(`${r.category}::${r.task_id}`));
  }

  return {
    backends: aggregateClient(rows, "backend", "backend", false, null, data.categories),
    pairs: aggregateClient(rows, "_pair_key", "model_label", true, (r) => `${r.backend}::${r.model_slug}`, data.categories),
    taskCount: allowedTasks ? allowedTasks.size : totalTasks,
    modelCount: allowedModels ? allowedModels.size : totalModels,
    totalModels,
    totalTasks,
  };
}

function aggregateClient(rows, keyField, labelField, carryBackend, keyFn = null, categories = null) {
  const cats = Array.isArray(categories) && categories.length
    ? categories
    : [...new Set(rows.map((r) => r.category).filter(Boolean))].sort();
  const buckets = new Map();
  for (const row of rows) {
    const key = keyFn ? keyFn(row) : row[keyField];
    if (!buckets.has(key)) {
      const slot = { key, label: row[labelField], rows: [] };
      if (carryBackend) slot.backend = row.backend;
      buckets.set(key, slot);
    }
    buckets.get(key).rows.push(row);
  }
  const out = [];
  for (const slot of buckets.values()) {
    const slotRows = slot.rows;
    delete slot.rows;
    slot.total = summarizeClient(slotRows);
    slot.byCategory = {};
    for (const cat of cats) {
      slot.byCategory[cat] = summarizeClient(slotRows.filter((r) => r.category === cat));
    }
    out.push(slot);
  }
  return out;
}

function summarizeClient(rows) {
  if (!rows.length) {
    return {
      pass_rate: null, avg_score: null, n: 0,
      avg_input_tokens: null, avg_output_tokens: null, avg_runtime_ms: null,
    };
  }
  const n = rows.length;
  const mean = (f) => {
    const vs = rows.map((r) => r[f]).filter((v) => v != null);
    return vs.length ? vs.reduce((a, b) => a + b, 0) / vs.length : null;
  };
  return {
    pass_rate: rows.filter((r) => r.passed).length / n,
    avg_score: rows.reduce((s, r) => s + r.score, 0) / n,
    n,
    avg_input_tokens: mean("prompt_tokens"),
    avg_output_tokens: mean("completion_tokens"),
    avg_runtime_ms: mean("runtime_ms"),
  };
}

function sortEntries(entries) {
  return [...entries].sort((a, b) => {
    const pa = a.total?.pass_rate ?? -1;
    const pb = b.total?.pass_rate ?? -1;
    if (pb !== pa) return pb - pa;
    return (a.label || a.key).localeCompare(b.label || b.key);
  });
}

function applyTheme(node, idx) {
  const [base, soft, bg] = PALETTE[idx % PALETTE.length];
  node.style.setProperty("--row-base", base);
  node.style.setProperty("--row-soft", soft);
  node.style.setProperty("--row-bg", bg);
}

// Per-row expandable model row. Clicking the row (or its chevron) lazily
// appends/removes ``buildCategoryDetail(entry)`` for THAT row only — there is
// no global expand-all. Indented breakdown rows still show their own count.
function buildModelRow(entry, idx, { indented }) {
  const wrap = h(`div.metric-block.expandable${indented ? ".indented" : ""}`);
  applyTheme(wrap, idx);
  const metricRow = buildMetricRow({
    label: displayModelName(entry.label || entry.key),
    total: entry.total || {},
    metaParts: indented ? `n=${(entry.total || {}).n ?? 0}` : entryMeta(entry),
    expandable: true,
  });

  let detail = null;
  const toggle = () => {
    if (detail) {
      detail.remove();
      detail = null;
      wrap.classList.remove("expanded");
      metricRow.setAttribute("aria-expanded", "false");
    } else {
      detail = buildCategoryDetail(entry);
      wrap.appendChild(detail);
      wrap.classList.add("expanded");
      metricRow.setAttribute("aria-expanded", "true");
    }
  };

  metricRow.classList.add("clickable");
  metricRow.setAttribute("role", "button");
  metricRow.setAttribute("tabindex", "0");
  metricRow.setAttribute("aria-expanded", "false");
  metricRow.addEventListener("click", toggle);
  metricRow.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggle();
    }
  });

  wrap.appendChild(metricRow);
  return wrap;
}

function buildBackendRow(entry, idx, { pairs, modelRank, initiallyExpanded = false }) {
  const wrap = h("div.metric-block.expandable");
  applyTheme(wrap, idx);
  const metricRow = buildMetricRow({
    label: backendDisplayName(entry.label || entry.key),
    total: entry.total || {},
    metaParts: entryMeta(entry),
    expandable: true,
  });

  const buildChildren = () => {
    const myPairs = pairs.filter((p) => p.key.startsWith(entry.key + "::"));
    const sortedPairs = sortEntries(myPairs);
    const sub = h("div.results-children");
    sortedPairs.forEach((pair) => {
      const modelSlug = pair.key.split("::").slice(1).join("::");
      const themeIdx = modelRank.get(modelSlug) ?? 0;
      sub.appendChild(buildModelRow(pair, themeIdx, { indented: true }));
    });
    if (!sortedPairs.length) {
      sub.appendChild(h("div.results-empty-child", "No model rows in this comparison scope."));
    }
    return sub;
  };

  let detail = null;
  const toggle = () => {
    if (detail) {
      detail.remove();
      detail = null;
      wrap.classList.remove("expanded");
      metricRow.setAttribute("aria-expanded", "false");
    } else {
      detail = buildChildren();
      wrap.appendChild(detail);
      wrap.classList.add("expanded");
      metricRow.setAttribute("aria-expanded", "true");
    }
  };

  metricRow.classList.add("clickable");
  metricRow.setAttribute("role", "button");
  metricRow.setAttribute("tabindex", "0");
  metricRow.setAttribute("aria-expanded", "false");
  metricRow.addEventListener("click", toggle);
  metricRow.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggle();
    }
  });

  wrap.appendChild(metricRow);
  if (initiallyExpanded) toggle();
  return wrap;
}

function buildMetricRow({ label, total, metaParts, expandable = false }) {
  const passRate = total.pass_rate;
  const avgScore = total.avg_score;
  const avgIn = total.avg_input_tokens;
  const avgOut = total.avg_output_tokens;
  const avgRt = total.avg_runtime_ms;
  const row = h("div.metric-row", [
    h("div.metric-label", label),
    h("div.metric-bars", [
      bar(passRate, "pass"),
      bar(avgScore, "score"),
    ]),
    h("div.metric-values", [
      h("div.metric-value.pass", passRate == null ? "—" : pct(passRate, { digits: 0 })),
      h("div.metric-value.score", avgScore == null ? "—" : score(avgScore, { digits: 2 })),
    ]),
    h("div.metric-averages", [
      `avg ${tokens(avgIn)} in · ${tokens(avgOut)} out · ${duration(avgRt)}`,
    ]),
  ]);
  if (expandable) {
    row.appendChild(h("span.metric-chevron", { "aria-hidden": "true" }, "▸"));
  }
  if (metaParts) {
    row.appendChild(h("div.metric-meta", metaParts));
  }
  return row;
}

function bar(value, kind) {
  const fill = h(`div.metric-bar-fill.${kind}`);
  if (value == null) {
    fill.classList.add("empty");
    fill.style.width = "0%";
  } else {
    const clamped = Math.max(0, Math.min(1, value));
    fill.style.width = (clamped * 100).toFixed(1) + "%";
  }
  return h(`div.metric-bar.${kind}`, fill);
}

function buildCategoryDetail(entry) {
  const wrap = h("div.metric-detail");
  const by = entry.byCategory || {};
  for (const cat of Object.keys(by).sort()) {
    const stats = by[cat] || {
      pass_rate: null, avg_score: null, n: 0,
      avg_input_tokens: null, avg_output_tokens: null, avg_runtime_ms: null,
    };
    const row = h("div.metric-row.metric-row-cat", [
      h("div.metric-label", `${cat.slice(0, 3)} ${categoryLabel(cat)}`),
      h("div.metric-bars", [
        bar(stats.pass_rate, "pass"),
        bar(stats.avg_score, "score"),
      ]),
      h("div.metric-values", [
        h("div.metric-value.pass", stats.pass_rate == null ? "—" : pct(stats.pass_rate, { digits: 0 })),
        h("div.metric-value.score", stats.avg_score == null ? "—" : score(stats.avg_score, { digits: 2 })),
      ]),
      h("div.metric-averages",
        `avg ${tokens(stats.avg_input_tokens)} in · ${tokens(stats.avg_output_tokens)} out · ${duration(stats.avg_runtime_ms)}`,
      ),
      h("div.metric-meta", `n=${stats.n}`),
    ]);
    if (!stats.n) row.classList.add("empty");
    wrap.appendChild(row);
  }
  return wrap;
}

function entryMeta(entry) {
  const total = entry.total || {};
  const parts = [`n=${total.n ?? 0}`];
  if (entry.backend) parts.push(entry.backend);
  return parts.join(" · ");
}

function backendDisplayName(label) {
  return (label || "").toUpperCase();
}
