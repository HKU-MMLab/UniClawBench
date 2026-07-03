import { renderMarkdown as renderMarkdownRich } from "../../lib/markdown.js";
import { canPreview as canPreviewTextFile } from "../../lib/file-preview.js";
import { displayModelName } from "../../lib/format.js";

// DOM references are bound lazily by ``bindDom()`` (called from
// ``bootTrace``) because the trace layout is now injected by
// ``pages/trace/index.js`` after the page mounts. Top-level lookups
// would race the layout creation and bind to null.
let runList;
let summaryEl;
let timelineEl;
let execTimelinePanelEl;
let execTimelineBodyEl;
let execTimelineToggleEl;
let outputsEl;
let checkpointsEl;
let gradingPanelEl;
let gradingTitleEl;
let gradingNoteEl;
// Lightbox refs unused here — lib/lightbox.js owns the click and
// escape handlers globally. Keep references nullable for any legacy
// code path that still touches them.
let lightboxEl;
let lightboxImageEl;
let lightboxCaptionEl;
let lightboxCloseEl;
let lightboxBackdropEl;
let flowFilterEls = [];
let attemptSelectWrapEl;
let attemptSelectEl;
let flowShowToolsEl;
let filterBackendEl;
let filterModelEl;
let filterStatusEl;
let filterCategoryEl;
let filterTaskEl;
let refreshFabEl;

function bindDom() {
  runList = document.getElementById("run-list");
  summaryEl = document.getElementById("summary");
  timelineEl = document.getElementById("timeline");
  execTimelinePanelEl = document.getElementById("exec-timeline-panel");
  execTimelineBodyEl = execTimelinePanelEl?.querySelector(".exec-timeline-body") || null;
  execTimelineToggleEl = execTimelinePanelEl?.querySelector(".exec-timeline-toggle") || null;
  outputsEl = document.getElementById("outputs");
  checkpointsEl = document.getElementById("checkpoints");
  gradingPanelEl = document.getElementById("grading-panel");
  gradingTitleEl = document.getElementById("grading-title");
  gradingNoteEl = document.getElementById("grading-note");
  lightboxEl = document.getElementById("image-lightbox");
  lightboxImageEl = document.getElementById("lightbox-image");
  lightboxCaptionEl = document.getElementById("lightbox-caption");
  lightboxCloseEl = document.getElementById("lightbox-close");
  lightboxBackdropEl = document.getElementById("lightbox-backdrop");
  flowFilterEls = [...document.querySelectorAll("[data-flow-filter]")];
  attemptSelectWrapEl = document.getElementById("attempt-select-wrap");
  attemptSelectEl = document.getElementById("attempt-select");
  flowShowToolsEl = document.getElementById("flow-show-tools");
  filterBackendEl = document.getElementById("filter-backend");
  filterModelEl = document.getElementById("filter-model");
  filterStatusEl = document.getElementById("filter-status");
  filterCategoryEl = document.getElementById("filter-category");
  filterTaskEl = document.getElementById("filter-task");
  refreshFabEl = document.getElementById("refresh-fab");
}

