// Home page — paper-aligned overview plus live/static benchmark highlights.

import { getJSON, invalidate } from "../lib/api.js";
import { h, clear } from "../lib/dom.js";
import { displayModelName, pct, score, duration, tokens as tokenCount, categoryLabel } from "../lib/format.js";
import { writeHash } from "../lib/router.js";
import { registerPageRefresh } from "../lib/refresh.js";

const PAPER_FIGURES = {
  method: "assets/paper/three_role_strategy_web.png",
  coverage: "assets/paper/statistics_heatmaps_combined_wide_web.png",
  tokens: "assets/paper/token_and_user_web.png",
};
const DEMO_ASSET_VERSION = "demo_20260703_1";

const RESOURCE_LINKS = [
  { label: "Project Page", icon: "🌐", href: "https://uniclawbench.github.io", tone: "project" },
  { label: "Code", icon: "⌘", href: "https://github.com/HKU-MMLab/UniClawBench", tone: "code" },
  { label: "arXiv", icon: "📄", href: "#", tone: "arxiv" },
  { label: "Daily Paper", icon: "🤗", href: "#", tone: "daily" },
];

const LEADERBOARD_PALETTE = [
  ["#1f6f5f", "rgba(31,111,95,0.42)", "rgba(31,111,95,0.1)"],
  ["#b97a2c", "rgba(185,122,44,0.4)", "rgba(185,122,44,0.1)"],
  ["#2c6f8a", "rgba(44,111,138,0.4)", "rgba(44,111,138,0.1)"],
  ["#7a4f8a", "rgba(122,79,138,0.4)", "rgba(122,79,138,0.1)"],
  ["#a44a3f", "rgba(164,74,63,0.42)", "rgba(164,74,63,0.1)"],
  ["#4a6a52", "rgba(74,106,82,0.45)", "rgba(74,106,82,0.1)"],
];

const DEMO_CASES = [
  {
    title: "Receipt GUI Reconciliation",
    taskId: "task_205_36_receipt_packet_gui_audit",
    capability: "Cross-Platform · ZH",
    status: "pass",
    backend: "openclaw",
  },
  {
    title: "PyPI Upgrade Web Audit",
    taskId: "task_205_40_pypi_upgrade_web_audit",
    capability: "Cross-Platform · ZH",
    status: "pass",
    backend: "openclaw",
  },
  {
    title: "RAG Evaluation GUI Stack",
    taskId: "task_205_07_rag_evaluation_gui_full_stack",
    capability: "Cross-Platform · ZH",
    status: "budget_exhausted",
    backend: "openclaw",
  },
  {
    title: "Rust Meetup Calendar",
    taskId: "task_205_03_rust_tokyo_meetup_gui_calendar",
    capability: "Cross-Platform · ZH",
    status: "budget_exhausted",
    backend: "nanobot",
  },
  {
    title: "Screen Web Compare",
    taskId: "task_105_16_screen_web_compare",
    capability: "Cross-Platform",
    status: "pass",
    backend: "openclaw",
  },
];

let lastRoute = null;
let mountGeneration = 0;
let carouselIndex = 0;
let homeLeaderboardMode = "model";
const demoMediaCache = new Map();
const demoDetailCache = new Map();

function aggregateUrl(refresh = false) {
  const staticFile = typeof window !== "undefined" && window.CLAWBENCH_STATIC_DATA;
  if (staticFile) return refresh ? cacheBust(staticFile) : staticFile;
  return refresh ? "/api/aggregate?refresh=1" : "/api/aggregate";
}

function tasksUrl(refresh = false) {
  const staticFile = typeof window !== "undefined" && window.CLAWBENCH_STATIC_TASKS;
  if (staticFile) return refresh ? cacheBust(staticFile) : staticFile;
  return refresh ? "/api/tasks?refresh=1" : "/api/tasks";
}

function runsUrl(refresh = false) {
  const staticFile = typeof window !== "undefined" && window.CLAWBENCH_STATIC_RUNS;
  if (staticFile) return refresh ? cacheBust(staticFile) : staticFile;
  return refresh ? "/api/runs?slim=1&refresh=1" : "/api/runs?slim=1";
}

function demoManifestUrl(refresh = false) {
  const url = "assets/demo/manifest.json";
  return refresh ? cacheBust(url) : `${url}?v=${DEMO_ASSET_VERSION}`;
}

function cacheBust(url) {
  return url + (url.includes("?") ? "&" : "?") + "_=" + Date.now();
}

export async function mount(root, route) {
  lastRoute = route;
  const generation = ++mountGeneration;
  clear(root);
  const page = h("div.home-page", [
    buildHero(),
    h("section.home-section.home-loading", h("div.loading-stub", "Loading task catalog…")),
  ]);
  root.appendChild(page);

  try {
    const [tasksPayload, demoManifest] = await Promise.all([
      getJSON(tasksUrl()),
      loadDemoManifest(),
    ]);
    if (generation !== mountGeneration) return;
    clear(page);
    const tasks = tasksPayload.tasks || [];
    let heroSection = buildHero({}, tasks, []);
    let leaderboardSection = buildLeaderboardSection(null);
    let dataSection = buildDataSection(tasks, {});
    page.appendChild(heroSection);
    page.appendChild(buildDemoSection(tasks, [], demoManifest));
    page.appendChild(leaderboardSection);
    page.appendChild(buildMethodsSection());
    page.appendChild(dataSection);
    page.appendChild(buildRuntimeSection());

    getJSON(aggregateUrl()).then((aggregate) => {
      if (generation !== mountGeneration) return;
      const nextHero = buildHero(aggregate, tasks, []);
      const nextLeaderboard = buildLeaderboardSection(aggregate);
      const nextData = buildDataSection(tasks, aggregate);
      heroSection.replaceWith(nextHero);
      leaderboardSection.replaceWith(nextLeaderboard);
      dataSection.replaceWith(nextData);
      heroSection = nextHero;
      leaderboardSection = nextLeaderboard;
      dataSection = nextData;
    }).catch((err) => {
      if (generation !== mountGeneration) return;
      const warning = h("div.home-inline-warning", `Leaderboard data is still warming: ${err.message || err}`);
      leaderboardSection.querySelector(".home-section-head")?.appendChild(warning);
    });
  } catch (err) {
    const loading = page.querySelector(".home-loading");
    if (loading) {
      clear(loading);
      loading.appendChild(h("div.error-stub", `Failed to load home data: ${err.message || err}`));
    }
  }
}

async function refreshHomeLikeRoute() {
  invalidate(aggregateUrl());
  invalidate(tasksUrl());
  invalidate(demoManifestUrl());
  await Promise.all([
    getJSON(aggregateUrl(true), { refresh: true, noStore: Boolean(window.CLAWBENCH_STATIC_DATA) }),
    getJSON(tasksUrl(true), { refresh: true, noStore: Boolean(window.CLAWBENCH_STATIC_TASKS) }),
    loadDemoManifest(true),
  ]);
  if (lastRoute) await mount(document.getElementById("page-root"), lastRoute);
}

registerPageRefresh("home", refreshHomeLikeRoute);

async function loadDemoManifest(refresh = false) {
  try {
    return await getJSON(demoManifestUrl(refresh), { noStore: refresh });
  } catch {
    return null;
  }
}

