// Tasks index page — grouped ALL / Smoketest / EN / ZH, each group with a
// second-level row of its suites (e.g. EN → ALL / 101 / … / 105).
//
// Categories are derived from the live /api/tasks data, never hardcoded,
// so renamed suites (and brand-new ones) show up automatically. Grouping
// is by the leading digit of the suite number: 0xx → Smoketest,
// 1xx → EN, 2xx → ZH.

import { getJSON, invalidate } from "../../lib/api.js";
import { h, clear } from "../../lib/dom.js";
import { categoryLabel } from "../../lib/format.js";
import { parseHash, writeHash } from "../../lib/router.js";
import { registerPageRefresh } from "../../lib/refresh.js";
import { mount as mountDetail } from "./detail.js";

const GROUPS = [
  { id: "smoke", label: "Smoketest", match: (c) => c.startsWith("0") },
  { id: "en", label: "EN", match: (c) => c.startsWith("1") },
  { id: "zh", label: "ZH", match: (c) => c.startsWith("2") },
];

// Ordered palette so each suite section gets a distinct, *sequenced* color
// (same hues as the Results page, for a consistent look across the app).
const PALETTE = ["#1f6f5f", "#b97a2c", "#2c6f8a", "#7a4f8a", "#a44a3f", "#4a6a52"];

function applyTheme(node, idx) {
  node.style.setProperty("--row-base", PALETTE[idx % PALETTE.length]);
}

function groupOf(category) {
  const g = GROUPS.find((x) => x.match(category));
  return g ? g.id : "other";
}

function categoriesFrom(tasks) {
  const set = new Set();
  for (const t of tasks) if (t.category) set.add(t.category);
  return [...set].sort();
}

let lastRoute = null;

export function tasksListUrl({ refresh = false } = {}) {
  const staticTasks =
    typeof window !== "undefined" &&
    typeof window.CLAWBENCH_STATIC_TASKS === "string" &&
    window.CLAWBENCH_STATIC_TASKS;
  if (!staticTasks) return refresh ? "/api/tasks?refresh=1" : "/api/tasks";
  return refresh
    ? staticTasks + (staticTasks.includes("?") ? "&" : "?") + "_=" + Date.now()
    : staticTasks;
}

export async function mount(root, route) {
  lastRoute = route;
  const grp = route.query.grp || "all";
  const cat = route.query.cat || "";

  clear(root);
  const page = h("div.tasks-page", [
    h("div.tasks-header", [h("h2", "Tasks")]),
    h("div#tasks-nav"),
    h("div#tasks-body", h("div.loading-stub", "Loading…")),
  ]);
  root.appendChild(page);

  const body = page.querySelector("#tasks-body");
  const nav = page.querySelector("#tasks-nav");
  try {
    const data = await getJSON(tasksListUrl());
    const tasks = data.tasks || [];
    const cats = categoriesFrom(tasks);
    renderNav(nav, cats, grp, cat);
    renderBody(body, tasks, cats, grp, cat);
  } catch (err) {
    clear(body);
    body.appendChild(h("div.error-stub", `Failed to load tasks: ${err.message || err}`));
  }
}

// One registration for the whole Tasks area — dispatches to the right
// mount based on the *current* route, not a stale ``lastRoute`` snapshot.
registerPageRefresh("tasks", async () => {
  invalidate("/api/tasks");
  invalidate(tasksListUrl());
  invalidate("/api/task/");
  const route = parseHash();
  const root = document.getElementById("page-root");
  if (route.sub) {
    await mountDetail(root, route);
  } else {
    await mount(root, route);
  }
});

function pill(label, active, query) {
  const link = h("a", {
    href: "#/tasks",
    onclick: (event) => {
      event.preventDefault();
      writeHash({ page: "tasks", query });
    },
  }, label);
  if (active) link.classList.add("active");
  return link;
}

function renderNav(nav, cats, grp, cat) {
  clear(nav);
  // Top level: ALL + only the groups that actually have suites present.
  const top = h("div.tasks-cat-filter");
  top.appendChild(pill("ALL", grp === "all", {}));
  for (const g of GROUPS) {
    if (!cats.some((c) => groupOf(c) === g.id)) continue;
    top.appendChild(pill(g.label, grp === g.id, { grp: g.id }));
  }
  nav.appendChild(top);

  // Second level: the active group's suites (ALL + each suite number).
  if (grp !== "all") {
    const suites = cats.filter((c) => groupOf(c) === grp);
    const sub = h("div.tasks-cat-filter.tasks-cat-sub");
    sub.appendChild(pill("ALL", !cat, { grp }));
    for (const c of suites) {
      const slug = c.split("_")[0];
      sub.appendChild(pill(`${slug} ${categoryLabel(c)}`, cat === slug, { grp, cat: slug }));
    }
    nav.appendChild(sub);
  }
}

function renderBody(body, tasks, cats, grp, cat) {
  clear(body);
  let shown = cats;
  if (grp !== "all") shown = shown.filter((c) => groupOf(c) === grp);
  if (cat) shown = shown.filter((c) => c.split("_")[0] === cat);
  shown.forEach((c, idx) => {
    body.appendChild(buildSection(c, tasks.filter((t) => t.category === c), idx));
  });
  if (!shown.length) {
    body.appendChild(h("div.tasks-empty-cat", "No tasks in this scope yet."));
  }
}

function buildSection(category, tasks, idx = 0) {
  const section = h("section.tasks-section", [
    h("div.tasks-section-head", [
      h("div.tasks-section-title", `${category.split("_")[0]} · ${categoryLabel(category)}`),
      h("div.tasks-section-count", `${tasks.length} task${tasks.length === 1 ? "" : "s"}`),
    ]),
  ]);
  applyTheme(section, idx);
  if (!tasks.length) {
    section.appendChild(h("div.tasks-empty-cat", "Empty for now."));
    return section;
  }
  const grid = h("div.tasks-grid");
  for (const task of tasks) {
    grid.appendChild(buildCard(task));
  }
  section.appendChild(grid);
  return section;
}

function buildCard(task) {
  const card = h("a.task-card", {
    href: `#/tasks/${encodeURIComponent(task.task_id)}`,
    onclick: (event) => {
      event.preventDefault();
      writeHash({ page: "tasks", sub: task.task_id });
    },
  }, [
    h("div.task-card-id", task.task_id),
  ]);
  if (Array.isArray(task.skills) && task.skills.length) {
    const skillsRow = h("div.task-card-skills");
    for (const skill of task.skills.slice(0, 4)) {
      skillsRow.appendChild(h("span.task-card-skill", skill));
    }
    if (task.skills.length > 4) {
      skillsRow.appendChild(h("span.task-card-skill", `+${task.skills.length - 4}`));
    }
    card.appendChild(skillsRow);
  }
  if (task.prompt_preview) {
    card.appendChild(h("div.task-card-prompt", task.prompt_preview));
  }
  const present = [];
  if (task.has_privacy) present.push(".privacy");
  if (task.has_sources) present.push("sources");
  if (task.has_references) present.push("references");
  if (present.length) {
    const flagsRow = h("div.task-card-flags");
    for (const name of present) flagsRow.appendChild(h("span.task-card-flag.has", name));
    card.appendChild(flagsRow);
  }
  return card;
}