// Hash format under the new shell: ``#/trace/<encoded-rel-path>``.
// ``hashToPath`` strips the page prefix so the legacy code keeps
// reading just ``<rel-path>`` (the path under runs/).
function hashToPath() {
  try {
    const raw = (location.hash || "").replace(/^#/, "");
    const stripped = raw.replace(/^\/?trace\/?/, "");
    return decodeURIComponent(stripped);
  } catch (err) {
    return "";
  }
}

function writeHashForPath(relPath) {
  if (!relPath) return;
  const desired = "#/trace/" + encodeURIComponent(relPath);
  if (location.hash === desired) return;
  try {
    history.replaceState({}, "", desired);
  } catch (err) {
    location.hash = desired;
  }
}

let allRuns = [];
let activePath = hashToPath();
let activePayload = null;
let activeRunCard = null;
let flowFilter = "all";
let showToolDetails = false;

const FILTER_STORAGE_KEY = "clawbench.filters.v1";

function staticUrl(name) {
  if (typeof window === "undefined") return "";
  return typeof window[name] === "string" ? window[name] : "";
}

function runsIndexUrl({ refresh = false } = {}) {
  const staticRuns = staticUrl("CLAWBENCH_STATIC_RUNS");
  if (staticRuns) {
    return refresh
      ? staticRuns + (staticRuns.includes("?") ? "&" : "?") + "_=" + Date.now()
      : staticRuns;
  }
  return refresh ? "/api/runs?slim=1&refresh=1" : "/api/runs?slim=1";
}

function unpackRunsIndex(payload) {
  const runs = Array.isArray(payload?.runs) ? payload.runs : [];
  if (!Array.isArray(payload?.fields)) return runs;
  const fields = payload.fields.map((field) => String(field || ""));
  return runs.map((row) => {
    if (!Array.isArray(row)) return row || {};
    const item = {};
    fields.forEach((field, index) => {
      if (field) item[field] = row[index];
    });
    item.modelDisplay = displayModelName(item.model || item.modelSlug || "");
    return item;
  });
}

function staticAttemptUrl(relPath) {
  const base = staticUrl("CLAWBENCH_STATIC_ATTEMPTS_BASE");
  if (!base || !relPath) return "";
  const encoded = String(relPath)
    .split("/")
    .filter(Boolean)
    .map((part) => encodeURIComponent(part))
    .join("/");
  return `${base.replace(/\/+$/, "")}/${encoded}.json`;
}

function attemptUrl(relPath) {
  return staticAttemptUrl(relPath) || `/api/attempt?path=${encodeURIComponent(relPath)}`;
}

function parentRunPath(relPath) {
  const parts = String(relPath || "").split("/").filter(Boolean);
  if (parts.length >= 4 && parts[0] === "r" && parts[2] === "a") {
    return parts.slice(0, 2).join("/");
  }
  if (parts.length >= 5 && /^p\d+-/.test(parts[parts.length - 1])) {
    return parts.slice(0, -1).join("/");
  }
  return String(relPath || "");
}

function backendFromRelPath(relPath) {
  if (!relPath) return "";
  const parts = String(relPath).split("/").filter(Boolean);
  if (parts[0] === "r") return "";
  // Accepts either "runs/<backend>/..." or "<backend>/..." layouts.
  if (parts.length >= 2 && parts[0] === "runs") return parts[1];
  if (parts.length >= 1) return parts[0];
  return "";
}

function runForRelPath(runs, relPath) {
  if (!relPath) return null;
  const target = String(relPath);
  const targetRun = parentRunPath(target);
  return (runs || []).find((run) => {
    const summary = String(run?.summaryPath || "");
    const selected = String(run?.selectedAttemptPath || "");
    return summary === target
      || summary === targetRun
      || selected === target
      || parentRunPath(selected) === targetRun;
  }) || null;
}

function applyFiltersForPath(runs, relPath) {
  const run = runForRelPath(runs, relPath);
  if (!run || !filterBackendEl || !filterModelEl) return false;
  if (run.backend && [...filterBackendEl.options].some((option) => option.value === run.backend)) {
    filterBackendEl.value = run.backend;
  }
  if (filterStatusEl) filterStatusEl.value = "all";
  if (filterCategoryEl) filterCategoryEl.value = "all";
  if (filterTaskEl) filterTaskEl.value = "";
  syncModelOptions();
  const model = modelFilterValue(run);
  if (model && [...filterModelEl.options].some((option) => option.value === model)) {
    filterModelEl.value = model;
  }
  return true;
}

function loadStoredFilters() {
  try {
    const raw = sessionStorage.getItem(FILTER_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed ? parsed : {};
  } catch (err) {
    return {};
  }
}

function saveStoredFilters() {
  try {
    sessionStorage.setItem(
      FILTER_STORAGE_KEY,
      JSON.stringify({
        backend: filterBackendEl?.value || "all",
        model: filterModelEl?.value || "all",
        status: filterStatusEl?.value || "all",
        category: filterCategoryEl?.value || "all",
        task: filterTaskEl?.value || "",
      }),
    );
  } catch (err) {
    /* sessionStorage may be disabled; fall through silently */
  }
}
const BACKEND_ORDER = ["openclaw", "openclaw_edict", "nanobot"];
const EDICT_AGENT_ORDER = ["taizi", "zhongshu", "menxia", "shangshu", "libu", "hubu", "bingbu", "xingbu", "gongbu", "libu_hr", "zaochao"];
const EDICT_AGENT_META = {
  taizi: { label: "Crown Prince", emoji: "🤴", role: "Coordinator" },
  zhongshu: { label: "Central Secretariat", emoji: "📜", role: "Planning" },
  menxia: { label: "Chancellery", emoji: "🔍", role: "Review" },
  shangshu: { label: "State Affairs", emoji: "📮", role: "Dispatch" },
  libu: { label: "Rites Office", emoji: "📝", role: "Docs/UI" },
  hubu: { label: "Revenue Office", emoji: "💰", role: "Data" },
  bingbu: { label: "War Office", emoji: "⚔️", role: "Engineering" },
  xingbu: { label: "Justice Office", emoji: "⚖️", role: "Test/Audit" },
  gongbu: { label: "Works Office", emoji: "🔧", role: "Operations" },
  libu_hr: { label: "Personnel Office", emoji: "👔", role: "Training" },
  zaochao: { label: "Bulletin Office", emoji: "📰", role: "Reports" },
};

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(text) {
  return escapeHtml(text).replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function shortText(text, max = 220) {
  const clean = String(text || "").trim().replace(/\s+/g, " ");
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function mediaDataUrl(data, mimeType = "image/jpeg") {
  const value = String(data || "").trim();
  if (!value) return "";
  if (value.startsWith("data:")) return value;
  return `data:${mimeType};base64,${value}`;
}

function imagePreviewMarkup(src, caption, className = "") {
  const safeSrc = escapeAttr(src);
  return `
    <figure class="flow-image ${escapeAttr(className)}">
      <button type="button" class="image-preview-trigger flow-image-trigger" data-preview-caption="${escapeAttr(caption || "")}">
        <img src="${safeSrc}" alt="${escapeAttr(caption || "image")}" />
      </button>
      ${caption ? `<figcaption>${escapeHtml(caption)}</figcaption>` : ""}
    </figure>
  `;
}

function openImageLightbox(src, caption = "") {
  if (!src) return;
  lightboxImageEl.src = src;
  lightboxImageEl.alt = caption || "image preview";
  lightboxCaptionEl.textContent = caption || "";
  lightboxEl.classList.remove("hidden");
  lightboxEl.setAttribute("aria-hidden", "false");
}

function closeImageLightbox() {
  lightboxEl.classList.add("hidden");
  lightboxEl.setAttribute("aria-hidden", "true");
  lightboxImageEl.src = "";
  lightboxImageEl.alt = "";
  lightboxCaptionEl.textContent = "";
}

function formatScore(value) {
  return typeof value === "number" ? value.toFixed(2) : "n/a";
}

function formatRuntime(value) {
  return typeof value === "number" ? `${(value / 1000).toFixed(1)}s` : "n/a";
}

function formatDuration(value) {
  if (typeof value !== "number" || Number.isNaN(value) || value < 0) return "n/a";
  const totalSeconds = Math.round(value / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function formatTokens(value) {
  return typeof value === "number" ? value.toLocaleString() : "n/a";
}

function badge(label, tone = "neutral") {
  return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
}

function agentMeta(agentId) {
  if (!agentId) return null;
  const meta = EDICT_AGENT_META[agentId] || {};
  return {
    id: agentId,
    label: meta.label || agentId,
    emoji: meta.emoji || "🧩",
    role: meta.role || "",
  };
}

function agentLabel(agentId) {
  const meta = agentMeta(agentId);
  return meta ? `${meta.emoji} ${meta.label}` : "";
}

function parseAgentSessionTarget(sessionKey) {
  const value = String(sessionKey || "").trim();
  if (!value) return "";
  if (value.startsWith("agent:")) {
    const parts = value.split(":");
    if (parts.length >= 2) return parts[1] || "";
  }
  return value;
}

function primaryAgentId(detail, payload) {
  const manifest = detail?.agentSessionManifest || payload?.agentSessionManifest || {};
  if (manifest?.primaryAgentId) return manifest.primaryAgentId;
  const backend = detail?.meta?.backend || payload?.backend || "";
  if (backend === "openclaw_edict") return "taizi";
  if (backend === "openclaw") return "main";
  if (backend === "nanobot") return "nanobot";
  return "";
}

function statusTone(status) {
  if (status === "pass") return "ok";
  if (status === "running") return "neutral";
  // rate_limit (429 from upstream provider) and budget_exhausted (model
  // burned its allotted budget) are both quota/throttle issues — amber.
  if (status === "rate_limit") return "warn";
  if (status === "budget_exhausted") return "warn";
  // Real model failures (red): didn't finish task within available means.
  if (status === "stopped") return "bad";
  if (status === "executor_incomplete") return "bad";
  if (status === "global_timeout") return "bad";
  if (status === "fail") return "bad";
  // Infra-side breakage (purple): sandbox/container/setup broke before
  // the model could legitimately try — distinct from model fails (red)
  // and quota issues (amber).
  if (status === "infra_error") return "purple";
  if (status === "pre_exec_failed") return "purple";
  return "neutral";
}

function statusLabel(status) {
  if (status === "pass") return "PASS";
  if (status === "running") return "RUNNING";
  if (status === "infra_error") return "INFRA_ERROR";
  if (status === "rate_limit") return "RATE_LIMIT";
  if (status === "budget_exhausted") return "BUDGET_EXHAUSTED";
  if (status === "stopped") return "STOPPED";
  if (status === "executor_incomplete") return "EXECUTOR_INCOMPLETE";
  if (status === "global_timeout") return "GLOBAL_TIMEOUT";
  if (status === "pre_exec_failed") return "PRE_EXEC_FAILED";
  if (status === "fail") return "FAIL";
  return "UNKNOWN";
}

function verdictLabel(verdict) {
  if (verdict === "pass") return "PASS";
  if (verdict === "continue") return "CONTINUE";
  if (verdict === "infra_error") return "INFRA_ERROR";
  if (verdict === "rate_limit") return "RATE_LIMIT";
  if (verdict === "fail") return "FAIL";
  return "UNKNOWN";
}

function stageLabel(item) {
  return item.stageId || (item?.attempt ? `p${item.attempt}` : "primary");
}

function taskSortKey(taskId) {
  const match = /task_(\d+)/.exec(taskId || "");
  return [match ? Number(match[1]) : 1e9, taskId || ""];
}

function displayTaskLabel(taskId, maxLength = 28) {
  const raw = String(taskId || "task").trim();
  const match = /^task_(\d+)(?:_(.*))?$/.exec(raw);
  const compact = match
    ? `task${match[1]}${match[2] ? `_${match[2]}` : ""}`
    : raw;
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength - 1)}…`;
}

function categoryShortLabel(category) {
  const raw = String(category || "").trim();
  if (!raw) return "CAT";
  const match = /^(\d+)_?(.*)$/.exec(raw);
  const prefix = match ? match[1] : "";
  const words = (match ? match[2] : raw)
    .split(/[_\s-]+/)
    .filter(Boolean);
  const abbrev = words.length
    ? words.map((word) => word[0]).join("").slice(0, 3).toUpperCase()
    : raw.slice(0, 3).toUpperCase();
  return [prefix, abbrev].filter(Boolean).join(" ");
}

function categoryLongLabel(category) {
  const raw = String(category || "").trim();
  if (!raw) return "Uncategorized";
  const match = /^(\d+)_?(.*)$/.exec(raw);
  const words = (match ? match[2] : raw)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return [match ? match[1] : "", words].filter(Boolean).join(" · ");
}

function compareTaskIds(a, b) {
  const [na, sa] = taskSortKey(a);
  const [nb, sb] = taskSortKey(b);
  if (na !== nb) return na - nb;
  return sa.localeCompare(sb);
}

// Per-attempt wall-clock, with fallbacks. The summary's per-attempt
// ``runtimeMs`` is frequently null (the worker often never wrote it), which
// made the Runtime pill read "0s". Recover the elapsed time the same way the
// Results aggregate does (webui/aggregate.py:_extract_stats): prefer the
// summary value, else the attempt's ``meta.runtimeMs`` (executor wall-clock),
// else the attempt timeline's ``attempt_ended_ms − attempt_started_ms``.
function attemptRuntimeMs(summaryAttempt, detail) {
  const fromSummary = Number(summaryAttempt?.runtimeMs);
  if (Number.isFinite(fromSummary) && fromSummary > 0) return fromSummary;
  const fromMeta = Number(detail?.meta?.runtimeMs);
  if (Number.isFinite(fromMeta) && fromMeta > 0) return fromMeta;
  const tl = detail?.timeline;
  if (tl && typeof tl === "object") {
    const start = Number(tl.attempt_started_ms);
    const end = Number(tl.attempt_ended_ms);
    if (Number.isFinite(start) && Number.isFinite(end) && end >= start) return end - start;
  }
  return 0;
}

function runMetrics(payload) {
  const taskSummary = payload.taskSummary || {};
  const attempts = Array.isArray(taskSummary.attempts) ? taskSummary.attempts : [];
  // Map each summary attempt to its matching attemptDetails entry (by attempt
  // number) so the runtime fallbacks below can read meta/timeline.
  const detailByAttempt = new Map(
    (payload.attemptDetails || [])
      .filter((d) => d && d.attempt != null)
      .map((d) => [Number(d.attempt), d]),
  );
  const attemptScores = (payload.attemptDetails || [])
    .map((detail) => detail?.score?.final_completion_score ?? detail?.score?.capped_score ?? detail?.score?.overall_score)
    .filter((value) => typeof value === "number");
  const attemptSupervisorScores = (payload.attemptDetails || [])
    .map((detail) => detail?.score?.overall_score)
    .filter((value) => typeof value === "number");
  const summaryScores = attempts
    .map((item) => item?.score)
    .filter((value) => typeof value === "number");
  const allScores = [...attemptScores, ...summaryScores];
  const totalRuntime = attempts.length
    ? attempts.reduce(
        (sum, item) => sum + attemptRuntimeMs(item, detailByAttempt.get(Number(item?.attempt))),
        0,
      )
    : Number(payload.meta?.runtimeMs || 0);
  const usage = payload.usageSummary || {};
  // Round 9 / B4: surface EDICT upstream-revision metadata for the
  // header badge.  Prefer the per-task summary block (written by
  // lib.runner.orchestration.task_summary_base) and fall back to the
  // agent_sessions_manifest fields that lib.runner.artifacts emits.
  const manifest = payload?.agentSessionManifest || {};
  const edictBlock = taskSummary.edict || (
    (manifest.edictMode || manifest.edictCommit || manifest.edictVersion)
      ? {
          mode: manifest.edictMode || "",
          commit: manifest.edictCommit || "",
          version: manifest.edictVersion || "",
        }
      : null
  );
  return {
    finalStatus: taskSummary.finalStatus || "fail",
    finalScore: taskSummary.finalScore ?? payload.score?.final_completion_score ?? payload.score?.capped_score ?? payload.score?.overall_score ?? null,
    rawSupervisorScore: taskSummary.rawFinalScore ?? payload.score?.overall_score ?? null,
    stopReason: taskSummary.stopReason || "",
    maxScore: allScores.length ? Math.max(...allScores) : null,
    maxSupervisorScore: attemptSupervisorScores.length ? Math.max(...attemptSupervisorScores) : null,
    runtimeMs: totalRuntime,
    backend: payload.backend || "unknown",
    model: displayModelName(payload.meta?.model || taskSummary.model || payload.meta?.modelSlug || taskSummary.modelSlug || "unknown"),
    supervisorModel: displayModelName(payload.supervision?.supervisor?.model || payload.meta?.supervision?.supervisor?.model || "n/a"),
    userSimulatorModel: displayModelName(payload.supervision?.userSimulator?.model || payload.meta?.supervision?.userSimulator?.model || "n/a"),
    supervisionCycles: payload.usageSummary?.supervisionCalls ?? payload.supervisionTrace?.length ?? 0,
    continuations: payload.continuationCount || 0,
    executorUsageAvailable: Boolean(usage.executorUsageAvailable),
    executorInputTokens: typeof usage.executorInputTokens === "number" ? usage.executorInputTokens : null,
    executorOutputTokens: typeof usage.executorOutputTokens === "number" ? usage.executorOutputTokens : null,
    executorTotalTokens: typeof usage.executorTotalTokens === "number" ? usage.executorTotalTokens : null,
    executorCallCount: typeof usage.executorCallCount === "number" ? usage.executorCallCount : null,
    edict: edictBlock,
  };
}

// Round 9 / B4: render the EDICT upstream-revision badge.  Short
// commit + version go on the same pill so the header stays compact.
function edictBadgeHtml(edict) {
  if (!edict || !edict.commit) return "";
  const short = String(edict.commit).slice(0, 12);
  const versionLabel = edict.version ? ` ｜ ${edict.version}` : "";
  const modeLabel = edict.mode || "official_specs_local_adapter";
  return `<span class="summary-pill emphasis edict-badge" title="EDICT adapter mode = ${escapeAttr(modeLabel)} ; upstream commit = ${escapeAttr(edict.commit)}">EDICT ${escapeHtml(short)}${escapeHtml(versionLabel)}</span>`;
}

function filteredMetrics(rows) {
  const scores = rows.map((item) => item.finalScore).filter((value) => typeof value === "number");
  const runtimes = rows.map((item) => item.runtimeMs).filter((value) => typeof value === "number");
  const continuations = rows.map((item) => item.continuationCount || 0);
  return {
    avgScore: scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : null,
    avgRuntime: runtimes.length ? runtimes.reduce((sum, value) => sum + value, 0) / runtimes.length : null,
    avgContinuation: continuations.length ? continuations.reduce((sum, value) => sum + value, 0) / continuations.length : null,
  };
}

function cardHtml(run) {
  const fullTaskId = run.taskId || "task";
  const taskLabel = displayTaskLabel(fullTaskId);
  const catLabel = categoryShortLabel(run.category);
  const title = `${categoryLongLabel(run.category)} · ${fullTaskId}`;
  return `
    <button class="run-card" data-path="${escapeHtml(run.summaryPath || "")}" title="${escapeAttr(title)}">
      <div class="run-top simple">
        <strong class="run-card-title"><span class="run-cat-prefix">${escapeHtml(catLabel)}</span>${escapeHtml(taskLabel)}</strong>
        ${badge(statusLabel(run.finalStatus), statusTone(run.finalStatus))}
      </div>
    </button>
  `;
}

function setOptions(selectEl, values, labelFn = (value) => value) {
  if (!selectEl) return;
  const current = selectEl.value;
  const options = ['<option value="all">All</option>']
    .concat(values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(labelFn(value))}</option>`));
  selectEl.innerHTML = options.join("");
  if (values.includes(current)) {
    selectEl.value = current;
  }
}

function availableModelsForBackend(backend) {
  return [...new Set(
    allRuns
      .filter((run) => backend === "all" || run.backend === backend)
      .map((run) => modelFilterValue(run))
      .filter(Boolean),
  )].sort();
}

function modelFilterValue(run) {
  return run?.modelDisplay || displayModelName(run?.model || run?.modelSlug || "");
}

function syncModelOptions() {
  const backend = filterBackendEl.value || "all";
  const current = filterModelEl.value;
  const values = availableModelsForBackend(backend);
  setOptions(filterModelEl, values);
  if (current && (current === "all" || values.includes(current))) {
    filterModelEl.value = current;
  } else if (values.length) {
    filterModelEl.value = values[0];
  }
}

function initFilters(runs) {
  const backends = [...new Set(runs.map((run) => run.backend).filter(Boolean))]
    .sort((a, b) => {
      const ia = BACKEND_ORDER.indexOf(a);
      const ib = BACKEND_ORDER.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
  setOptions(filterBackendEl, backends);
  const categories = [...new Set(runs.map((run) => run.category).filter(Boolean))]
    .sort((a, b) => {
      const [na, sa] = taskSortKey(a.replace(/^(\d+)_/, "task_$1_"));
      const [nb, sb] = taskSortKey(b.replace(/^(\d+)_/, "task_$1_"));
      if (na !== nb) return na - nb;
      return sa.localeCompare(sb);
    });
  setOptions(filterCategoryEl, categories, (value) => `${categoryShortLabel(value)} · ${categoryLongLabel(value)}`);
  const stored = loadStoredFilters();
  if (backends.length) {
    // Resolve an initial backend with three fallbacks, favouring whatever
    // the user had active when the page was reloaded:
    //   1. backend implied by the current activePath (URL hash)
    //   2. backend remembered in sessionStorage from the previous session
    //   3. first backend in the preferred order
    const pathRun = runForRelPath(runs, activePath);
    const activeBackend = pathRun?.backend || backendFromRelPath(activePath);
    const preferred = [activeBackend, stored.backend].find(
      (candidate) => candidate && backends.includes(candidate),
    );
    filterBackendEl.value = preferred || backends[0];
    // Restore the other filters from sessionStorage when possible. Model
    // options depend on the selected backend, so apply after backend is set.
    if (stored.status) filterStatusEl.value = stored.status;
    if (stored.category && filterCategoryEl && [...filterCategoryEl.options].some((o) => o.value === stored.category)) {
      filterCategoryEl.value = stored.category;
    }
    if (stored.task) filterTaskEl.value = stored.task;
  }
  syncModelOptions();
  const pathRun = runForRelPath(runs, activePath);
  const pathModel = pathRun ? modelFilterValue(pathRun) : "";
  if (pathRun) {
    if (filterStatusEl) filterStatusEl.value = "all";
    if (filterCategoryEl) filterCategoryEl.value = "all";
    if (filterTaskEl) filterTaskEl.value = "";
  }
  if (pathModel && [...filterModelEl.options].some((o) => o.value === pathModel)) {
    filterModelEl.value = pathModel;
  } else if (stored.model && [...filterModelEl.options].some((o) => o.value === stored.model)) {
    filterModelEl.value = stored.model;
  }
  const persistAndRender = () => {
    saveStoredFilters();
    renderRunList();
  };
  filterBackendEl.addEventListener("change", () => {
    syncModelOptions();
    persistAndRender();
  });
  [filterModelEl, filterStatusEl, filterCategoryEl].filter(Boolean).forEach((el) => el.addEventListener("change", persistAndRender));
  filterTaskEl?.addEventListener("input", persistAndRender);
}

function filteredRuns() {
  const backend = filterBackendEl.value || "all";
  const model = filterModelEl.value || "all";
  const status = filterStatusEl.value || "all";
  const category = filterCategoryEl?.value || "all";
  const search = (filterTaskEl.value || "").trim().toLowerCase();
  return allRuns
    .filter((run) => {
      if (backend !== "all" && run.backend !== backend) return false;
      if (model !== "all" && modelFilterValue(run) !== model) return false;
      if (status !== "all" && run.finalStatus !== status) return false;
      if (category !== "all" && run.category !== category) return false;
      if (search) {
        const hay = `${run.taskId || ""} ${run.category || ""} ${run.backend || ""} ${modelFilterValue(run) || ""}`.toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    })
    .sort((a, b) => {
      const byCat = String(a.category || "").localeCompare(String(b.category || ""));
      if (byCat) return byCat;
      return compareTaskIds(a.taskId, b.taskId);
    });
}

function renderRunList() {
  const rows = filteredRuns();
  if (!rows.length) {
    runList.innerHTML = `<div class="empty">No tasks match the current filters.</div>`;
    summaryEl.innerHTML = `
      <div class="hero-copy">
        <div class="eyebrow">Attempt Review</div>
        <h2>No matching tasks</h2>
        <p>Adjust backend, model, category, status, or task search to load a task.</p>
      </div>
      <div class="quick-stats"></div>
    `;
    timelineEl.innerHTML = `<div class="empty">No flow available.</div>`;
    checkpointsEl.innerHTML = `<div class="empty">No supervisor details.</div>`;
    outputsEl.innerHTML = `<div class="empty">No saved results.</div>`;
    return;
  }
  runList.innerHTML = rows.map(cardHtml).join("");
  document.querySelectorAll(".run-card").forEach((card) => {
    card.addEventListener("click", () => loadAttempt(card.dataset.path, card));
  });
  const activeRunPath = parentRunPath(activePath);
  let activeCard = [...document.querySelectorAll(".run-card")].find((card) => card.dataset.path === activeRunPath || card.dataset.path === activePath);
  if (!activeCard) activeCard = document.querySelector(".run-card");
  if (activeCard) loadAttempt(activePath && activeCard.dataset.path === activeRunPath ? activePath : activeCard.dataset.path, activeCard);
}

function renderSummary(payload, rows) {
  const taskId = payload.meta?.taskId || payload.relPath || "run";
  const category = payload.taskSummary?.category || payload.meta?.category || (payload.relPath || "").split("/")[2] || "";
  const fullTaskLabel = `${categoryShortLabel(category)} · ${taskId}`;
  const metrics = runMetrics(payload);
  const settingMetrics = filteredMetrics(rows);
  summaryEl.innerHTML = `
    <div class="hero-copy">
      <div class="eyebrow">Attempt Review</div>
      <h2>${escapeHtml(fullTaskLabel)}</h2>
      <div class="summary-lines">
        <div class="summary-line">
          <span class="summary-pill status ${escapeAttr(statusTone(metrics.finalStatus))}">Status ${escapeHtml(statusLabel(metrics.finalStatus))}</span>
          <span class="summary-pill emphasis">Final Score ${escapeHtml(formatScore(metrics.finalScore))}</span>
          ${metrics.stopReason ? `<span class="summary-pill">Stop ${escapeHtml(metrics.stopReason)}</span>` : ""}
        </div>
        <div class="summary-line">
          <span class="summary-pill">Backend ${escapeHtml(metrics.backend)}</span>
          <span class="summary-pill">Model ${escapeHtml(metrics.model)}</span>
          <span class="summary-pill">Supervisor ${escapeHtml(metrics.supervisorModel)}</span>
          <span class="summary-pill">User Simulator ${escapeHtml(metrics.userSimulatorModel)}</span>
          ${edictBadgeHtml(metrics.edict)}
        </div>
        <div class="summary-line">
          <span class="summary-pill">Input Tokens ${escapeHtml(formatTokens(metrics.executorInputTokens))}</span>
          <span class="summary-pill">Output Tokens ${escapeHtml(formatTokens(metrics.executorOutputTokens))}</span>
          <span class="summary-pill">Runtime ${escapeHtml(formatDuration(metrics.runtimeMs))}</span>
        </div>
        <div class="summary-line">
          <span class="summary-pill">Max Final Score ${escapeHtml(formatScore(metrics.maxScore))}</span>
          <span class="summary-pill">Max Supervisor ${escapeHtml(formatScore(metrics.maxSupervisorScore))}</span>
          <span class="summary-pill">Supervision Cycles ${escapeHtml(String(metrics.supervisionCycles))}</span>
          <span class="summary-pill">Continuations ${escapeHtml(String(metrics.continuations))}</span>
        </div>
        <p class="status-line subtle">Setting Avg Score ${escapeHtml(formatScore(settingMetrics.avgScore))} ｜ Setting Avg Runtime ${escapeHtml(formatRuntime(settingMetrics.avgRuntime))} ｜ Setting Avg Continuation ${escapeHtml(settingMetrics.avgContinuation === null ? "n/a" : settingMetrics.avgContinuation.toFixed(2))}</p>
      </div>
    </div>
    <div class="quick-stats"></div>
  `;
}

function textParts(content, type) {
  return (content || [])
    .filter((part) => part.type === type)
    .map((part) => part.text || part[type] || "")
    .join("\n\n")
    .trim();
}

function toolSummary(call) {
  const name = call.name || "tool";
  const args = call.arguments || {};
  if (name === "browser") {
    const action = args.action || "action";
    const target = args.url || args.ref || args.selector || "";
    return `${action}${target ? ` · ${target}` : ""}`;
  }
  if (name === "exec") {
    return shortText(args.command || args.cmd || args.script || pretty(args), 240);
  }
  return shortText(pretty(args), 240);
}

// Strip ANSI color codes — both real ESC-prefixed (\x1b[Nm) and the literal
// "[Nm" form left behind when the ESC byte was lost during JSON serialization.
function stripAnsi(text) {
  return String(text || "")
    .replace(/\x1b\[[0-9;]*m/g, "")
    .replace(/\[[0-9;]+m/g, "");
}

// Resolve a screenshot path observed in a tool-result text into a webui URL.
// resultsRootUrl points to the on-disk result/ root for the attempt. Tools
// commonly save under /tmp_workspace/results/ which maps onto that root, so
// preserve everything after results/ to keep subdirectories like screenshots/.
function resolveResultUrl(rawPath, resultsRootUrl) {
  const cleaned = stripAnsi(String(rawPath || "")).trim().replace(/^[\[\]<>"'`]+|[\[\]<>"'`]+$/g, "");
  if (!cleaned) return null;
  const marker = "/tmp_workspace/results/";
  let rel;
  if (cleaned.startsWith(marker)) {
    rel = cleaned.slice(marker.length);
  } else if (cleaned.includes(marker)) {
    rel = cleaned.split(marker).pop();
  } else if (cleaned.startsWith("/")) {
    // Absolute path that isn't under the known prefix — fall back to basename.
    rel = cleaned.split("/").pop();
  } else {
    rel = cleaned;
  }
  rel = rel.replace(/^\/+/, "");
  if (!rel) return null;
  return `${resultsRootUrl}${rel}`;
}

function toolResultImages(content, options = {}) {
  const images = [];

  // Source of truth #1: image parts directly attached to the toolResult, with
  // base64 data — we render these unconditionally because the data is in-band.
  for (const part of content || []) {
    if (part.type !== "image") continue;
    const src = mediaDataUrl(part.data, part.mimeType || "image/jpeg");
    if (!src) continue;
    images.push({
      src,
      caption: part.alt || part.label || "",
    });
  }

  // Source of truth #2: files saved under the attempt directory — a union of
  //   - ``result/`` files (agent-authored artifacts, enumerated server-side as
  //     ``resultFiles``),
  //   - ``inline_images/`` files (transient screenshots extracted from base64
  //     payloads in tool results; written by ``lib.runner._persist_inline_image``
  //     and enumerated server-side as ``inlineImages``), and
  //   - ``mcp_artifacts/`` files (MCP tool side-effects such as playwright-mcp
  //     auto-saved screenshots, kept outside ``result/`` so they do not flood
  //     the supervisor workspace; enumerated server-side as ``mcpArtifacts``).
  // We only render an inline thumbnail when the toolResult text references a
  // path or basename present in this combined whitelist. References to
  // non-existent files (e.g. "page.png" showing up inside an accessibility
  // tree snapshot) are silently dropped — the user can still browse every
  // saved artifact in the dedicated "Saved Results" panel.
  const resultFiles = Array.isArray(options.resultFiles) ? options.resultFiles : [];
  const inlineImages = Array.isArray(options.inlineImages) ? options.inlineImages : [];
  const mcpArtifacts = Array.isArray(options.mcpArtifacts) ? options.mcpArtifacts : [];
  if (!resultFiles.length && !inlineImages.length && !mcpArtifacts.length) return images;

  const fileByPath = new Map();      // exact relPath under attempt → url
  const fileByBasename = new Map();  // basename → url (first wins on collisions)
  // ``result/`` entries use relPath relative to ``result/`` itself
  for (const f of resultFiles) {
    const rel = String(f && f.path || "").trim();
    if (!rel) continue;
    const url = String(f && f.url || "").trim();
    if (!url) continue;
    fileByPath.set(rel, url);
    const base = rel.split("/").pop();
    if (base && !fileByBasename.has(base)) fileByBasename.set(base, url);
  }
  // ``inline_images/`` entries already carry the ``inline_images/...`` prefix.
  for (const f of inlineImages) {
    const rel = String(f && f.path || "").trim();
    if (!rel) continue;
    const url = String(f && f.url || "").trim();
    if (!url) continue;
    fileByPath.set(rel, url);
    const base = rel.split("/").pop();
    if (base && !fileByBasename.has(base)) fileByBasename.set(base, url);
  }
  // ``mcp_artifacts/`` entries carry the ``mcp_artifacts/...`` prefix.
  for (const f of mcpArtifacts) {
    const rel = String(f && f.path || "").trim();
    if (!rel) continue;
    const url = String(f && f.url || "").trim();
    if (!url) continue;
    fileByPath.set(rel, url);
    const base = rel.split("/").pop();
    if (base && !fileByBasename.has(base)) fileByBasename.set(base, url);
  }

  const text = (content || []).map((p) => (p.type === "text" ? p.text || "" : "")).join("\n");
  const stripped = stripAnsi(text);
  if (!stripped.trim()) return images;

  const seen = new Set();
  function tryAdd(rawCandidate) {
    if (!rawCandidate) return;
    let cleaned = rawCandidate.trim().replace(/^[\[\]<>"'`]+|[\[\]<>"'`]+$/g, "");
    if (!cleaned) return;
    const resultsMarker = "/tmp_workspace/results/";
    // playwright-mcp writes ``--output-dir /tmp_workspace/.mcp_artifacts/...``;
    // the text result references that container-side path (with or without
    // leading slash). We re-root to ``mcp_artifacts/...`` to match the
    // whitelist key layout (host side uses ``<attempt>/mcp_artifacts/`` — no
    // leading dot — per ``collect_attempt_artifacts``).
    const mcpArtifactsMarker = "/tmp_workspace/.mcp_artifacts/";
    let rel = "";
    if (cleaned.startsWith(resultsMarker)) rel = cleaned.slice(resultsMarker.length);
    else if (cleaned.includes(resultsMarker)) rel = cleaned.split(resultsMarker).pop();
    else if (cleaned.startsWith(mcpArtifactsMarker)) rel = "mcp_artifacts/" + cleaned.slice(mcpArtifactsMarker.length);
    else if (cleaned.includes(mcpArtifactsMarker)) rel = "mcp_artifacts/" + cleaned.split(mcpArtifactsMarker).pop();
    else if (cleaned.startsWith("inline_images/")) rel = cleaned;
    else if (cleaned.startsWith("mcp_artifacts/")) rel = cleaned;
    else if (cleaned.startsWith("/")) rel = "";  // unknown absolute path; ignore
    else rel = cleaned;
    rel = rel.replace(/^\/+/, "");
    let url = "";
    if (rel && fileByPath.has(rel)) url = fileByPath.get(rel);
    else {
      const base = (rel || cleaned).split("/").pop();
      if (base && fileByBasename.has(base)) url = fileByBasename.get(base);
    }
    if (!url || seen.has(url)) return;
    seen.add(url);
    images.push({ src: url, caption: (rel || cleaned).split("/").pop() });
  }

  let m;

  // Path A — ``[image: inline_images/<hash>.<ext>]`` references written by
  // ``_normalize_content_blocks`` after persisting extracted base64 payloads.
  // Highest-specificity pattern — always matches a real file in the whitelist.
  const reInline = /\[image:\s*(inline_images\/[A-Za-z0-9_./\-]+\.(?:png|jpe?g|gif|webp))\s*\]/gi;
  while ((m = reInline.exec(stripped)) !== null) tryAdd(m[1]);

  // Path B — explicit ``/tmp_workspace/results/<path>`` mention.
  const reContainerPath = /\/tmp_workspace\/results\/([^\s\[\]<>"'`]+\.(?:png|jpe?g|gif|webp))/gi;
  while ((m = reContainerPath.exec(stripped)) !== null) tryAdd(m[1]);

  // Path B' — playwright-mcp writes its output-dir path as a Markdown link
  // target, typically dropping the leading slash:
  //   [Screenshot of viewport](tmp_workspace/.mcp_artifacts/mcp_screenshots/page-xxx.png)
  // Match both with and without the leading slash and re-root to
  // ``mcp_artifacts/...`` for whitelist lookup.
  const reMcpArtifacts = /\/?tmp_workspace\/\.mcp_artifacts\/([^\s\[\]<>"'`()]+\.(?:png|jpe?g|gif|webp))/gi;
  while ((m = reMcpArtifacts.exec(stripped)) !== null) tryAdd("mcp_artifacts/" + m[1]);

  // Path C — "Screenshot saved to <path>" / "Saved screenshot to <path>".
  const reSaved = /(?:Screenshot|Saved screenshot)\s+(?:saved\s+to|to)\s+([^\s\[\]<>"'`]+\.(?:png|jpe?g|gif|webp))/gi;
  while ((m = reSaved.exec(stripped)) !== null) tryAdd(m[1]);

  // Path D — file emoji at line start (nanobot style).
  const reEmoji = /(?:^|[\r\n])\s*[📄💾📷🖼]\s*([A-Za-z0-9_./\-]+\.(?:png|jpe?g|gif|webp))/g;
  while ((m = reEmoji.exec(stripped)) !== null) tryAdd(m[1]);

  // Path E — "[image: <label>]" fallback form used by
  // ``_normalize_content_blocks`` when no base64 payload was available (the
  // <label> is usually a basename the agent chose). Only matches short labels
  // without path separators to avoid swallowing multi-line labels.
  const reImageLabel = /\[image:\s*([A-Za-z0-9_.\-]+\.(?:png|jpe?g|gif|webp))\s*\]/gi;
  while ((m = reImageLabel.exec(stripped)) !== null) tryAdd(m[1]);

  // Path F — entire trimmed text is a single short bare filename. Skip when
  // text contains whitespace (multi-line snapshots) or is unreasonably long.
  const trimmed = stripped.trim();
  if (trimmed.length > 0 && trimmed.length <= 200 && !/\s/.test(trimmed) && /\.(?:png|jpe?g|gif|webp)$/i.test(trimmed)) {
    tryAdd(trimmed);
  }

  return images;
}

function summarizeToolResultText(text, imageCount) {
  const clean = stripAnsi(String(text || "")).trim();
  if (!clean && imageCount) return `Returned ${imageCount} image result(s).`;
  if (!clean) return "";
  const compact = clean
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => (line.startsWith("MEDIA:") ? "Captured image artifact." : line))
    .join("\n");
  return shortText(compact, 600);
}

function timelineFromTranscript(transcript, options = {}) {
  const events = [];
  let userIndex = 0;
  const rootAgentId = options.primaryAgentId || "";
  const showTools = options.showTools !== false;
  for (const item of transcript || []) {
    const agentId = item.agentId || item.agent || item.agent_id || item.message?.agentId || "";
    const agent = agentMeta(agentId);
    if (item.type === "plain_message") {
      events.push({
        kind: item.role === "assistant" ? "assistant" : "system",
        title: item.role === "assistant" ? "Agent Output" : "Runtime Log",
        body: item.text || "",
        agentId,
        agent,
      });
      continue;
    }
    if (item.type !== "message") continue;
    const message = item.message || {};
    const content = message.content || [];
    if ((message.role || "") === "assistant") {
      const assistantText = textParts(content, "text");
      if (assistantText) {
        events.push({
          kind: "assistant",
          title: agent ? `${agent.label} Output` : "Agent Output",
          body: assistantText,
          agentId,
          agent,
        });
      }
      for (const part of content) {
        if (part.type !== "toolCall") continue;
        if (!showTools) continue;
        events.push({
          kind: "tool",
          title: part.name || "tool",
          body: toolSummary(part),
          agentId,
          agent,
        });
      }
    } else if ((message.role || "") === "user") {
      const userText = textParts(content, "text");
      if (userText) {
        const delegated = agentId && rootAgentId && agentId !== rootAgentId;
        // In multi-agent edict runs, a sessions_send / sessions_spawn reply
        // from a sub-agent (e.g. zhongshu) shows up as a role=user
        // message on the primary's transcript. openclaw tags these with
        // ``provenance.kind === "inter_session"`` and
        // ``provenance.sourceSessionKey === "agent:<id>:main"``. Labelling
        // them "Simulated User / Continuation" falsely attributes the
        // sub-agent's court-register text to the human user_simulator and
        // reads like voice contamination. Detect and label accordingly.
        const provenance = (message && typeof message === "object" ? (message.provenance || {}) : {}) || {};
        const provKind = String(provenance.kind || "");
        const sourceSessionKey = String(provenance.sourceSessionKey || "");
        const fromSubAgent =
          provKind === "inter_session" ||
          (sourceSessionKey.startsWith("agent:") && !sourceSessionKey.includes(":user"));
        const sourceAgentId = fromSubAgent
          ? (sourceSessionKey.split(":")[1] || "").trim()
          : "";
        const sourceAgentMeta = sourceAgentId ? EDICT_AGENT_META[sourceAgentId] : null;
        // Orchestrator final-report triggers from docker/edict_orchestrator.py
        // land as role=user messages on taizi's transcript without any
        // `provenance` marker, so they previously got tagged "Simulated
        // User / Continuation". They're not user_simulator output — they're
        // the in-container orchestrator waking taizi up at the end of a
        // state=Done cycle. Recognize them by the literal prefix +
        // "(orchestrator trigger:" tail that ``invoke_taizi_final_report``
        // always emits.
        const orchestratorTrigger =
          !delegated &&
          !fromSubAgent &&
          /\[system\]\s*子代理链路/.test(userText) &&
          /orchestrator trigger:/i.test(userText);
        // Only count toward the userIndex when this is a real user-side
        // message (initial task input or a user_simulator continuation).
        // Orchestrator triggers and sub-agent reports are internal and
        // must not shift the "Task Input" vs "Simulated User" boundary.
        if (!delegated && !fromSubAgent && !orchestratorTrigger) userIndex += 1;
        let title;
        let eventKind = "user";
        if (delegated) {
          title = `Delegated Input · ${agent ? agent.label : agentId}`;
          eventKind = "system";
        } else if (fromSubAgent) {
          const sourceLabel = sourceAgentMeta ? `${sourceAgentMeta.emoji} ${sourceAgentMeta.label}` : (sourceAgentId || "sub-agent");
          title = `Sub-agent Report · ${sourceLabel}`;
          eventKind = "system";
        } else if (orchestratorTrigger) {
          title = "Orchestrator Trigger · state=Done";
          eventKind = "system";
        } else if (userIndex === 1) {
          title = "Task Input";
        } else {
          title = "Simulated User / Continuation";
        }
        events.push({
          kind: eventKind,
          title,
          body: userText,
          agentId,
          agent,
        });
      }
    } else if ((message.role || "") === "toolResult") {
      const images = toolResultImages(content, {
        resultBaseUrl: options.resultBaseUrl || "",
        resultFiles: options.resultFiles || [],
        inlineImages: options.inlineImages || [],
        mcpArtifacts: options.mcpArtifacts || [],
      });
      const body = summarizeToolResultText(textParts(content, "text"), images.length);
      if (body || images.length) {
        events.push({
          kind: images.length ? "tool-result" : "tool",
          title: showTools ? `Tool Result · ${message.toolName || "tool"}` : (images.length ? "Snapshot" : ""),
          body: showTools ? body : "",
          images,
          agentId,
          agent,
        });
      }
    }
  }
  return events;
}

function groupTurnsFromTranscript(detail, payload) {
  const attemptPath = detail.selectedAttemptPath || payload?.selectedAttemptPath || "";
  const resultBaseUrl = attemptPath ? `/runs/${attemptPath}/result/` : "";
  // Authoritative whitelist of files actually saved on disk under this
  // attempt — union of ``result/`` (agent-authored, from ``resultFiles``) and
  // ``inline_images/`` (transient screenshots extracted from base64 payloads,
  // from ``inlineImages``). Inline thumbnails render ONLY for entries in
  // this combined list, so text mentions of non-existent paths (e.g. a page
  // element labelled "page.png" inside an accessibility-tree snapshot) never
  // produce broken image cards.
  const resultFiles = Array.isArray(detail.resultFiles) ? detail.resultFiles : (Array.isArray(payload?.resultFiles) ? payload.resultFiles : []);
  const inlineImages = Array.isArray(detail.inlineImages) ? detail.inlineImages : (Array.isArray(payload?.inlineImages) ? payload.inlineImages : []);
  const mcpArtifacts = Array.isArray(detail.mcpArtifacts) ? detail.mcpArtifacts : (Array.isArray(payload?.mcpArtifacts) ? payload.mcpArtifacts : []);
  const events = timelineFromTranscript(detail.transcript || [], {
    primaryAgentId: primaryAgentId(detail, payload),
    showTools: payload?.showTools !== false,
    resultBaseUrl,
    resultFiles,
    inlineImages,
    mcpArtifacts,
  });
  const turns = [];
  let current = null;
  for (const event of events) {
    if (event.kind === "user") {
      if (current) turns.push(current);
      current = {
        turnIndex: turns.length + 1,
        userEvent: event,
        events: [event],
      };
      continue;
    }
    if (!current) {
      current = {
        turnIndex: turns.length + 1,
        userEvent: null,
        events: [],
      };
    }
    current.events.push(event);
  }
  if (current) turns.push(current);
  return turns;
}

function renderFlowEvent(event) {
  return `
    <div class="bubble ${event.kind}" ${event.agentId ? `data-agent="${escapeAttr(event.agentId)}"` : ""}>
      <div class="bubble-title-row">
        <div class="bubble-title">${escapeHtml(event.title)}</div>
        ${event.agent ? `<span class="agent-chip agent-${escapeAttr(event.agent.id)}">${escapeHtml(`${event.agent.emoji} ${event.agent.label}`)}</span>` : ""}
      </div>
      ${event.body ? `<div class="bubble-body"><pre>${escapeHtml(event.body)}</pre></div>` : ""}
      ${(event.images || []).map((image, index) => imagePreviewMarkup(image.src, image.caption || `${event.title} image ${index + 1}`)).join("")}
    </div>
  `;
}

function flowEventVisible(event) {
  if (!showToolDetails && (event.kind === "tool" || (event.kind === "tool-result" && !(event.images || []).length))) {
    return false;
  }
  if (flowFilter === "all") return true;
  if (flowFilter === "user") return event.kind === "user";
  if (flowFilter === "supervisor") return false;
  if (flowFilter === "executor") return ["assistant", "tool", "tool-result", "system"].includes(event.kind);
  return true;
}

function flowShowsSupervisor() {
  return flowFilter === "all" || flowFilter === "supervisor";
}

function flowShowsExecutorExtras() {
  return flowFilter === "all" || flowFilter === "executor";
}

function selectedAttemptDetails(payload) {
  const details = Array.isArray(payload?.attemptDetails) ? payload.attemptDetails : [];
  const selected = String(payload?.selectedAttemptPath || "").trim();
  if (!selected) return details;
  const match = details.find((detail) => String(detail?.attemptPath || "").trim() === selected);
  return match ? [match] : details;
}

function selectedAttemptDetail(payload) {
  const details = selectedAttemptDetails(payload);
  return details[details.length - 1] || null;
}

function updateFlowFilterButtons() {
  for (const el of flowFilterEls) {
    const active = (el.dataset.flowFilter || "all") === flowFilter;
    el.classList.toggle("active", active);
    el.setAttribute("aria-pressed", active ? "true" : "false");
  }
}

function setupFlowFilters() {
  updateFlowFilterButtons();
  for (const el of flowFilterEls) {
    el.addEventListener("click", () => {
      const next = el.dataset.flowFilter || "all";
      if (next === flowFilter) return;
      flowFilter = next;
      updateFlowFilterButtons();
      if (activePayload) {
        renderFlow(activePayload);
      }
    });
  }
  flowShowToolsEl?.addEventListener("change", () => {
    showToolDetails = Boolean(flowShowToolsEl.checked);
    if (activePayload) {
      renderFlow(activePayload);
    }
  });
}

function populateAttemptSelector(payload) {
  if (!attemptSelectEl || !attemptSelectWrapEl) return;
  const cards = Array.isArray(payload?.attemptCards) ? payload.attemptCards : [];
  attemptSelectEl.innerHTML = "";
  if (cards.length <= 1) {
    attemptSelectWrapEl.classList.add("hidden");
    return;
  }
  for (const card of cards) {
    const option = document.createElement("option");
    option.value = String(card.attemptPath || "");
    option.textContent = stageLabel(card);
    attemptSelectEl.appendChild(option);
  }
  attemptSelectEl.value = String(payload?.selectedAttemptPath || cards[cards.length - 1]?.attemptPath || "");
  attemptSelectWrapEl.classList.remove("hidden");
}

function renderContinuationDecision(item, cycle = null) {
  if (!item) return "";
  const summaryReason = continuationSummaryReason(item, cycle);
  const statusLine = continuationStatusLine(item);
  const blocks = [
    `<pre>${escapeHtml(pretty({
      verdict: item.verdict,
      attemptState: item.attemptState,
      currentScore: item.currentScore,
      finalCompletionScore: item.finalCompletionScore,
      error: item.error,
      transcriptAvailable: item.transcriptAvailable,
      assistantCompletionSignal: item.assistantCompletionSignal,
      executorCompleted: item.executorCompleted,
      executorCompletionReason: item.executorCompletionReason,
      rawSupervisorVerdict: item.rawSupervisorVerdict,
      evaluationIndex: item.evaluationIndex,
      safeUserFeedback: item.safeUserFeedback,
      followupAgentExitCode: item.followupAgentExitCode,
    }))}</pre>`,
  ];
  if (cycle?.rationale) {
    blocks.push(`<div class="check-copy"><strong>Supervisor Rationale</strong><pre>${escapeHtml(cycle.rationale)}</pre></div>`);
  }
  if (Array.isArray(cycle?.missing_artifacts) && cycle.missing_artifacts.length) {
    blocks.push(`<div class="check-copy"><strong>Missing Artifacts</strong><pre>${escapeHtml(cycle.missing_artifacts.join("\n- "))}</pre></div>`);
  }
  return `
    <details class="bubble continuation">
      <summary class="continuation-summary">
        <span class="continuation-summary-status">${escapeHtml(statusLine)}</span>
        ${summaryReason ? `<span class="continuation-summary-reason">${escapeHtml(summaryReason)}</span>` : ""}
      </summary>
      <div class="bubble-body">
        ${blocks.join("")}
      </div>
    </details>
  `;
}

function continuationStatusLine(item) {
  return `Continuation ${item.index || "?"} · ${item.action || "stop"} · ${item.reason || "unknown"}`;
}

function continuationSummaryReason(item, cycle = null) {
  const candidates = [
    cycle?.rationale,
    Array.isArray(cycle?.missing_artifacts) ? cycle.missing_artifacts[0] : "",
    cycle?.public_feedback_summary,
    item?.safeUserFeedback,
    item?.reason,
  ];
  for (const value of candidates) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text) continue;
    return text.length > 220 ? `${text.slice(0, 217)}...` : text;
  }
  return "";
}

function recentToolCalls(toolUsage, limit = 10) {
  const calls = Array.isArray(toolUsage?.tool_calls) ? toolUsage.tool_calls : [];
  return calls.slice(-limit);
}

function toolUsageSummary(toolUsage) {
  if (!toolUsage || !Object.keys(toolUsage).length) return null;
  return {
    toolCounts: toolUsage.tool_counts || {},
    browserActionCounts: toolUsage.browser_action_counts || {},
    recentCalls: recentToolCalls(toolUsage).map((call) => ({
      name: call.name,
      summary: toolSummary(call),
      timestamp: call.timestamp,
    })),
  };
}

function delegationTrace(toolUsage) {
  const calls = Array.isArray(toolUsage?.tool_calls) ? toolUsage.tool_calls : [];
  const items = [];
  for (const call of calls) {
    if (!call || typeof call !== "object") continue;
    const name = String(call.name || "").trim();
    const args = call.arguments || {};
    if (name === "sessions_send") {
      items.push({
        fromAgent: String(call.agentId || "").trim(),
        toAgent: parseAgentSessionTarget(args.sessionKey),
        via: "sessions_send",
        summary: toolSummary(call),
      });
      continue;
    }
    if (name === "sessions_spawn") {
      items.push({
        fromAgent: String(call.agentId || "").trim(),
        toAgent: String(args.agentId || args.agent || args.targetAgent || "").trim(),
        via: "sessions_spawn",
        summary: toolSummary(call),
      });
      continue;
    }
    if (name === "subagents") {
      const toAgent = String(args.agentId || args.agent || args.targetAgent || "").trim();
      const action = String(args.action || "").trim();
      if (!toAgent && !action) continue;
      items.push({
        fromAgent: String(call.agentId || "").trim(),
        toAgent,
        via: "subagents",
        summary: toolSummary(call),
      });
    }
  }
  return items;
}

function runtimeProbeSummary(runtimeProbe) {
  if (!runtimeProbe || !Object.keys(runtimeProbe).length) return null;
  return {
    windows: runtimeProbe.windows || [],
    resultFiles: runtimeProbe.result_files || [],
    processes: runtimeProbe.processes || {},
  };
}

function sortedAgentSessions(detail) {
  const sessions = Array.isArray(detail?.agentSessions) ? detail.agentSessions.slice() : [];
  return sessions.sort((a, b) => {
    const ia = EDICT_AGENT_ORDER.indexOf(a.id || "");
    const ib = EDICT_AGENT_ORDER.indexOf(b.id || "");
    if (ia === -1 && ib === -1) return String(a.id || "").localeCompare(String(b.id || ""));
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
}

function renderAgentRoster(detail) {
  const sessions = sortedAgentSessions(detail);
  if (!sessions.length) return "";
  const cards = sessions.map((session) => {
    const toolCounts = session.toolUsage?.tool_counts || {};
    const toolKinds = Object.keys(toolCounts).length;
    const totalToolCalls = Array.isArray(session.toolUsage?.tool_calls) ? session.toolUsage.tool_calls.length : 0;
    const label = session.label || agentMeta(session.id)?.label || session.id || "agent";
    const emoji = session.emoji || agentMeta(session.id)?.emoji || "🧩";
    const role = session.role || agentMeta(session.id)?.role || "";
    const highlights = Object.entries(toolCounts)
      .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0))
      .slice(0, 3)
      .map(([name, count]) => `${name} ${count}`);
    return `
      <div class="agent-card" data-agent="${escapeAttr(session.id || "")}">
        <div class="agent-card-head">
          <span class="agent-card-emoji">${escapeHtml(emoji)}</span>
          <div>
            <div class="agent-card-title">${escapeHtml(label)}</div>
            <div class="agent-card-subtitle">${escapeHtml(role || "Agent")}</div>
          </div>
        </div>
        <div class="agent-card-metrics">
          <span>${escapeHtml(`${session.eventCount || 0} event(s)`)}</span>
          <span>${escapeHtml(`${toolKinds} tool type(s)`)}</span>
          <span>${escapeHtml(`${totalToolCalls} tool call(s)`)}</span>
        </div>
        ${highlights.length ? `<div class="agent-card-highlights">${highlights.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
      </div>
    `;
  });
  return `<div class="agent-roster">${cards.join("")}</div>`;
}

function renderDelegationTrace(detail) {
  const trace = delegationTrace(detail?.toolUsage || {});
  if (!trace.length) return "";
  const items = trace.map((item) => {
    const from = agentMeta(item.fromAgent);
    const to = agentMeta(item.toAgent);
    const fromLabel = from ? `${from.emoji} ${from.label}` : (item.fromAgent || "agent");
    const toLabel = to ? `${to.emoji} ${to.label}` : (item.toAgent || "unknown");
    return `
      <div class="handoff-item">
        <div class="handoff-route">
          <span class="agent-chip agent-${escapeAttr(item.fromAgent || "unknown")}">${escapeHtml(fromLabel)}</span>
          <span class="handoff-arrow">→</span>
          <span class="agent-chip agent-${escapeAttr(item.toAgent || "unknown")}">${escapeHtml(toLabel)}</span>
          <span class="handoff-via">${escapeHtml(item.via)}</span>
        </div>
        <div class="handoff-summary">${escapeHtml(item.summary || "")}</div>
      </div>
    `;
  });
  return `
    <details class="handoff-trace" open>
      <summary class="continuation-summary">
        <span>Delegation Trace</span>
        <span>${escapeHtml(`${trace.length} handoff(s)`)}</span>
      </summary>
      <div class="handoff-list">${items.join("")}</div>
    </details>
  `;
}

function renderFlow(payload) {
  timelineEl.innerHTML = "";
  const details = selectedAttemptDetails(payload);
  if (!details.length) {
    timelineEl.innerHTML = `<div class="empty">${escapeHtml(payload.emptyReason || "No flow available.")}</div>`;
    return;
  }
  const hasAnyTranscript = details.some((detail) => Array.isArray(detail.transcript) && detail.transcript.length);
  const hasAnySupervision = details.some((detail) => Array.isArray(detail.supervisionTrace) && detail.supervisionTrace.length);
  const hasAnyLogs = details.some((detail) => detail.logs && Object.keys(detail.logs).length);
  if (!hasAnyTranscript && !hasAnySupervision && !hasAnyLogs && payload.emptyReason) {
    timelineEl.innerHTML = `<div class="empty">${escapeHtml(payload.emptyReason)}</div>`;
    return;
  }
  let renderedAnything = false;
  for (const detail of details) {
    const block = document.createElement("div");
    block.className = "flow-stage";
    const completionScore = detail.score?.final_completion_score ?? detail.score?.capped_score ?? 0;
    const supervisorScore = detail.score?.overall_score;
    const verdict = detail.score?.verdict || "unknown";
    const supervisorModel = displayModelName(detail.supervision?.supervisor?.model || "supervisor n/a");
    block.innerHTML = `
      <div class="flow-stage-head">
        <strong>${escapeHtml(stageLabel(detail))}</strong>
        <span class="flow-stage-meta">${escapeHtml(`final ${formatScore(completionScore)} ｜ supervisor ${formatScore(supervisorScore)} ｜ ${verdictLabel(verdict)} ｜ ${supervisorModel} ｜ ${(detail.meta || {}).backend || payload.backend || "backend n/a"}`)}</span>
      </div>
    `;
    let blockHasContent = false;
    const agentRoster = showToolDetails ? renderAgentRoster(detail) : "";
    if (agentRoster) {
      block.insertAdjacentHTML("beforeend", agentRoster);
      blockHasContent = true;
    }
    const handoffTrace = showToolDetails ? renderDelegationTrace(detail) : "";
    if (handoffTrace) {
      block.insertAdjacentHTML("beforeend", handoffTrace);
      blockHasContent = true;
    }
    if (flowShowsExecutorExtras() && showToolDetails) {
      for (const item of detail.keyNodes || []) {
        const node = document.createElement("div");
        node.className = "bubble system";
        node.innerHTML = `<div class="bubble-title">${escapeHtml(item.title || "Key Node")}</div><div class="bubble-body"><pre>${escapeHtml(item.body || "")}</pre></div>`;
        block.appendChild(node);
        blockHasContent = true;
      }
    }
    const turns = groupTurnsFromTranscript(detail, { ...payload, showTools: showToolDetails });
    const cycleMap = new Map((detail.supervisionTrace || []).map((cycle) => [Number(cycle.evaluation_index || 0), cycle]));
    const continuationMap = new Map((detail.continuationTrace || []).map((item) => [Number(item.evaluationIndex || item.index || 0), item]));
    const recordingsByCycle = detail.recordingsByCycle || {};
    for (const turn of turns) {
      // Per-cycle recording — render ABOVE the executor flow events and the
      // supervisor/continuation blocks for this turn, so users see the video
      // as the opening artifact of each cycle.
      const cycleRecording = recordingsByCycle[String(turn.turnIndex)] || recordingsByCycle[turn.turnIndex];
      if (cycleRecording && cycleRecording.url) {
        block.insertAdjacentHTML("beforeend", renderCycleRecording(turn.turnIndex, cycleRecording));
        blockHasContent = true;
      }
      for (const event of turn.events) {
        if (!flowEventVisible(event)) continue;
        block.insertAdjacentHTML("beforeend", renderFlowEvent(event));
        blockHasContent = true;
      }
      if (flowShowsSupervisor()) {
        const cycle = cycleMap.get(turn.turnIndex);
        if (cycle) {
          block.insertAdjacentHTML("beforeend", renderSupervisorCycle(cycle));
          blockHasContent = true;
        }
        const continuation = continuationMap.get(turn.turnIndex);
        if (continuation) {
          block.insertAdjacentHTML("beforeend", renderContinuationDecision(continuation, cycle || null));
          blockHasContent = true;
        }
      }
      const continuationRecord = (detail.continuations || []).find((item) => Number(item.index || 0) === turn.turnIndex);
      const nextTurnExists = turns.some((candidate) => candidate.turnIndex === turn.turnIndex + 1 && candidate.userEvent);
      if (continuationRecord && !nextTurnExists && flowEventVisible({ kind: "user" })) {
        block.insertAdjacentHTML("beforeend", renderFlowEvent({
          kind: "user",
          title: `Simulated User / Continuation ${continuationRecord.index || "?"}`,
          body: continuationRecord.safeUserFeedback || "",
          images: [],
        }));
        blockHasContent = true;
      }
    }
    if (flowShowsExecutorExtras() && showToolDetails) {
      const toolSummaryPayload = toolUsageSummary(detail.toolUsage);
      if (toolSummaryPayload) {
        const toolKinds = Object.keys(toolSummaryPayload.toolCounts || {});
        const node = document.createElement("details");
        node.className = "bubble tool";
        node.innerHTML = `
          <summary class="continuation-summary">
            <span>Tool Usage</span>
            <span>${escapeHtml(`${toolKinds.length} tool type(s) ｜ ${(toolSummaryPayload.recentCalls || []).length} recent call(s)`)}</span>
          </summary>
          <div class="bubble-body">
            <pre>${escapeHtml(pretty(toolSummaryPayload))}</pre>
          </div>
        `;
        block.appendChild(node);
        blockHasContent = true;
      }
      const probeSummary = runtimeProbeSummary(detail.runtimeProbe);
      if (probeSummary) {
        const node = document.createElement("details");
        node.className = "bubble system";
        node.innerHTML = `
          <summary class="continuation-summary">
            <span>Runtime Probe</span>
            <span>${escapeHtml(`${(probeSummary.windows || []).length} window(s) ｜ ${(probeSummary.resultFiles || []).length} result file(s)`)}</span>
          </summary>
          <div class="bubble-body">
            <pre>${escapeHtml(pretty(probeSummary))}</pre>
          </div>
        `;
        block.appendChild(node);
        blockHasContent = true;
      }
    }
    if (blockHasContent) {
      timelineEl.appendChild(block);
      renderedAnything = true;
    }
  }
  if (!renderedAnything) {
    timelineEl.innerHTML = `<div class="empty">No flow items match the current flow filter.</div>`;
  }
}

function isPreferredResult(file, payload) {
  const processFile = (payload.process || {}).file || "";
  const preferred = new Set([...(payload.outputs || []), processFile]);
  if (!preferred.size) {
    return /^[^/]+\.(md|markdown|txt|log|json|jsonl|ndjson|ya?ml|csv|tsv|html?|pdf|png|jpe?g|gif|webp|svg|mp4|webm)$/i.test(file.path) || file.path === "process.md";
  }
  return preferred.has(`/tmp_workspace/results/${file.path}`) || preferred.has(file.path) || file.path === "process.md";
}

function resultBaseDir(file) {
  if (!file?.url) return "";
  const idx = file.url.lastIndexOf("/");
  return idx === -1 ? file.url : file.url.slice(0, idx + 1);
}

function fileExt(path = "") {
  const name = String(path || "").split(/[?#]/, 1)[0];
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : "";
}

function resultFileKind(file) {
  const ext = fileExt(file?.path || file?.url || "");
  if (["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif"].includes(ext)) return "image";
  if (["mp4", "webm", "mov", "m4v"].includes(ext)) return "video";
  if (["mp3", "wav", "ogg", "m4a"].includes(ext)) return "audio";
  if (ext === "pdf") return "pdf";
  if (["html", "htm"].includes(ext)) return "html";
  if (["md", "markdown"].includes(ext)) return "markdown";
  if (["json", "jsonl", "ndjson"].includes(ext)) return "json";
  if (["csv", "tsv"].includes(ext)) return "table";
  if (["txt", "log", "yaml", "yml", "xml", "env", "py", "js", "ts", "css", "toml", "ini"].includes(ext)) return "text";
  if (["ppt", "pptx", "key"].includes(ext)) return "presentation";
  if (["xls", "xlsx", "ods"].includes(ext)) return "spreadsheet";
  if (["doc", "docx", "rtf"].includes(ext)) return "document";
  if (["zip", "tar", "gz", "tgz", "bz2", "xz", "7z"].includes(ext)) return "archive";
  if (canPreviewTextFile(file?.path || "")) return "text";
  return "binary";
}

function bytes(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let size = n;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  const digits = idx === 0 || size >= 10 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[idx]}`;
}

async function fetchResultText(file) {
  if (Object.prototype.hasOwnProperty.call(file || {}, "text") && typeof file.text === "string") return file.text;
  if (!file?.url) throw new Error(file?.assetUnavailableReason || "Artifact file is not included in this static export.");
  const response = await fetch(file.url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.text();
}

function hasInlineResultText(file, kind = resultFileKind(file)) {
  return ["markdown", "json", "table", "text"].includes(kind)
    && typeof file?.text === "string"
    && file.text.length > 0;
}

function prettyJsonLike(text, ext) {
  if (ext === "jsonl" || ext === "ndjson") {
    const lines = String(text || "").split(/\r?\n/);
    const pretty = lines.map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return "";
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch {
        return line;
      }
    });
    return pretty.join("\n");
  }
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text || "";
  }
}

function parseDelimitedRows(text, delimiter) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const value = String(text || "");
  for (let i = 0; i < value.length; i += 1) {
    const ch = value[i];
    if (quoted) {
      if (ch === '"' && value[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
      continue;
    }
    if (ch === '"') {
      quoted = true;
    } else if (ch === delimiter) {
      row.push(cell);
      cell = "";
    } else if (ch === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (ch !== "\r") {
      cell += ch;
    }
  }
  row.push(cell);
  if (row.some((item) => item !== "") || rows.length) rows.push(row);
  return rows;
}

function renderDelimitedTable(text, file) {
  const ext = fileExt(file.path);
  const delimiter = ext === "tsv" ? "\t" : ",";
  const rows = parseDelimitedRows(text, delimiter).slice(0, 80);
  if (!rows.length) return `<pre class="file-preview-pre">${escapeHtml(text || "")}</pre>`;
  const maxCols = Math.min(24, Math.max(...rows.map((row) => row.length)));
  const header = rows[0] || [];
  const body = rows.slice(1);
  const headerHtml = Array.from({ length: maxCols }, (_, i) => `<th>${escapeHtml(header[i] ?? "")}</th>`).join("");
  const bodyHtml = body.map((row) => (
    `<tr>${Array.from({ length: maxCols }, (_, i) => `<td>${escapeHtml(row[i] ?? "")}</td>`).join("")}</tr>`
  )).join("");
  const truncated = parseDelimitedRows(text, delimiter).length > rows.length ? `<div class="result-preview-note">Showing first ${rows.length} rows.</div>` : "";
  return `
    <div class="result-table-wrap">
      <table class="result-table">
        <thead><tr>${headerHtml}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>
    ${truncated}
  `;
}

function resultBinaryNotice(file, label) {
  const size = bytes(file.size);
  const unavailable = !file?.url;
  const reason = file?.assetUnavailableReason || "This artifact is not included in this static export.";
  return `
    <div class="result-binary-preview">
      <strong>${escapeHtml(label)}</strong>
      <span>${escapeHtml(file.path)}${size ? ` · ${escapeHtml(size)}` : ""}</span>
      ${unavailable
        ? `<span class="result-unavailable">${escapeHtml(reason)}</span>`
        : `<a href="${escapeAttr(file.url)}" target="_blank" rel="noreferrer">Open raw file</a>`}
    </div>
  `;
}

async function renderResultBody(file) {
  const kind = resultFileKind(file);
  const ext = fileExt(file.path);
  const hasInlineText = hasInlineResultText(file, kind);
  if (!file?.url && !hasInlineText) {
    return resultBinaryNotice(file, `${kind[0].toUpperCase()}${kind.slice(1)} artifact`);
  }
  if (kind === "image") {
    return `<figure class="md-figure"><button type="button" class="image-preview-trigger" data-preview-src="${escapeAttr(file.url)}" data-preview-caption="${escapeAttr(file.path)}"><img src="${escapeAttr(file.url)}" alt="${escapeAttr(file.path)}" loading="lazy" /></button><figcaption>${escapeHtml(file.path)}</figcaption></figure>`;
  }
  if (kind === "video") {
    return `<video class="result-media" controls preload="metadata" src="${escapeAttr(file.url)}"></video>`;
  }
  if (kind === "audio") {
    return `<audio class="result-audio" controls preload="metadata" src="${escapeAttr(file.url)}"></audio>`;
  }
  if (kind === "pdf") {
    return `<iframe class="result-frame pdf" src="${escapeAttr(file.url)}" title="${escapeAttr(file.path)}"></iframe>`;
  }
  if (kind === "html") {
    return `<iframe class="result-frame html" src="${escapeAttr(file.url)}" title="${escapeAttr(file.path)}" sandbox="" referrerpolicy="no-referrer"></iframe>`;
  }
  if (kind === "markdown") {
    const text = await fetchResultText(file);
    try {
      const html = await renderMarkdownRich(text, { baseUrl: resultBaseDir(file) });
      return `<div class="markdown-body result-markdown">${html}</div>`;
    } catch {
      return `<pre class="file-preview-pre">${escapeHtml(text)}</pre>`;
    }
  }
  if (kind === "json") {
    const text = await fetchResultText(file);
    return `<pre class="file-preview-pre result-code">${escapeHtml(prettyJsonLike(text, ext))}</pre>`;
  }
  if (kind === "table") {
    const text = await fetchResultText(file);
    return renderDelimitedTable(text, file);
  }
  if (kind === "text") {
    const text = await fetchResultText(file);
    return `<pre class="file-preview-pre result-code">${escapeHtml(text)}</pre>`;
  }
  if (kind === "presentation") return resultBinaryNotice(file, "Presentation file");
  if (kind === "spreadsheet") return resultBinaryNotice(file, "Spreadsheet file");
  if (kind === "document") return resultBinaryNotice(file, "Document file");
  if (kind === "archive") return resultBinaryNotice(file, "Archive file");
  return resultBinaryNotice(file, "Binary artifact");
}

async function hydrateResultBody(details, file) {
  const body = details.querySelector(".result-body");
  if (!body || body.dataset.loaded === "true") return;
  body.dataset.loaded = "loading";
  body.innerHTML = `<div class="loading-stub">Loading preview…</div>`;
  try {
    body.innerHTML = await renderResultBody(file);
    body.dataset.loaded = "true";
  } catch (err) {
    body.dataset.loaded = "error";
    body.innerHTML = `<div class="error-stub">Preview failed: ${escapeHtml(err.message || err)}</div>`;
  }
}

async function renderOutputs(payload) {
  outputsEl.innerHTML = "";
  const files = Array.isArray(payload.resultFiles) ? payload.resultFiles : [];
  if (!files.length) {
    outputsEl.innerHTML = `<div class="empty">${escapeHtml(payload.emptyReason || "No saved results.")}</div>`;
    return;
  }
  const sorted = files.slice().sort((a, b) => {
    const pa = isPreferredResult(a, payload) ? 0 : 1;
    const pb = isPreferredResult(b, payload) ? 0 : 1;
    if (pa !== pb) return pa - pb;
    return a.path.localeCompare(b.path);
  });
  for (const file of sorted) {
    const details = document.createElement("details");
    details.className = "result-item";
    const preferred = isPreferredResult(file, payload);
    if (preferred) details.open = true;
    const kind = resultFileKind(file);
    const size = bytes(file.size);
    const previewable = !["binary", "archive", "presentation", "spreadsheet", "document"].includes(kind);
    const hasUrl = Boolean(file.url);
    const hasInlineText = hasInlineResultText(file, kind);
    details.innerHTML = `
      <summary class="result-summary">
        <span class="result-title">
          <strong>${escapeHtml(file.path)}</strong>
          <span class="result-file-meta">${escapeHtml(kind)}${size ? ` · ${escapeHtml(size)}` : ""}${!hasUrl ? " · lite metadata" : ""}</span>
        </span>
        <span class="result-actions">
          ${hasUrl && canPreviewTextFile(file.path) ? `<button type="button" class="result-preview-link file-preview-trigger" data-preview-url="${escapeAttr(file.url)}" data-preview-name="${escapeAttr(file.path)}">preview</button>` : ""}
          ${hasUrl
            ? `<a href="${escapeAttr(file.url)}" target="_blank" rel="noreferrer">${previewable ? "open" : "download"}</a>`
            : `<span class="result-unavailable">${hasInlineText ? "inline" : "not exported"}</span>`}
        </span>
      </summary>
      <div class="result-body" data-loaded="false"></div>
    `;
    details.addEventListener("toggle", () => {
      if (details.open) hydrateResultBody(details, file);
    });
    outputsEl.appendChild(details);
    if (details.open) hydrateResultBody(details, file);
  }
}

function renderCycleRecording(turnIndex, rec) {
  // Inline player rendered at the TOP of a cycle block in the Execution Flow
  // timeline. One recording per cycle — the executor's desktop during that
  // cycle's agent turn.
  if (!rec || !rec.url) return "";
  const speed = Number.isFinite(rec.speedup) ? rec.speedup : 16;
  const sizeLabel = Number.isFinite(rec.sizeBytes) && rec.sizeBytes > 0
    ? ` · ${(rec.sizeBytes / (1024 * 1024)).toFixed(1)} MB`
    : "";
  const poster = rec.poster ? ` poster="${escapeAttr(rec.poster)}"` : "";
  return `
    <div class="cycle-recording">
      <div class="cycle-recording-header">
        <strong>Cycle ${turnIndex} · Desktop recording</strong>
        <span class="cycle-recording-meta">${speed}× speed${sizeLabel}</span>
      </div>
      <video class="recording-player" controls preload="metadata" playsinline${poster}>
        <source src="${escapeAttr(rec.url)}" type="video/mp4">
      </video>
    </div>
  `;
}

function renderCheckpointFold(checkpointItem) {
  const detail = checkpointItem.detail === undefined ? "" : `<pre>${escapeHtml(typeof checkpointItem.detail === "string" ? checkpointItem.detail : pretty(checkpointItem.detail))}</pre>`;
  return `
    <details class="check-fold">
      <summary class="check-summary">
        <span>${escapeHtml(checkpointItem.name || "checkpoint")}</span>
        <span>${escapeHtml(checkpointItem.passed ? "pass" : "fail")}</span>
      </summary>
      ${detail}
    </details>
  `;
}

function componentLabel(name) {
  if (name === "answer_supervisor") return "Answer Supervisor";
  if (name === "public_user_simulator") return "Public User Simulator";
  if (name === "feedback_rewriter") return "Feedback Rewriter";
  return name || "Component";
}

function renderSupervisorComponent(name, component) {
  if (!component || !Object.keys(component).length) return "";
  const summaryBits = [];
  if (component.transport) summaryBits.push(component.transport);
  if (typeof component.elapsed_ms === "number" && component.elapsed_ms > 0) {
    summaryBits.push(`${component.elapsed_ms}ms`);
  }
  if (Array.isArray(component.image_inputs) && component.image_inputs.length) {
    summaryBits.push(`${component.image_inputs.length} image(s)`);
  }
  let inputBlock = "";
  const inputWorkspace = component.input_workspace || null;
  const inputReadme = component.input_readme || "";
  const rolePrompt = component.prompt || "";
  if (inputWorkspace || inputReadme) {
    const inputBits = [];
    if (inputWorkspace?.files?.length) inputBits.push(`${inputWorkspace.files.length} file(s)`);
    if (Array.isArray(inputWorkspace?.attached_images) && inputWorkspace.attached_images.length) {
      inputBits.push(`${inputWorkspace.attached_images.length} attached image(s)`);
    }
    if (inputWorkspace?.hidden_references_available) inputBits.push("hidden refs visible");
    if (inputWorkspace && inputWorkspace.supervisor_feedback_available) inputBits.push("supervisor feedback visible");
    inputBlock = `
      <details class="check-fold nested-fold">
        <summary class="check-summary">
          <span>Workspace</span>
          <span>${escapeHtml(inputBits.join(" ｜ ") || "details")}</span>
        </summary>
        ${inputReadme ? `<pre>${escapeHtml(inputReadme)}</pre>` : ""}
        ${inputWorkspace ? `<pre>${escapeHtml(pretty(inputWorkspace))}</pre>` : ""}
      </details>
    `;
  }
  let promptBlock = "";
  if (rolePrompt) {
    const promptLines = String(rolePrompt).split(/\r?\n/).filter(Boolean).length;
    promptBlock = `
      <details class="check-fold nested-fold">
        <summary class="check-summary">
          <span>Role Prompt</span>
          <span>${escapeHtml(`${promptLines} line(s)`)}</span>
        </summary>
        <pre>${escapeHtml(rolePrompt)}</pre>
      </details>
    `;
  }
  return `
    <details class="check-fold">
      <summary class="check-summary">
        <span>${escapeHtml(componentLabel(name))}</span>
        <span>${escapeHtml(summaryBits.join(" ｜ ") || "details")}</span>
      </summary>
      ${promptBlock}
      ${inputBlock}
      <pre>${escapeHtml(pretty(component.decision || component))}</pre>
    </details>
  `;
}

function renderSupervisorCycle(cycle) {
  const blocks = [];
  const decisionEnvelope = cycle.supervision_decision || null;
  const requestedAction = decisionEnvelope?.decision?.requested_action || "";
  const requestedReason = decisionEnvelope?.decision?.requested_reason || "";
  const executorByTurn = activePayload?.usageSummary?.executorByTurn || {};
  const turnKey = String(cycle.evaluation_index || "");
  const cycleTokens = turnKey && executorByTurn[turnKey] ? executorByTurn[turnKey] : null;
  if (cycleTokens) {
    blocks.push(
      `<div class="check-copy"><strong>Executor Tokens</strong><pre>${escapeHtml(`input ${formatTokens(cycleTokens.inputTokens)} ｜ output ${formatTokens(cycleTokens.outputTokens)} ｜ total ${formatTokens(cycleTokens.totalTokens)} ｜ calls ${formatTokens(cycleTokens.callCount)}`)}</pre></div>`,
    );
  }
  if (cycle.attempt_state || typeof cycle.recoverable === "boolean") {
    const stateParts = [];
    if (cycle.attempt_state) stateParts.push(`attempt_state=${cycle.attempt_state}`);
    if (typeof cycle.recoverable === "boolean") stateParts.push(`recoverable=${String(cycle.recoverable)}`);
    if (typeof cycle.remaining_followups === "number") stateParts.push(`remaining_followups=${cycle.remaining_followups}`);
    if (cycle.followup_budget_exhausted) stateParts.push("followup_budget_exhausted=true");
    blocks.push(`<div class="check-copy"><strong>State</strong><pre>${escapeHtml(stateParts.join("\n"))}</pre></div>`);
  }
  if (decisionEnvelope) {
    blocks.push(
      `<div class="check-copy"><strong>Decision JSON</strong><pre>${escapeHtml(pretty(decisionEnvelope))}</pre></div>`,
    );
  }
  if (cycle.rationale) {
    blocks.push(`<div class="check-copy"><strong>Rationale</strong><pre>${escapeHtml(cycle.rationale)}</pre></div>`);
  }
  if (Array.isArray(cycle.missing_artifacts) && cycle.missing_artifacts.length) {
    blocks.push(`<div class="check-copy"><strong>Missing Artifacts</strong><pre>${escapeHtml(cycle.missing_artifacts.join("\n"))}</pre></div>`);
  }
  if (Array.isArray(cycle.guidance_tags) && cycle.guidance_tags.length) {
    blocks.push(`<div class="check-copy"><strong>Guidance Tags</strong><pre>${escapeHtml(cycle.guidance_tags.join("\n"))}</pre></div>`);
  }
  if (cycle.safe_user_feedback) {
    blocks.push(`<div class="check-copy"><strong>Safe User Feedback</strong><pre>${escapeHtml(cycle.safe_user_feedback)}</pre></div>`);
  }
  if (cycle.public_feedback_summary) {
    blocks.push(`<div class="check-copy"><strong>Public Feedback Summary</strong><pre>${escapeHtml(cycle.public_feedback_summary)}</pre></div>`);
  }
  if (Array.isArray(cycle.public_feedback_points) && cycle.public_feedback_points.length) {
    blocks.push(`<div class="check-copy"><strong>Public Feedback Points</strong><pre>${escapeHtml(cycle.public_feedback_points.join("\n"))}</pre></div>`);
  }
  if (cycle.user_simulator_mode === "silent" && cycle.user_simulator_skip_reason) {
    blocks.push(`<div class="check-copy"><strong>User Simulator State</strong><pre>${escapeHtml(`silent (${cycle.user_simulator_skip_reason})`)}</pre></div>`);
  }
  const components = cycle.components || {};
  // Round 9 / B4: highlight failure / infra signal cycles so reviewers
  // jump straight to the problem turn.  Triggered by the supervisor's
  // own verdict / attempt_state OR by signal keywords in the rationale.
  const FAILURE_VERDICTS = new Set(["fail", "infra_error", "rate_limit"]);
  const FAILURE_STATES = new Set(["terminal_failure", "executor_incomplete"]);
  const rationaleLower = String(cycle.rationale || "").toLowerCase();
  const rationaleSignal = ["timeout", "rate limit", "rate_limit", "fallback", "infra_error", "pre_exec", "dispatcher_timeout", "agent_no_response", "review_rejected", "terminal_state_missing"]
    .some((needle) => rationaleLower.includes(needle));
  const isFailureCycle = FAILURE_VERDICTS.has(cycle.verdict)
    || FAILURE_STATES.has(cycle.attempt_state)
    || rationaleSignal;
  const failureClass = isFailureCycle ? " check-fold-failure" : "";
  return `
    <details class="check-fold${failureClass}"${isFailureCycle ? " open" : ""}>
      <summary class="check-summary">
        <span>${escapeHtml(`Cycle ${cycle.evaluation_index || "?"}`)}${isFailureCycle ? ' <span class="badge bad">&#9888; failure signal</span>' : ""}</span>
        <span>${escapeHtml(`${verdictLabel(cycle.verdict)} ｜ ${cycle.attempt_state || "state n/a"} ｜ ${requestedAction || "stop"}${requestedReason ? `:${requestedReason}` : ""} ｜ supervisor ${formatScore(cycle.score)} ｜ ${cycle.confidence || "medium"}`)}</span>
      </summary>
      ${blocks.join("") || `<div class="empty">No supervisor notes recorded.</div>`}
      ${renderSupervisorComponent("answer_supervisor", components.answer_supervisor)}
      ${renderSupervisorComponent("public_user_simulator", components.public_user_simulator)}
      ${renderSupervisorComponent("feedback_rewriter", components.feedback_rewriter)}
      <pre>${escapeHtml(pretty({
        transport: cycle.transport,
        elapsedMs: cycle.elapsed_ms,
        cycleDir: cycle.cycle_dir,
      }))}</pre>
    </details>
  `;
}

function renderSupervisorAssessment(detail) {
  const cycles = Array.isArray(detail?.supervisionTrace) ? detail.supervisionTrace : [];
  if (cycles.length) {
    return cycles.map(renderSupervisorCycle).join("");
  }
  if (detail?.score?.error) {
    return `<pre>${escapeHtml(detail.score.error)}</pre>`;
  }
  const checkpoints = Array.isArray(detail?.score?.checkpoints) ? detail.score.checkpoints : [];
  return checkpoints.map(renderCheckpointFold).join("") || `<div class="empty">No supervisor decisions were recorded.</div>`;
}

function renderGrading(payload) {
  const primaryDetail = selectedAttemptDetail(payload);

  checkpointsEl.innerHTML = "";
  gradingTitleEl.textContent = "Supervisor Assessment";
  gradingNoteEl.textContent = "Supervisor internal reasoning, user simulator status, and continuation prompts";
  const assessmentHtml = renderSupervisorAssessment(primaryDetail);
  checkpointsEl.innerHTML = assessmentHtml.includes("No supervisor decisions were recorded.") && payload.emptyReason
    ? `<div class="empty">${escapeHtml(payload.emptyReason)}</div>`
    : assessmentHtml;
  if (payload.supervisionContext && Object.keys(payload.supervisionContext).length) {
    checkpointsEl.innerHTML += `
      <details class="check-fold">
        <summary class="check-summary">
          <span>Context Snapshot</span>
          <span>redacted</span>
        </summary>
        <pre>${escapeHtml(pretty(payload.supervisionContext))}</pre>
      </details>
    `;
  }
  if (payload.supervisionArtifacts?.length) {
    checkpointsEl.innerHTML += `
      <details class="check-fold">
        <summary class="check-summary">
          <span>Supervisor Artifacts</span>
          <span>${escapeHtml(String(payload.supervisionArtifacts.length))} file(s)</span>
        </summary>
        <div class="artifact-list">
          ${payload.supervisionArtifacts.map((file) => {
            const label = escapeHtml(file.path);
            const link = file.url
              ? `<a href="${escapeAttr(file.url)}" target="_blank" rel="noreferrer">${label}</a>`
              : `<span>${label}</span>`;
            const text = file.text ? `<pre>${escapeHtml(file.text)}</pre>` : "";
            return `<div class="artifact-row">${link}${text}</div>`;
          }).join("")}
        </div>
      </details>
    `;
  }
  if (payload.supervisionLog) {
    checkpointsEl.innerHTML += `
      <details class="check-fold">
        <summary class="check-summary">
          <span>Supervisor Log</span>
          <span>text</span>
        </summary>
        <pre>${escapeHtml(payload.supervisionLog)}</pre>
      </details>
    `;
  }
}

async function loadAttempt(relPath, card) {
  if (!relPath) return;
  activePath = relPath;
  writeHashForPath(relPath);
  activeRunCard = card || activeRunCard;
  document.querySelectorAll(".run-card").forEach((el) => el.classList.remove("active"));
  activeRunCard?.classList.add("active");
  let payload;
  try {
    const response = await fetch(attemptUrl(relPath), { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    payload = await response.json();
  } catch (err) {
    summaryEl.innerHTML = `
      <div class="hero-copy">
        <div class="eyebrow">Attempt Review</div>
        <h2>Trace detail unavailable</h2>
        <p>${escapeHtml(err.message || err)}</p>
      </div>
      <div class="quick-stats"></div>
    `;
    timelineEl.innerHTML = `<div class="empty">No flow available for this static export.</div>`;
    checkpointsEl.innerHTML = `<div class="empty">No supervisor details.</div>`;
    outputsEl.innerHTML = `<div class="empty">No saved results.</div>`;
    return;
  }
  activePayload = payload;
  populateAttemptSelector(payload);
  const rows = filteredRuns();
  renderSummary(payload, rows);
  renderFlow(payload);
  renderExecutionTimeline(payload);
  renderGrading(payload);
  await renderOutputs(payload);
}

// --- Execution Timeline (step-list panel) -----------------------------

function pickTimeline(payload) {
  // Server exposes the raw timeline.json either at top-level (single
  // attempt) or inside each attempt card (multi-attempt runs). Prefer the
  // currently-selected attempt, then fall back to top-level. An empty
  // ``{}`` (from ``read_json`` on a missing file) is treated as no data.
  const details = typeof selectedAttemptDetails === "function" ? selectedAttemptDetails(payload) : [];
  if (Array.isArray(details) && details.length) {
    for (const d of details) {
      const t = d && d.timeline;
      if (t && typeof t === "object" && Array.isArray(t.phases) && t.phases.length) return t;
    }
  }
  const top = payload && payload.timeline;
  if (top && typeof top === "object" && Array.isArray(top.phases) && top.phases.length) return top;
  return null;
}

function formatDurationMs(ms) {
  const n = Number(ms) || 0;
  if (n < 1000) return `${n}ms`;
  const s = n / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 2 : 1)}s`;
  const m = Math.floor(s / 60);
  const rem = s - m * 60;
  return `${m}m${rem.toFixed(rem < 10 ? 1 : 0)}s`;
}

// Map a phase object into one or more flat "step" objects for the step-list.
// An executor phase explodes into its underlying tool_calls; other phases
// become a single step. Each step carries enough state to render a row
// (category / color, label, duration, optional side-annotations).
function flattenTimelinePhases(phases) {
  const steps = [];
  for (const p of phases) {
    if (!p || typeof p !== "object") continue;
    if (p.kind === "executor" && Array.isArray(p.tool_calls) && p.tool_calls.length) {
      // Represent the executor phase itself as a "container" header so the
      // cycle boundary stays visible, then expand each tool_call as a row.
      steps.push({
        kind: "executor",
        category: "executor",
        name: p.name || `cycle_${p.cycle ?? "??"}_executor`,
        start_ms: Number(p.start_ms) || 0,
        end_ms: Number(p.end_ms) || 0,
        cycle: p.cycle,
        isHeader: true,
      });
      for (const tc of p.tool_calls) {
        if (!tc) continue;
        const tcName = String(tc.name || "tool");
        const category = classifyToolCall(tcName);
        steps.push({
          kind: "tool_call",
          category,
          name: tcName,
          agent_id: tc.agent_id && tc.agent_id !== "main" ? tc.agent_id : "",
          start_ms: Number(tc.start_ms) || 0,
          end_ms: Number(tc.end_ms) || 0,
          approximate: !!tc.approximate,
          cycle: p.cycle,
        });
      }
    } else {
      const cat = p.kind === "container_lifecycle" ? "container" : p.kind;
      steps.push({
        kind: p.kind,
        category: cat,
        name: p.name || p.kind || "phase",
        start_ms: Number(p.start_ms) || 0,
        end_ms: Number(p.end_ms) || 0,
        cycle: p.cycle,
        verdict: p.verdict,
        score: p.score,
        skipped: !!p.skipped,
        skip_reason: p.skip_reason,
        errored: !!p.errored,
      });
    }
  }
  steps.sort((a, b) => (a.start_ms || 0) - (b.start_ms || 0));
  return steps;
}

function classifyToolCall(toolName) {
  const n = String(toolName).toLowerCase();
  if (n === "browser" || n.startsWith("browser_") || n.startsWith("mcp_playwright")) return "browser";
  if (n === "read" || n === "read_file" || n === "view_image") return "read";
  if (n === "write" || n === "write_file" || n === "edit") return "write";
  if (n === "exec" || n === "bash" || n === "shell") return "exec";
  if (n.includes("web_search") || n.includes("search")) return "search";
  if (n.includes("duckduckgo")) return "search";
  if (n.includes("process")) return "exec";
  if (n.includes("sessions_spawn") || n.includes("agents_")) return "meta";
  return "tool";
}

function stepIcon(category) {
  switch (category) {
    case "container": return "📦";
    case "executor": return "🎯";
    case "tool_call": return "🔧";
    case "browser": return "🌐";
    case "read": return "📄";
    case "write": return "✏️";
    case "exec": return "⚡";
    case "search": return "🔍";
    case "meta": return "🧠";
    case "supervisor": return "🧑‍⚖️";
    case "user_simulator": return "👤";
    case "artifact": return "📥";
    default: return "•";
  }
}

function stepCategoryLabel(category) {
  switch (category) {
    case "container": return "container";
    case "executor": return "executor";
    case "browser": return "browser";
    case "read": return "read";
    case "write": return "write";
    case "exec": return "exec";
    case "search": return "search";
    case "meta": return "meta";
    case "supervisor": return "supervisor";
    case "user_simulator": return "user sim";
    case "artifact": return "artifact";
    default: return "tool";
  }
}

let _execTimelineState = {
  rawSteps: [],
  maxMs: 1,
  filterText: "",
  totalMs: 0,
  baseMs: 0,
};

function renderExecTimelineSteps() {
  if (!execTimelineBodyEl) return;
  const stepsEl = execTimelineBodyEl.querySelector(".exec-timeline-steps");
  if (!stepsEl) return;
  const filter = (_execTimelineState.filterText || "").toLowerCase().trim();
  const all = _execTimelineState.rawSteps;
  const visible = filter
    ? all.filter((s) => {
        const hay = `${s.name} ${s.category} ${s.kind} ${s.agent_id || ""}`.toLowerCase();
        return hay.includes(filter);
      })
    : all;
  const countEl = execTimelineBodyEl.querySelector(".exec-timeline-count");
  if (countEl) countEl.textContent = filter ? `${visible.length} / ${all.length} steps` : `${all.length} steps`;
  // Anchor every bar against the attempt's full duration: the track is the
  // whole attempt wall-clock, and each step's bar sits at ``left = (start -
  // base) / total`` with ``width = duration / total``. That makes the panel
  // a proper Gantt strip — you can tell at a glance that the first row
  // happened at t=0, a long executor span hogs the middle, and the
  // supervisor sits at the tail, rather than every bar filling its own
  // track with no positional context.
  const baseMs = Number(_execTimelineState.baseMs) || 0;
  const totalMs = Math.max(1, Number(_execTimelineState.totalMs) || 1);
  const chunks = [];
  let seq = 0;
  for (const s of visible) {
    seq += 1;
    const startMs = Number(s.start_ms) || baseMs;
    const endMs = Math.max(Number(s.end_ms) || startMs, startMs);
    const durMs = Math.max(0, endMs - startMs);
    // Offset + width as percentages of the overall attempt window.
    let leftPct = ((startMs - baseMs) / totalMs) * 100;
    let widthPct = (durMs / totalMs) * 100;
    // Clamp into [0, 100]; keep zero-duration spans visible as a hairline.
    if (leftPct < 0) leftPct = 0;
    if (leftPct > 100) leftPct = 100;
    const minWidth = 0.4;
    if (widthPct < minWidth) widthPct = minWidth;
    if (leftPct + widthPct > 100) widthPct = Math.max(minWidth, 100 - leftPct);
    const startOffsetSec = (startMs - baseMs) / 1000;
    const title = [
      s.name,
      `start t+${startOffsetSec >= 0 ? startOffsetSec.toFixed(1) : startOffsetSec.toFixed(2)}s`,
      `dur ${formatDurationMs(durMs)}`,
      s.cycle != null ? `cycle ${s.cycle}` : "",
      s.agent_id ? `agent ${s.agent_id}` : "",
      s.verdict ? `verdict ${s.verdict}` : "",
      s.skipped ? `skipped (${s.skip_reason || "no reason"})` : "",
      s.approximate ? "approximate" : "",
      s.errored ? "errored" : "",
    ].filter(Boolean).join(" · ");
    const approxAttr = s.approximate ? ' data-approximate="true"' : "";
    const skippedAttr = s.skipped ? ' data-skipped="true"' : "";
    const erroredAttr = s.errored ? ' data-errored="true"' : "";
    const headerAttr = s.isHeader ? ' data-header="true"' : "";
    const displayLabel = s.category === "browser" && s.name !== s.category ? `browser: ${s.name.replace(/^browser_/, "").replace(/^browser:?\s*/, "")}` : s.name;
    chunks.push(`
      <div class="exec-step" data-category="${escapeAttr(s.category || "tool")}"${approxAttr}${skippedAttr}${erroredAttr}${headerAttr} title="${escapeAttr(title)}">
        <div class="exec-step-num">${seq}</div>
        <div class="exec-step-accent"></div>
        <div class="exec-step-body">
          <div class="exec-step-head">
            <span class="exec-step-icon" aria-hidden="true">${stepIcon(s.category)}</span>
            <span class="exec-step-name">${escapeHtml(displayLabel)}</span>
            ${s.agent_id ? `<span class="exec-step-agent">${escapeHtml(s.agent_id)}</span>` : ""}
            ${s.cycle != null ? `<span class="exec-step-cycle">c${String(s.cycle).padStart(2, "0")}</span>` : ""}
            <span class="exec-step-dur">${escapeHtml(formatDurationMs(durMs))}</span>
          </div>
          <div class="exec-step-bar">
            <div class="exec-step-bar-fill" style="left:${leftPct.toFixed(3)}%;width:${widthPct.toFixed(3)}%"></div>
          </div>
        </div>
      </div>
    `);
  }
  if (!visible.length) {
    chunks.push(`<div class="exec-timeline-empty">${escapeHtml(filter ? "No steps match this filter." : "No steps recorded yet.")}</div>`);
  }
  stepsEl.innerHTML = chunks.join("");
}

function renderExecutionTimeline(payload) {
  if (!execTimelineBodyEl || !execTimelinePanelEl) return;
  const timeline = pickTimeline(payload);
  if (!timeline) {
    execTimelineBodyEl.innerHTML = `
      <div class="exec-timeline-summary">
        <strong>Execution Timeline</strong>
        <div class="exec-timeline-hint">No timeline recorded for this attempt yet. Data appears as the attempt makes progress.</div>
      </div>
    `;
    _execTimelineState = { rawSteps: [], maxMs: 1, filterText: "", totalMs: 0, baseMs: 0 };
    return;
  }
  const baseMs = Number(timeline.attempt_started_ms) || 0;
  const endMs = Number(timeline.attempt_ended_ms) || baseMs;
  const totalMs = Math.max(1, endMs - baseMs);
  const phases = Array.isArray(timeline.phases) ? timeline.phases : [];
  const steps = flattenTimelinePhases(phases);
  const maxMs = steps.reduce((acc, s) => Math.max(acc, (s.end_ms || 0) - (s.start_ms || 0)), 1);
  const inProgress = !!timeline.in_progress;
  _execTimelineState = {
    rawSteps: steps,
    maxMs,
    filterText: _execTimelineState.filterText || "",
    totalMs,
    baseMs,
  };
  const filterValue = _execTimelineState.filterText;
  execTimelineBodyEl.innerHTML = `
    <div class="exec-timeline-summary">
      <strong>Total ${escapeHtml(formatDurationMs(totalMs))}</strong>
      <span class="exec-timeline-status" data-in-progress="${inProgress ? "true" : "false"}">${inProgress ? "in progress" : "finished"}</span>
    </div>
    <div class="exec-timeline-controls">
      <input type="search" class="exec-timeline-filter" placeholder="Filter steps…" value="${escapeAttr(filterValue)}" />
      <span class="exec-timeline-count">${steps.length} steps</span>
    </div>
    <div class="exec-timeline-steps"></div>
  `;
  const filterInput = execTimelineBodyEl.querySelector(".exec-timeline-filter");
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      _execTimelineState.filterText = String(e.target.value || "");
      renderExecTimelineSteps();
    });
  }
  renderExecTimelineSteps();
}

function bindExecutionTimelineToggle() {
  if (!execTimelineToggleEl || !execTimelinePanelEl) return;
  // ``index.js`` rebuilds the trace layout (``root.innerHTML = LAYOUT_HTML``)
  // on every mount, so after the user visits Results/Tasks and returns the
  // toggle is a BRAND-NEW element. A module-level "already bound" guard left
  // the click handler attached to the stale, detached node, so the
  // Execution Timeline panel could no longer be opened.
  // Guard per-element via a data flag instead so each fresh toggle gets its
  // own listener while a re-mount of the same node stays idempotent.
  if (execTimelineToggleEl.dataset.toggleBound === "1") return;
  execTimelineToggleEl.dataset.toggleBound = "1";
  execTimelineToggleEl.addEventListener("click", () => {
    const collapsed = execTimelinePanelEl.classList.toggle("collapsed");
    execTimelineToggleEl.setAttribute("aria-expanded", collapsed ? "false" : "true");
  });
}

async function refreshCurrentData() {
  if (!refreshFabEl) return;
  refreshFabEl.classList.add("loading");
  // Guarantee the user sees at least one full spin even if the fetch is fast.
  const minSpin = new Promise((resolve) => setTimeout(resolve, 850));
  try {
    const response = await fetch(runsIndexUrl({ refresh: true }), { cache: "no-cache" });
    const payload = await response.json();
    allRuns = unpackRunsIndex(payload);
    // Refresh filter dropdown option lists (preserve user selections) without
    // re-binding listeners, so repeated refreshes don't stack handlers.
    const backends = [...new Set(allRuns.map((run) => run.backend).filter(Boolean))]
      .sort((a, b) => {
        const ia = BACKEND_ORDER.indexOf(a);
        const ib = BACKEND_ORDER.indexOf(b);
        if (ia === -1 && ib === -1) return a.localeCompare(b);
        if (ia === -1) return 1;
        if (ib === -1) return -1;
        return ia - ib;
      });
    setOptions(filterBackendEl, backends);
    syncModelOptions();
    renderRunList();
  } catch (err) {
    console.error("refresh failed", err);
  } finally {
    await minSpin;
    refreshFabEl.classList.remove("loading");
  }
}

// One-shot listeners outlive the trace layout, so guard them so they
// no-op while the user is on /results or /tasks.
let listenersBound = false;

function bindGlobalListeners() {
  if (listenersBound) return;
  listenersBound = true;
  window.addEventListener("hashchange", () => {
    if (!String(location.hash || "").startsWith("#/trace")) return;
    const target = hashToPath();
    if (!target || target === activePath) return;
    const targetRunPath = parentRunPath(target);
    if (applyFiltersForPath(allRuns, target)) {
      activePath = target;
      saveStoredFilters();
      renderRunList();
      return;
    }
    const card = [...document.querySelectorAll(".run-card")].find((el) => el.dataset.path === targetRunPath || el.dataset.path === target);
    loadAttempt(target, card);
  });
}

let initialFetchDone = false;

export async function bootTrace() {
  bindDom();
  bindExecutionTimelineToggle();
  setupFlowFilters();
  attemptSelectEl?.addEventListener("change", () => {
    const relPath = String(attemptSelectEl.value || "").trim();
    if (!relPath || relPath === activePath) return;
    loadAttempt(relPath, activeRunCard);
  });
  // The shell's main.js owns the FAB click; we expose ``refreshTrace``
  // for it to call so the legacy refresh logic stays self-contained.
  bindGlobalListeners();
  // Keep filters aligned with the current trace hash before option
  // restoration. Static exports use opaque public paths such as ``r/run-*``;
  // those need the runs index to recover backend/model rather than guessing
  // from the first path segment.
  activePath = hashToPath();
  if (!initialFetchDone) {
    initialFetchDone = true;
    const response = await fetch(runsIndexUrl());
    const payload = await response.json();
    allRuns = unpackRunsIndex(payload);
    initFilters(allRuns);
  } else {
    initFilters(allRuns);
  }
  renderRunList();
}

export async function refreshTrace() {
  await refreshCurrentData();
}