function buildHero(aggregate = {}, tasks = [], runs = []) {
  const taskCount = uniqueTasks(tasks, aggregate);
  const passRate = passRateFromRows(aggregate.rows || runs);
  const leaders = topLeaderboardHighlights(aggregate);
  return h("section.home-hero", [
    h("div.home-hero-copy", [
      h("div.eyebrow", "Capability-driven benchmark for proactive agents"),
      h("h1", "UniClawBench"),
      h("p", "A bilingual benchmark for tool-using agents across skill usage, exploration, long-context reasoning, multimodal understanding, and cross-platform coordination, covering 10 models and 3 harness platforms."),
      h("div.home-hero-actions", [
        actionLink("Leaderboard", "#/leaderboard/model", "primary"),
        actionLink("Trace", "#/trace"),
        actionLink("Tasks", "#/tasks"),
      ]),
      h("div.home-resource-links", RESOURCE_LINKS.map((link) => resourceLink(link))),
    ]),
    h("div.home-hero-panel", [
      h("div.home-hero-stats", [
        statTile(taskCount || 400, "Tasks"),
        statTile("5", "Capabilities"),
        statTile("EN / ZH", "Languages"),
        statTile(passRate == null ? "—" : pct(passRate, { digits: 0 }), "Avg PR"),
      ]),
      leaderMiniCard(leaders),
    ]),
  ]);
}

function actionLink(label, href, tone = "") {
  const el = h("a.home-action", { href }, [h("span", label), h("span.home-link-arrow", { "aria-hidden": "true" }, "→")]);
  if (tone) el.classList.add(tone);
  return el;
}

function resourceLink(link) {
  const label = link?.label || "Resource";
  const disabled = !link?.href || link.href === "#";
  const attrs = {
    href: link?.href || "#",
    "aria-label": label,
    class: `home-resource-badge ${link?.tone || ""}${disabled ? " pending" : ""}`.trim(),
  };
  if (disabled) {
    attrs["aria-disabled"] = "true";
    attrs.title = `${label} link pending`;
    attrs.onclick = (event) => event.preventDefault();
  }
  if (attrs.href !== "#") {
    attrs.target = "_blank";
    attrs.rel = "noopener";
  }
  if (link?.value) {
    return h("a", attrs, [
      h("span.home-resource-label", label),
      h("span.home-resource-value", link.value),
    ]);
  }
  return h("a", attrs, [
    h("span.home-resource-icon", { "aria-hidden": "true" }, link?.icon || "↗"),
    h("span", label),
  ]);
}

function statTile(value, label) {
  return h("div.home-stat-tile", [
    h("strong", value),
    h("span", label),
  ]);
}

function topLeaderboardHighlights(aggregate) {
  if (!aggregate || (!Array.isArray(aggregate.rows) && !Array.isArray(aggregate.models) && !Array.isArray(aggregate.backends))) {
    return { model: null, harness: null };
  }
  const model = prepareLeaderboardRows(aggregate)[0] || null;
  const harness = prepareHarnessRows(aggregate)[0] || null;
  return {
    model: model ? {
      name: displayModelName(model.label || model.key),
      harness: leaderHarnessForModel(aggregate, model),
    } : null,
    harness: harness ? {
      name: backendDisplayName(harness.label || harness.key),
    } : null,
  };
}

function leaderMiniCard(leaders) {
  const model = leaders?.model;
  const harness = leaders?.harness;
  return h("div.home-leader-mini", [
    leaderMiniRow("🥇", "Top model", model?.name || "Pending runs", model?.harness || ""),
    leaderMiniRow("🥇", "Top harness", harness?.name || "Pending runs", ""),
  ]);
}

function leaderMiniRow(icon, label, name, sub) {
  return h("div.home-leader-mini-row", [
    h("span.home-leader-mini-medal", { "aria-hidden": "true" }, icon),
    h("span.home-leader-mini-label", label),
    h("strong", name),
    sub ? h("small", `(${sub})`) : null,
  ]);
}

function buildMethodsSection() {
  return h("section.home-section.home-method-grid", [
    h("div.home-section-copy", [
      h("div.eyebrow", "Evaluation design"),
      h("h2", "Closed-loop tasks without leaking hidden rubrics"),
      h("p", "The executor works only with public task inputs. A hidden supervisor evaluates fine-grained checkpoints, while a user simulator receives only a coarse progress signal and visible trajectory before returning sanitized feedback."),
      h("div.home-role-strip", [
        roleChip("Executor", "Public tools and task package"),
        roleChip("Supervisor", "Private checkpoints and rubric signals"),
        roleChip("User Simulator", "Visible trajectory and coarse status"),
      ]),
    ]),
    figureCard(PAPER_FIGURES.method, "Three-role closed-loop evaluation strategy", "method"),
  ]);
}

function roleChip(label, note) {
  return h("div.role-chip", [h("strong", label), h("span", note)]);
}

function buildDataSection(tasks, aggregate) {
  const counts = capabilityCounts(tasks);
  return h("section.home-section", [
    h("div.home-section-head", [
      h("div", [
        h("div.eyebrow", "Benchmark composition"),
        h("h2", "Bilingual tasks organized by capability bottleneck"),
      ]),
      h("a.home-inline-link", { href: "#/tasks" }, ["Open tasks", h("span.home-link-arrow", { "aria-hidden": "true" }, "→")]),
    ]),
    h("div.home-data-grid", [
      h("div.home-chart-card", [
        h("h3", "Task families"),
        h("div.home-bars", counts.map((row) => capabilityBar(row, counts))),
      ]),
      figureCard(PAPER_FIGURES.coverage, "Input/output diversity and application-domain coverage", "wide"),
      h("div.home-chart-card.compact", [
        h("h3", "Experiment scope"),
        h("div.home-facts", [
          fact("10 × 400", "OpenClaw model comparison"),
          fact("2 × 3 × 400", "Cross-framework subset in this run set"),
          fact(String((aggregate.all_backends || []).length || 3), "Harnesses represented"),
          fact("2 follow-ups", "Maximum user-simulator cycles"),
        ]),
      ]),
    ]),
  ]);
}

function capabilityBar(row, rows) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return h("div.home-bar-row", [
    h("span", row.label),
    h("div.home-bar-track", h("div.home-bar-fill", { style: { width: `${(row.count / max) * 100}%` } })),
    h("strong", String(row.count)),
  ]);
}

function fact(value, label) {
  return h("div.home-fact", [h("strong", value), h("span", label)]);
}

function buildLeaderboardSection(aggregate) {
  if (!aggregate) {
    return h("section.home-section", [
      h("div.home-section-head", [
        h("div", [
          h("div.eyebrow", "Current run snapshot"),
          h("h2", "Leaderboard excerpt"),
        ]),
        h("a.home-inline-link", { href: "#/leaderboard/model" }, ["Full leaderboard", h("span.home-link-arrow", { "aria-hidden": "true" }, "→")]),
      ]),
      h("div.home-leaderboard-card.compact", h("div.loading-stub", "Preparing leaderboard…")),
    ]);
  }
  const rowSets = {
    model: prepareLeaderboardRows(aggregate),
    backend: prepareHarnessRows(aggregate),
  };
  const rowsSlot = h("div.home-leaderboard");
  const fullLink = h("a.home-inline-link", { href: `#/leaderboard/${homeLeaderboardMode}` }, ["Full leaderboard", h("span.home-link-arrow", { "aria-hidden": "true" }, "→")]);
  const toggles = {
    model: h("button.home-leader-toggle", { type: "button" }, "Model"),
    backend: h("button.home-leader-toggle", { type: "button" }, "Harness"),
  };
  const render = (mode) => {
    homeLeaderboardMode = mode;
    fullLink.href = `#/leaderboard/${mode}`;
    for (const [key, button] of Object.entries(toggles)) {
      button.classList.toggle("active", key === mode);
      button.setAttribute("aria-pressed", key === mode ? "true" : "false");
    }
    clear(rowsSlot);
    const rows = rowSets[mode] || [];
    const sub = mode === "backend" ? "backend" : "model";
    rowsSlot.append(...(rows.length
      ? rows.map((row, idx) => leaderboardRow(row, idx, sub))
      : [h("div.results-empty", "No leaderboard rows yet.")]));
  };
  toggles.model.addEventListener("click", () => render("model"));
  toggles.backend.addEventListener("click", () => render("backend"));
  render(homeLeaderboardMode);
  return h("section.home-section", [
    h("div.home-section-head", [
      h("div", [
        h("div.eyebrow", "Current run snapshot"),
        h("h2", "Leaderboard excerpt"),
      ]),
      h("div.home-leaderboard-tools", [
        h("div.home-leader-switch", [toggles.model, toggles.backend]),
        fullLink,
      ]),
    ]),
    h("div.home-leaderboard-card.compact", rowsSlot),
  ]);
}

function leaderboardRow(row, idx, sub = "model") {
  const total = row.total || {};
  const passRate = total.pass_rate;
  const avgScore = total.avg_score;
  const [base, soft, bg] = LEADERBOARD_PALETTE[idx % LEADERBOARD_PALETTE.length];
  return h("button.home-leader-row", {
    type: "button",
    onclick: () => writeHash({ page: "leaderboard", sub }),
    style: { "--row-base": base, "--row-soft": soft, "--row-bg": bg },
  }, [
    leaderboardRank(idx, sub),
    h("span.home-model", sub === "model" ? displayModelName(row.label || row.key) : backendDisplayName(row.label || row.key)),
    h("span.home-leader-bars", [
      homeMetricBar(passRate, "pass"),
      homeMetricBar(avgScore, "score"),
    ]),
    h("span.home-pr", passRate == null ? "—" : pct(passRate, { digits: 0 })),
    h("span.home-as", avgScore == null ? "—" : score(avgScore, { digits: 2 })),
  ]);
}

function leaderboardRank(idx, sub = "model") {
  const medals = ["🥇", "🥈", "🥉"];
  const showMedal = sub === "model" ? idx < medals.length : idx === 0;
  return h("span.home-rank", [
    showMedal ? h("span.home-medal", { "aria-label": `rank ${idx + 1}` }, medals[idx]) : null,
    h("span.home-rank-number", String(idx + 1)),
  ]);
}

function homeMetricBar(value, kind) {
  const width = value == null ? 0 : Math.max(0, Math.min(100, Number(value) * 100));
  return h(`i.home-leader-bar.${kind}`, h("b", { style: { width: `${width}%` } }));
}

function buildDemoSection(tasks, runs, manifest = null) {
  const taskById = new Map(tasks.map((task) => [task.task_id, task]));
  const manifestItems = Array.isArray(manifest?.items) ? manifest.items.map(normalizeDemoManifestItem).filter((item) => item.taskId) : [];
  const manifestByTask = new Map(manifestItems.map((item) => [item.taskId, item]));
  const baseItems = manifestItems.length ? manifestItems : DEMO_CASES;
  const demos = baseItems.map((item) => ({
    ...item,
    ...(manifestItems.length ? {} : normalizeDemoManifestItem(manifestByTask.get(item.taskId))),
    task: taskById.get(item.taskId),
    run: item.traceUrl ? null : selectDemoRun(item, runs),
  }));
  carouselIndex = Math.min(carouselIndex, demos.length - 1);
  const frame = h("div.demo-frame");
  const dots = h("div.demo-dots");
  const move = (delta) => {
    if (!demos.length) return;
    carouselIndex = (carouselIndex + demos.length + delta) % demos.length;
    renderSlide();
  };
  const renderSlide = () => {
    clear(frame);
    clear(dots);
    const slide = demoSlide(demos[carouselIndex]);
    frame.appendChild(slide);
    hydrateDemoMedia(demos[carouselIndex], slide.querySelector(".demo-media"), () => move(1));
    hydrateDemoDetails(demos[carouselIndex], slide.querySelector(".demo-run-summary"));
    demos.forEach((_, idx) => {
      const dot = h("button.demo-dot", { type: "button", title: `Demo ${idx + 1}` });
      if (idx === carouselIndex) dot.classList.add("active");
      dot.addEventListener("click", () => {
        carouselIndex = idx;
        renderSlide();
      });
      dots.appendChild(dot);
    });
  };
  renderSlide();
  return h("section.home-section", { id: "home-demo" }, [
    h("div.home-section-head", [
      h("div", [
        h("div.eyebrow", "Demo recording queue"),
        h("h2", "Curated demo trajectories"),
      ]),
      h("a.home-inline-link", { href: "#/tasks" }, ["Task catalog", h("span.home-link-arrow", { "aria-hidden": "true" }, "→")]),
    ]),
    h("div.demo-frame-shell", [
      h("button.demo-nav.demo-nav-left", { type: "button", "aria-label": "Previous demo", onclick: () => move(-1) }, "‹"),
      frame,
      h("button.demo-nav.demo-nav-right", { type: "button", "aria-label": "Next demo", onclick: () => move(1) }, "›"),
    ]),
    dots,
  ]);
}

function demoSlide(item) {
  const run = item.run || {};
  const task = item.task || {};
  const status = run.finalStatus || item.finalStatus || item.status;
  const detailSlot = h("div.demo-run-summary", buildDemoRunSummary(item, null));
  return h("div.demo-slide", [
    h("div.demo-media", h("div.demo-media-empty", [
      h("strong", run.summaryPath ? "Loading media preview" : "Pending demo run"),
      h("span", run.summaryPath ? "Trace media is being resolved." : "This case is queued for isolated re-run."),
    ])),
    h("div.demo-copy", [
      h("div.demo-kicker", `${item.capability} · ${statusLabel(status)}`),
      h("h3", item.title),
      h("p.demo-prompt", item.prompt || task.prompt_preview || "Prompt preview unavailable in this export."),
      detailSlot,
    ]),
  ]);
}

function selectDemoRun(item, runs) {
  const candidates = (runs || []).filter((run) => {
    if (run.taskId !== item.taskId) return false;
    if (item.backend && run.backend !== item.backend) return false;
    return true;
  });
  if (!candidates.length) return null;
  const expectedModel = displayModelName(item.model || "");
  const modelMatched = expectedModel
    ? candidates.filter((run) => displayModelName(run.model || run.modelSlug || "") === expectedModel)
    : candidates;
  const scoped = expectedModel ? modelMatched : candidates;
  if (!scoped.length) return null;
  const exact = (item.status || item.finalStatus)
    ? scoped.filter((run) => run.finalStatus === (item.status || item.finalStatus))
    : scoped;
  return [...(exact.length ? exact : scoped)].sort((a, b) => Number(b.finalScore ?? -1) - Number(a.finalScore ?? -1))[0];
}

async function hydrateDemoMedia(item, slot, onEnded = null) {
  if (item?.video || item?.image) {
    clear(slot);
    slot.appendChild(buildMedia({ video: item.video, image: item.poster || item.image }, item.title, onEnded));
    return;
  }
  const relPath = item?.run?.summaryPath;
  if (!slot || !relPath) return;
  try {
    const media = await demoMediaForRun(relPath);
    if (item.run.summaryPath !== relPath) return;
    clear(slot);
    slot.appendChild(buildMedia(media, item.title, onEnded));
  } catch {
    clear(slot);
    slot.appendChild(h("div.demo-media-empty", "Media preview unavailable"));
  }
}

function normalizeDemoManifestItem(item) {
  if (!item) return {};
  const finalStatus = item.finalStatus || item.final_status || item.status;
  return {
    taskId: item.taskId || item.task_id,
    title: item.title,
    capability: item.capability,
    video: item.video,
    image: item.image,
    poster: item.poster,
    prompt: item.prompt || item.prompt_preview,
    status: finalStatus,
    finalStatus,
    runtimeMs: item.runtimeMs || item.runtime_ms,
    score: item.score ?? item.finalScore ?? item.final_score,
    inputTokens: item.inputTokens ?? item.input_tokens,
    outputTokens: item.outputTokens ?? item.output_tokens,
    cycles: item.cycles ?? item.cycleCount ?? item.cycle_count,
    backend: item.backend,
    model: item.model,
    artifactUrl: item.artifactUrl || item.artifact_url,
    traceUrl: item.traceUrl || item.trace_url || item.detailsUrl || item.details_url,
  };
}

async function hydrateDemoDetails(item, slot) {
  const relPath = item?.run?.summaryPath;
  if (!slot) return;
  if (!item?.traceUrl && !relPath) {
    clear(slot);
    slot.appendChild(buildDemoRunSummary(item, null));
    return;
  }
  try {
    const payload = item?.traceUrl ? await getJSON(item.traceUrl) : await demoAttemptForRun(relPath);
    if (relPath && item.run.summaryPath !== relPath) return;
    clear(slot);
    slot.appendChild(buildDemoRunSummary(item, payload));
  } catch {
    clear(slot);
    slot.appendChild(buildDemoRunSummary(item, null));
  }
}

function demoAttemptForRun(relPath) {
  if (demoDetailCache.has(relPath)) return demoDetailCache.get(relPath);
  const promise = getJSON(attemptUrl(relPath));
  demoDetailCache.set(relPath, promise);
  return promise;
}

function buildDemoRunSummary(item, payload) {
  const usage = payload?.usageSummary || {};
  const task = item.task || {};
  const run = item.run || {};
  const scoreValue = firstNumber(
    item.score,
    run.finalScore,
    payload?.taskSummary?.finalScore,
    payload?.taskSummary?.score,
    payload?.score?.capped_score,
    payload?.score?.overall_score,
    payload?.score?.final_completion_score,
  );
  const status = payload?.taskSummary?.finalStatus || run.finalStatus || item.finalStatus || item.status;
  const cycles = firstNumber(item.cycles, countDemoCycles(payload));
  const inputTokens = firstNumber(item.inputTokens, usage.executorInputTokens, usage.agentInputTokens, run.promptTokens, run.prompt_tokens);
  const outputTokens = firstNumber(item.outputTokens, usage.executorOutputTokens, usage.agentOutputTokens, run.completionTokens, run.completion_tokens);
  const runtimeMs = firstNumber(payload?.taskSummary?.runtimeMs, payload?.taskSummary?.runtime_ms, item.runtimeMs, run.runtimeMs, run.runtime_ms);
  const model = displayModelName(item.model || run.model || run.modelSlug || "");
  const summary = h("div.demo-run-card", [
    h("div.demo-info-row.demo-info-topline", [
      metricMini("Category", categoryLabel(task.category || run.category || item.capability || "")),
      metricMini("Model", model || "model n/a"),
      metricMini("Harness", item.backend || run.backend || "harness n/a"),
    ]),
    h("div.demo-info-row.demo-info-result", [
      metricMini("Result", statusLabel(status)),
      metricMini("Score", scoreValue == null ? "—" : score(scoreValue, { digits: 2 })),
    ]),
    h("div.demo-info-row.demo-info-metrics", [
      metricMini("Input", tokenCount(inputTokens)),
      metricMini("Output", tokenCount(outputTokens)),
      metricMini("Turns", cycles == null ? "—" : String(cycles)),
      metricMini("Time", runtimeMs == null ? "—" : duration(runtimeMs)),
    ]),
  ]);
  const actions = h("div.demo-run-actions", [
    payload ? demoAction("Trace", "button", () => showDemoInspector(item, payload)) : demoAction("Trace", "button", null, true),
    demoAction("Task", `#/tasks/${encodeURIComponent(item.taskId)}`),
    item.artifactUrl ? demoAction("Asset", item.artifactUrl) : null,
  ]);
  return h("div", [summary, actions]);
}

function metricMini(label, value) {
  return h("div.demo-run-metric", [h("span", label), h("strong", value || "—")]);
}

function demoAction(label, target, onclick = null, disabled = false) {
  if (target === "button") {
    return h("button.demo-action", { type: "button", onclick, disabled }, [label, h("span", { "aria-hidden": "true" }, "↗")]);
  }
  return h("a.demo-action", { href: target }, [label, h("span", { "aria-hidden": "true" }, "↗")]);
}

function firstNumber(...values) {
  for (const value of values) {
    if (value === null || value === undefined || value === "") continue;
    const numeric = Number(value);
    if (!Number.isNaN(numeric)) return numeric;
  }
  return null;
}

function countDemoCycles(payload) {
  const detail = selectedAttemptDetail(payload);
  const counts = [];
  if (Array.isArray(detail?.supervisionTrace)) counts.push(detail.supervisionTrace.length);
  if (Array.isArray(payload?.supervisionTrace)) counts.push(payload.supervisionTrace.length);
  if (Array.isArray(detail?.continuations)) counts.push(1 + detail.continuations.length);
  if (Array.isArray(detail?.continuationTrace)) counts.push(detail.continuationTrace.length);
  const userTurns = demoFlowEvents(payload, { showTools: false }).filter((event) => event.kind === "user").length;
  if (userTurns) counts.push(userTurns);
  if (counts.length) return Math.max(...counts.filter(Boolean));
  if (Array.isArray(payload?.attemptCards)) return payload.attemptCards.length;
  return null;
}

function showDemoInspector(item, payload) {
  document.querySelector(".demo-inspector")?.remove();
  const status = payload?.taskSummary?.finalStatus || item.run?.finalStatus || item.finalStatus || item.status;
  const title = item.title || item.task?.title || item.taskId;
  let showTools = false;
  const flowSlot = h("div.demo-trace-flow-slot");
  const timelineToggle = h("button.demo-tool-toggle", { type: "button", "aria-pressed": "false" }, "Timeline");
  const toolToggle = h("button.demo-tool-toggle", { type: "button", "aria-pressed": "false" }, "Tool calls");
  const panel = h("aside.demo-inspector", [
    h("button.demo-inspector-close.demo-inspector-close-float", { type: "button", "aria-label": "Close pinned trace" }, "×"),
    h("div.demo-inspector-head", [
      h("div", [h("span", "Pinned demo trace"), h("strong", title)]),
      h("button.demo-inspector-close", { type: "button", "aria-label": "Close pinned trace" }, "×"),
    ]),
    h("div.demo-inspector-toolbar", [
      h("div.demo-inspector-meta", [
        pill(statusLabel(status)),
        pill(displayModelName(item.run?.model || item.run?.modelSlug || item.model || "")),
        pill(item.backend || item.run?.backend || "harness n/a"),
      ]),
      h("div.demo-inspector-controls", [toolToggle, timelineToggle]),
    ]),
    h("div.demo-inspector-shell", [
      h("div.demo-inspector-main", [
        h("div.demo-inspector-section-head", [
          h("h4", "Trace"),
          h("span", "Task input, agent output, and supervisor decisions"),
        ]),
        flowSlot,
        h("div.demo-inspector-links", [
          demoAction("Task", `#/tasks/${encodeURIComponent(item.taskId)}`),
        ]),
      ]),
      h("aside.demo-inspector-timeline", [
        h("div.demo-inspector-section-head", [
          h("h4", "Execution Timeline"),
          h("span", "Gantt view of recorded phases"),
        ]),
        buildDemoTimelineGantt(payload),
      ]),
    ]),
  ]);
  const renderFlow = () => {
    clear(flowSlot);
    flowSlot.appendChild(buildTraceConversation(payload, { showTools }));
  };
  renderFlow();
  toolToggle.addEventListener("click", () => {
    showTools = !showTools;
    toolToggle.classList.toggle("active", showTools);
    toolToggle.setAttribute("aria-pressed", showTools ? "true" : "false");
    renderFlow();
  });
  timelineToggle.addEventListener("click", () => {
    const open = !panel.classList.contains("timeline-open");
    panel.classList.toggle("timeline-open", open);
    timelineToggle.classList.toggle("active", open);
    timelineToggle.setAttribute("aria-pressed", open ? "true" : "false");
  });
  panel.querySelectorAll(".demo-inspector-close").forEach((button) => {
    button.addEventListener("click", () => panel.remove());
  });
  document.body.appendChild(panel);
}

function buildTraceConversation(payload, options = {}) {
  const turns = demoTurnGroups(payload, options);
  if (!turns.length) return h("div.demo-preview-empty", "No executor conversation was recorded for this attempt.");
  return h("div.demo-trace-flow", turns.map((turn) => buildDemoTurnBlock(turn)));
}

function buildDemoTurnBlock(turn) {
  const parts = [];
  for (const event of turn.events) parts.push(buildDemoFlowBubble(event));
  if (turn.supervision) parts.push(buildDemoFlowBubble(supervisorDecisionEvent(turn.supervision, turn.turnIndex)));
  if (turn.continuation) parts.push(buildDemoFlowBubble(continuationDecisionEvent(turn.continuation, turn.turnIndex)));
  if (turn.syntheticContinuation) parts.push(buildDemoFlowBubble(continuationEvent(turn.syntheticContinuation, turn.turnIndex)));
  const meta = [
    turn.supervision?.verdict || turn.supervision?.decision || "",
    turn.supervision?.score == null ? "" : `score ${score(turn.supervision.score, { digits: 2 })}`,
  ].filter(Boolean).join(" · ");
  return h("div.demo-cycle-block", [
    h("div.demo-cycle-head", [
      h("strong", `Cycle ${turn.turnIndex}`),
      h("span", meta || "executor turn"),
    ]),
    h("div.demo-cycle-events", parts),
  ]);
}

function buildDemoTimelineGantt(payload) {
  const timeline = pickDemoTimeline(payload);
  if (!timeline) return h("div.demo-preview-empty", "Timeline metadata is not available for this attempt.");
  const baseMs = Number(timeline.attempt_started_ms) || 0;
  const endMs = Number(timeline.attempt_ended_ms) || baseMs;
  const totalMs = Math.max(1, endMs - baseMs);
  const steps = flattenDemoTimelinePhases(Array.isArray(timeline.phases) ? timeline.phases : []);
  const rowsSlot = h("div.exec-timeline-steps");
  const count = h("span.exec-timeline-count", `${steps.length} steps`);
  const input = h("input.exec-timeline-filter", { type: "search", placeholder: "Filter steps…" });
  const render = () => {
    const needle = String(input.value || "").toLowerCase().trim();
    const visible = needle
      ? steps.filter((step) => `${step.name} ${step.category} ${step.kind} ${step.agent_id || ""}`.toLowerCase().includes(needle))
      : steps;
    count.textContent = needle ? `${visible.length} / ${steps.length} steps` : `${steps.length} steps`;
    clear(rowsSlot);
    if (!visible.length) {
      rowsSlot.appendChild(h("div.exec-timeline-empty", needle ? "No steps match this filter." : "No steps recorded yet."));
      return;
    }
    visible.forEach((step, idx) => rowsSlot.appendChild(buildDemoTimelineStep(step, idx, baseMs, totalMs)));
  };
  input.addEventListener("input", render);
  render();
  return h("div.demo-exec-timeline", [
    h("div.exec-timeline-summary", [
      h("strong", `Total ${formatDemoDuration(totalMs)}`),
      h("span.exec-timeline-status", { "data-in-progress": timeline.in_progress ? "true" : "false" }, timeline.in_progress ? "in progress" : "finished"),
    ]),
    h("div.exec-timeline-controls", [input, count]),
    rowsSlot,
  ]);
}

function pickDemoTimeline(payload) {
  const detail = selectedAttemptDetail(payload);
  const detailTimeline = detail?.timeline;
  if (detailTimeline && Array.isArray(detailTimeline.phases) && detailTimeline.phases.length) return detailTimeline;
  const top = payload?.timeline;
  if (top && Array.isArray(top.phases) && top.phases.length) return top;
  return null;
}

function flattenDemoTimelinePhases(phases) {
  const steps = [];
  for (const phase of phases || []) {
    if (!phase || typeof phase !== "object") continue;
    if (phase.kind === "executor" && Array.isArray(phase.tool_calls) && phase.tool_calls.length) {
      steps.push(demoTimelineStep(phase, "executor", phase.name || `cycle_${phase.cycle ?? "??"}_executor`, true));
      for (const call of phase.tool_calls) {
        if (!call) continue;
        const name = String(call.name || "tool");
        steps.push({
          kind: "tool_call",
          category: classifyDemoTimelineStep(name),
          name,
          agent_id: call.agent_id && call.agent_id !== "main" ? call.agent_id : "",
          start_ms: Number(call.start_ms) || 0,
          end_ms: Number(call.end_ms) || 0,
          approximate: !!call.approximate,
          cycle: phase.cycle,
        });
      }
      continue;
    }
    const category = phase.kind === "container_lifecycle" ? "container" : (phase.kind || "tool");
    steps.push(demoTimelineStep(phase, category, phase.name || phase.kind || "phase", false));
  }
  return steps.sort((a, b) => (a.start_ms || 0) - (b.start_ms || 0));
}

function demoTimelineStep(phase, category, name, isHeader) {
  return {
    kind: phase.kind || category,
    category,
    name,
    start_ms: Number(phase.start_ms) || 0,
    end_ms: Number(phase.end_ms) || 0,
    cycle: phase.cycle,
    verdict: phase.verdict,
    score: phase.score,
    skipped: !!phase.skipped,
    skip_reason: phase.skip_reason,
    errored: !!phase.errored,
    isHeader,
  };
}

function classifyDemoTimelineStep(name) {
  const n = String(name || "").toLowerCase();
  if (n === "browser" || n.startsWith("browser_") || n.startsWith("mcp_playwright")) return "browser";
  if (n === "read" || n === "read_file" || n === "view_image") return "read";
  if (n === "write" || n === "write_file" || n === "edit") return "write";
  if (n === "exec" || n === "bash" || n === "shell" || n.includes("process")) return "exec";
  if (n.includes("search") || n.includes("duckduckgo")) return "search";
  if (n.includes("sessions_spawn") || n.includes("agents_")) return "meta";
  return "tool";
}

function buildDemoTimelineStep(step, idx, baseMs, totalMs) {
  const startMs = Number(step.start_ms) || baseMs;
  const endMs = Math.max(Number(step.end_ms) || startMs, startMs);
  const durMs = Math.max(0, endMs - startMs);
  let leftPct = ((startMs - baseMs) / totalMs) * 100;
  let widthPct = (durMs / totalMs) * 100;
  leftPct = Math.max(0, Math.min(100, leftPct));
  widthPct = Math.max(0.4, widthPct);
  if (leftPct + widthPct > 100) widthPct = Math.max(0.4, 100 - leftPct);
  const title = [
    step.name,
    `start t+${((startMs - baseMs) / 1000).toFixed(1)}s`,
    `dur ${formatDemoDuration(durMs)}`,
    step.cycle != null ? `cycle ${step.cycle}` : "",
    step.agent_id ? `agent ${step.agent_id}` : "",
    step.verdict ? `verdict ${step.verdict}` : "",
    step.skipped ? `skipped (${step.skip_reason || "no reason"})` : "",
    step.approximate ? "approximate" : "",
    step.errored ? "errored" : "",
  ].filter(Boolean).join(" · ");
  const label = step.category === "browser" && step.name !== step.category
    ? `browser: ${String(step.name).replace(/^browser_/, "").replace(/^browser:?\s*/, "")}`
    : step.name;
  return h("div.exec-step", {
    "data-category": step.category || "tool",
    "data-approximate": step.approximate ? "true" : null,
    "data-skipped": step.skipped ? "true" : null,
    "data-errored": step.errored ? "true" : null,
    "data-header": step.isHeader ? "true" : null,
    title,
  }, [
    h("div.exec-step-num", String(idx + 1)),
    h("div.exec-step-accent"),
    h("div.exec-step-body", [
      h("div.exec-step-head", [
        h("span.exec-step-icon", { "aria-hidden": "true" }, stepIconForDemo(step.category)),
        h("span.exec-step-name", label),
        step.agent_id ? h("span.exec-step-agent", step.agent_id) : null,
        step.cycle != null ? h("span.exec-step-cycle", `c${String(step.cycle).padStart(2, "0")}`) : null,
        h("span.exec-step-dur", formatDemoDuration(durMs)),
      ]),
      h("div.exec-step-bar", h("div.exec-step-bar-fill", { style: { left: `${leftPct.toFixed(3)}%`, width: `${widthPct.toFixed(3)}%` } })),
    ]),
  ]);
}

function stepIconForDemo(category) {
  switch (category) {
    case "container": return "pkg";
    case "executor": return "run";
    case "browser": return "web";
    case "read": return "read";
    case "write": return "write";
    case "exec": return "exec";
    case "search": return "find";
    case "meta": return "meta";
    case "supervisor": return "eval";
    case "user_simulator": return "user";
    case "artifact": return "file";
    default: return "tool";
  }
}

function formatDemoDuration(ms) {
  const n = Number(ms) || 0;
  if (n < 1000) return `${Math.round(n)}ms`;
  const s = n / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 2 : 1)}s`;
  const m = Math.floor(s / 60);
  const rem = s - m * 60;
  return `${m}m${rem.toFixed(rem < 10 ? 1 : 0)}s`;
}

function buildDemoFlowBubble(event) {
  const bubble = h(`div.bubble.${event.kind}`, [
    h("div.bubble-title-row", [
      h("div.bubble-title", event.title),
      event.agent ? h("span.agent-chip", event.agent) : null,
    ]),
    event.body ? h("div.bubble-body", h("pre", event.body)) : null,
  ]);
  if (event.agentId) bubble.dataset.agent = event.agentId;
  return bubble;
}

function demoTurnGroups(payload, options = {}) {
  const detail = selectedAttemptDetail(payload) || {};
  const events = demoFlowEvents(payload, options);
  const turns = [];
  let current = null;
  for (const event of events) {
    if (event.kind === "user") {
      if (current) turns.push(current);
      current = { turnIndex: turns.length + 1, events: [event], userEvent: event };
      continue;
    }
    if (!current) current = { turnIndex: turns.length + 1, events: [], userEvent: null };
    current.events.push(event);
  }
  if (current) turns.push(current);
  const trace = supervisionTraceForPayload(payload);
  const cycleMap = new Map(trace.map((item, idx) => [Number(item.evaluation_index || idx + 1), item]));
  const continuationMap = new Map((Array.isArray(detail.continuationTrace) ? detail.continuationTrace : [])
    .map((item) => [continuationRawIndex(item), item]));
  const continuationRecords = Array.isArray(detail.continuations) ? detail.continuations : [];
  for (const turn of turns) {
    turn.supervision = cycleMap.get(turn.turnIndex) || null;
    turn.continuation = continuationMap.get(turn.turnIndex) || null;
    const nextTurnHasUser = turns.some((candidate) => candidate.turnIndex === turn.turnIndex + 1 && candidate.userEvent);
    turn.syntheticContinuation = nextTurnHasUser
      ? null
      : continuationRecords.find((item) => Number(item?.index || 0) === turn.turnIndex) || null;
  }
  for (const [cycle, supervision] of cycleMap.entries()) {
    if (!turns.some((turn) => turn.turnIndex === cycle)) {
      turns.push({ turnIndex: cycle, events: [], userEvent: null, supervision, continuation: continuationMap.get(cycle) || null });
    }
  }
  turns.sort((a, b) => a.turnIndex - b.turnIndex);
  return turns.filter((turn) => turn.events.length || turn.supervision || turn.continuation || turn.syntheticContinuation);
}

function continuationRawIndex(item) {
  const index = Number(item?.evaluationIndex ?? item?.evaluation_index ?? item?.index ?? 0);
  return Number.isFinite(index) && index > 0 ? index : 0;
}

function continuationEvent(item, cycle) {
  return {
    kind: "user",
    title: `Simulated User / Continuation ${cycle}`,
    body: item?.safeUserFeedback || item?.safe_user_feedback || item?.public_feedback_summary || "",
  };
}

function continuationDecisionEvent(item, cycle) {
  return {
    kind: "user",
    title: `User Simulator Feedback · Cycle ${cycle}`,
    body: item?.safeUserFeedback || item?.safe_user_feedback || item?.public_feedback_summary || "",
  };
}

function demoFlowEvents(payload, options = {}) {
  const showTools = Boolean(options.showTools);
  const detail = selectedAttemptDetail(payload) || {};
  const transcript = Array.isArray(detail.transcript) ? detail.transcript : (Array.isArray(payload?.transcript) ? payload.transcript : []);
  const events = [];
  let userIndex = 0;
  for (const item of transcript) {
    const agentId = item.agentId || item.agent || item.agent_id || item.message?.agentId || "";
    const agent = agentId ? agentId.replaceAll("_", " ") : "";
    if (item.type === "plain_message") {
      if (item.role === "assistant" || showTools) {
        events.push({
          kind: item.role === "assistant" ? "assistant" : "system",
          title: item.role === "assistant" ? "Agent Output" : "Runtime Log",
          body: String(item.text || ""),
          agentId,
          agent,
        });
      }
      continue;
    }
    if (item.type !== "message") continue;
    const message = item.message || {};
    const role = String(message.role || "");
    const content = Array.isArray(message.content) ? message.content : [];
    if (role === "assistant") {
      const assistantText = contentText(content);
      if (assistantText) {
        events.push({
          kind: "assistant",
          title: agent ? `${titleCase(agent)} Output` : "Agent Output",
          body: assistantText,
          agentId,
          agent,
        });
      }
      for (const part of content) {
        if (part?.type !== "toolCall") continue;
        if (!showTools) continue;
        events.push({
          kind: "tool",
          title: part.name || part.toolName || "Tool Call",
          body: toolCallBody(part),
          agentId,
          agent,
        });
      }
    } else if (role === "user") {
      const userText = contentText(content);
      if (!userText) continue;
      userIndex += 1;
      events.push({
        kind: "user",
        title: userIndex === 1 ? "Task Input" : "Simulated User / Continuation",
        body: userText,
        agentId,
        agent,
      });
    } else if (role === "toolResult") {
      if (!showTools) continue;
      const body = contentText(content) || "Tool result recorded.";
      events.push({
        kind: "tool-result",
        title: `Tool Result · ${message.toolName || message.name || "tool"}`,
        body: shortText(body, 1200),
        agentId,
        agent,
      });
    }
  }
  return events;
}

function supervisionTraceForPayload(payload) {
  const detail = selectedAttemptDetail(payload);
  if (Array.isArray(detail?.supervisionTrace) && detail.supervisionTrace.length) return detail.supervisionTrace;
  if (Array.isArray(payload?.supervisionTrace) && payload.supervisionTrace.length) return payload.supervisionTrace;
  return [];
}

function supervisorDecisionEvent(item, idx) {
  const verdict = item.verdict || item.status || item.decision || "recorded";
  const scoreValue = item.score ?? item.overall_score ?? item.finalScore;
  const note = [verdict, scoreValue == null ? "" : `score ${score(scoreValue, { digits: 2 })}`].filter(Boolean).join(" · ");
  const body = item.safe_user_feedback
    || item.public_feedback_summary
    || item.feedback
    || item.reasoning
    || item.rationale
    || item.summary
    || item.message
    || item.comment
    || note;
  return {
    kind: "supervisor",
    title: `Supervisor Decision · Cycle ${idx}`,
    body: shortText(body || note, 1200),
  };
}

function contentText(content) {
  const pieces = [];
  for (const part of content || []) {
    if (typeof part === "string") {
      pieces.push(part);
      continue;
    }
    if (!part || typeof part !== "object") continue;
    if (typeof part.text === "string") pieces.push(part.text);
    else if (typeof part.content === "string") pieces.push(part.content);
    else if (typeof part.value === "string") pieces.push(part.value);
  }
  return pieces.join("\n").trim();
}

function toolCallBody(part) {
  if (part.summary) return shortText(part.summary, 1200);
  const fields = [part.args, part.arguments, part.input, part.parameters, part.params, part.content, part.text]
    .filter((value) => value != null && value !== "");
  for (const field of fields) {
    if (typeof field === "string") return shortText(field, 1200);
    if (typeof field === "object" && !isEmptyObject(field)) {
      try {
        return shortText(JSON.stringify(field, null, 2), 1200);
      } catch {
        // Fall through to the compact metadata summary below.
      }
    }
  }
  const lines = [
    `Tool: ${part.name || part.toolName || "tool"}`,
    part.id || part.toolCallId || part.callId ? `Call ID: ${part.id || part.toolCallId || part.callId}` : null,
    part.status ? `Status: ${part.status}` : null,
    "Arguments: not serialized in this trace payload.",
  ].filter(Boolean);
  return lines.join("\n");
}

function isEmptyObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0;
}

function titleCase(value) {
  return String(value || "").replace(/\b\w/g, (c) => c.toUpperCase());
}

function shortText(value, max = 800) {
  const text = String(value || "").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

function selectedAttemptDetail(payload) {
  const details = Array.isArray(payload?.attemptDetails) ? payload.attemptDetails : [];
  if (!details.length) return null;
  const selectedPath = String(payload?.selectedAttemptPath || "");
  if (selectedPath) {
    const selected = details.find((detail) => String(detail?.attemptPath || "") === selectedPath);
    if (selected) return selected;
  }
  return details.find((detail) => String(detail?.status || "") === "resolved") || details[details.length - 1];
}

function orderedAttemptDetails(payload) {
  const details = Array.isArray(payload?.attemptDetails) ? payload.attemptDetails : [];
  const selected = selectedAttemptDetail(payload);
  if (!selected) return details;
  return [selected, ...details.filter((detail) => detail !== selected)];
}

async function demoMediaForRun(relPath) {
  if (demoMediaCache.has(relPath)) return demoMediaCache.get(relPath);
  const promise = getJSON(attemptUrl(relPath)).then(pickDemoMedia);
  demoMediaCache.set(relPath, promise);
  return promise;
}

function attemptUrl(relPath) {
  const staticBase = typeof window !== "undefined" && window.CLAWBENCH_STATIC_ATTEMPTS_BASE;
  if (!staticBase) return `/api/attempt?path=${encodeURIComponent(relPath)}`;
  return `${staticBase}/${String(relPath).split("/").map(encodeURIComponent).join("/")}.json`;
}

function pickDemoMedia(payload) {
  const details = orderedAttemptDetails(payload);
  const candidates = details.length ? details : [payload || {}];
  for (const detail of candidates) {
    const files = Array.isArray(detail.resultFiles) ? detail.resultFiles : Array.isArray(payload?.resultFiles) ? payload.resultFiles : [];
    const video = files.find((file) => isMedia(file, ["mp4", "webm", "mov"]));
    const image = files.find((file) => isMedia(file, ["png", "jpg", "jpeg", "gif", "webp"]));
    if (video) return { video: video.url, image: image?.url || detail.recording?.poster || "" };
    const recordings = Object.values(detail.recordingsByCycle || {});
    const recording = recordings.find((rec) => rec && rec.url) || detail.recording;
    if (recording?.url) return { video: recording.url, image: recording.poster || image?.url || "" };
    if (image) return { image: image.url };
  }
  return {};
}

function isMedia(file, exts) {
  const path = String(file?.path || file?.url || "").toLowerCase();
  return Boolean(file?.url) && exts.some((ext) => path.endsWith(`.${ext}`));
}

function buildMedia(media, title, onEnded = null) {
  if (media.video) {
    const videoSrc = versionedDemoAsset(media.video);
    const posterSrc = versionedDemoAsset(media.image || "");
    const mediaPath = String(media.video).split(/[?#]/)[0].toLowerCase();
    const video = h("video", {
      controls: true,
      autoplay: true,
      muted: true,
      playsInline: true,
      preload: "metadata",
      poster: posterSrc,
    });
    video.appendChild(h("source", { src: videoSrc, type: mediaPath.endsWith(".webm") ? "video/webm" : "video/mp4" }));
    video.appendChild(document.createTextNode("Video preview unavailable."));
    if (typeof onEnded === "function") video.addEventListener("ended", onEnded);
    setTimeout(() => video.play?.().catch?.(() => {}), 0);
    return video;
  }
  if (media.image) return h("img", { src: versionedDemoAsset(media.image), alt: title, loading: "lazy" });
  return h("div.demo-media-empty", "No media preview");
}

function versionedDemoAsset(url) {
  if (!url) return "";
  const value = String(url);
  if (!value.includes("assets/demo/")) return value;
  return value + (value.includes("?") ? "&" : "?") + `v=${encodeURIComponent(DEMO_ASSET_VERSION)}`;
}

function pill(label) {
  return h("span.demo-pill", label || "—");
}

function buildRuntimeSection() {
  return h("section.home-section.home-runtime-grid", [
    figureCard(PAPER_FIGURES.tokens, "Token usage and performance progression by cycle", "strip"),
    h("div.home-section-copy", [
      h("div.eyebrow", "Run review surfaces"),
      h("h2", "Dynamic and static WebUI share the same review model"),
      h("p", "The live server and exported static bundle use the same Home, Leaderboard, Tasks, and Trace components. Static exports ship compact indices plus lazy attempt payloads so timeline, supervisor assessment, saved results, and task definitions remain available on a static host."),
      h("div.home-role-strip", [
        roleChip("Leaderboard", "PR, AS, tokens, runtime, scope controls"),
        roleChip("Tasks", "Prompt, sources, privacy manifest"),
        roleChip("Trace", "Timeline, transcripts, artifacts, supervisor cycles"),
      ]),
    ]),
  ]);
}

function figureCard(src, caption, variant = "") {
  const figure = h("figure.paper-figure", [
    h("div.figure-media", h("img", { src, alt: caption, loading: "lazy" })),
    h("figcaption", caption),
  ]);
  if (variant) figure.classList.add(`paper-figure-${variant}`);
  return figure;
}

function uniqueTasks(tasks, aggregate) {
  if (tasks.length) {
    return new Set(tasks.filter((task) => !String(task.category || "").startsWith("0")).map((task) => task.task_id)).size;
  }
  if (aggregate.task_count) return aggregate.task_count;
  return 0;
}

function passRateFromRows(rows) {
  if (!Array.isArray(rows) || !rows.length) return null;
  const scored = rows.filter((row) => typeof row?.passed === "boolean");
  if (!scored.length) return null;
  return scored.filter(isPassedRow).length / scored.length;
}

function isPassedRow(row) {
  return row?.passed === true;
}

function capabilityCounts(tasks) {
  const order = [
    ["skill_usage", "Skill Usage"],
    ["exploration", "Exploration"],
    ["long_context", "Long Context"],
    ["multimodal", "Multimodal"],
    ["cross_platform", "Cross-Platform"],
  ];
  return order.map(([needle, label]) => ({
    label,
    count: tasks.filter((task) => String(task.category || "").includes(needle)).length,
  }));
}

function prepareLeaderboardRows(aggregate) {
  const rows = Array.isArray(aggregate.models) ? aggregate.models : aggregateClientModels(aggregate.rows || []);
  return [...rows]
    .filter((row) => row.total && row.total.n)
    .sort((a, b) => (b.total.pass_rate ?? -1) - (a.total.pass_rate ?? -1));
}

function prepareHarnessRows(aggregate) {
  const commonRows = fairHarnessRows(aggregate);
  const rows = commonRows.length
    ? commonRows
    : (Array.isArray(aggregate.backends) ? aggregate.backends : aggregateClientHarnesses(aggregate.rows || []));
  return [...rows]
    .filter((row) => row.total && row.total.n)
    .sort((a, b) => (b.total.pass_rate ?? -1) - (a.total.pass_rate ?? -1));
}

function fairHarnessRows(aggregate) {
  const rows = Array.isArray(aggregate?.rows) ? aggregate.rows : [];
  const allBackends = Array.isArray(aggregate?.all_backends)
    ? aggregate.all_backends.filter(Boolean)
    : [...new Set(rows.map((row) => row.backend).filter(Boolean))].sort();
  if (!rows.length || allBackends.length < 2) return [];

  const modelBackends = new Map();
  for (const row of rows) {
    if (!row.model_slug || !row.backend) continue;
    if (!modelBackends.has(row.model_slug)) modelBackends.set(row.model_slug, new Set());
    modelBackends.get(row.model_slug).add(row.backend);
  }
  const commonModels = new Set(
    [...modelBackends.entries()]
      .filter(([, backends]) => allBackends.every((backend) => backends.has(backend)))
      .map(([model]) => model),
  );
  if (!commonModels.size) return [];

  let filtered = rows.filter((row) => commonModels.has(row.model_slug));
  const taskBackends = new Map();
  for (const row of filtered) {
    if (!row.category || !row.task_id || !row.backend) continue;
    const key = `${row.category}::${row.task_id}`;
    if (!taskBackends.has(key)) taskBackends.set(key, new Set());
    taskBackends.get(key).add(row.backend);
  }
  const commonTasks = new Set(
    [...taskBackends.entries()]
      .filter(([, backends]) => allBackends.every((backend) => backends.has(backend)))
      .map(([task]) => task),
  );
  if (!commonTasks.size) return [];

  filtered = filtered.filter((row) => commonTasks.has(`${row.category}::${row.task_id}`));
  return aggregateClientHarnesses(filtered);
}

function aggregateClientModels(rows) {
  const buckets = new Map();
  for (const row of rows || []) {
    if (row.backend !== "openclaw") continue;
    const key = row.model_slug || row.modelSlug || row.model || "";
    if (!key) continue;
    const slot = buckets.get(key) || { key, label: row.model_label || row.model || key, values: [] };
    slot.values.push(row);
    buckets.set(key, slot);
  }
  return [...buckets.values()].map((slot) => {
    const n = slot.values.length;
    return {
      key: slot.key,
      label: slot.label,
      total: {
        n,
        pass_rate: n ? slot.values.filter(isPassedRow).length / n : null,
        avg_score: n ? slot.values.reduce((sum, row) => sum + Number(row.score ?? row.finalScore ?? 0), 0) / n : null,
      },
    };
  });
}

function leaderHarnessForModel(aggregate, modelRow) {
  const rows = Array.isArray(aggregate?.rows) ? aggregate.rows : [];
  const target = displayModelName(modelRow?.label || modelRow?.key || "");
  if (!rows.length || !target) return "";
  const buckets = new Map();
  for (const row of rows) {
    const label = displayModelName(row.model_label || row.model || row.model_slug || row.modelSlug || "");
    if (label !== target) continue;
    const backend = row.backend || "unknown";
    const slot = buckets.get(backend) || { key: backend, label: backend, values: [] };
    slot.values.push(row);
    buckets.set(backend, slot);
  }
  const best = [...buckets.values()]
    .map((slot) => summarizeRows(slot))
    .filter((row) => row.total && row.total.n)
    .sort((a, b) => (b.total.pass_rate ?? -1) - (a.total.pass_rate ?? -1))[0];
  return best ? backendDisplayName(best.label || best.key) : "";
}

function aggregateClientHarnesses(rows) {
  const buckets = new Map();
  for (const row of rows || []) {
    const key = row.backend || "";
    if (!key) continue;
    const slot = buckets.get(key) || { key, label: key, values: [] };
    slot.values.push(row);
    buckets.set(key, slot);
  }
  return [...buckets.values()].map((slot) => summarizeRows(slot));
}

function summarizeRows(slot) {
  const n = slot.values.length;
  return {
    key: slot.key,
    label: slot.label,
    total: {
      n,
      pass_rate: n ? slot.values.filter(isPassedRow).length / n : null,
      avg_score: n ? slot.values.reduce((sum, row) => sum + Number(row.score ?? row.finalScore ?? 0), 0) / n : null,
    },
  };
}

function backendDisplayName(value) {
  const label = String(value || "");
  if (label === "openclaw_edict") return "OpenClaw Edict";
  if (label === "openclaw") return "OpenClaw";
  return label.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function unpackRuns(payload) {
  const runs = Array.isArray(payload?.runs) ? payload.runs : [];
  if (!Array.isArray(payload?.fields)) return runs;
  const fields = payload.fields.map((field) => String(field || ""));
  return runs.map((row) => {
    if (!Array.isArray(row)) return row || {};
    const item = {};
    fields.forEach((field, index) => {
      if (field) item[field] = row[index];
    });
    return item;
  });
}

function statusLabel(status) {
  return String(status || "unknown").replaceAll("_", " ");
}
