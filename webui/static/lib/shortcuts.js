// Global keyboard shortcuts.
//
// All bindings are guarded so they never fire while the user is typing
// in an input, textarea, select, or contenteditable node. Modal-open
// state also suppresses arrow navigation so ESC (already handled by
// lightbox.js / file-preview.js) remains the only modal affordance.
//
// Bindings (non-modifier, no focused input):
//   ←  / →    — switch top-level page (Home ↔ Leaderboard ↔ Tasks ↔ Trace).
//               Exception: on a Task detail view, ← / → walk the prev /
//               next task in the same order the list renders.
//   ↑  / ↓    — Tasks list: cycle category (All → 101 → 102 → …).
//               Trace page: select prev / next run card.
//   Esc       — Task detail: back to the Tasks list.
//               (lightbox / file-preview own their own ESC handlers.)

import { getJSON } from "./api.js";
import { parseHash, writeHash } from "./router.js";
import { tasksListUrl } from "../pages/tasks/index.js";

const PAGE_ORDER = ["home", "leaderboard", "tasks", "trace"];
const CATEGORY_ORDER = ["", "101", "102", "103", "104", "105"];

let inited = false;

export function init() {
  if (inited) return;
  inited = true;
  document.addEventListener("keydown", onKeydown);
}

function onKeydown(event) {
  if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
  if (isTypingTarget(event.target)) return;

  const open = openModal();
  if (open) {
    // Arrows would fight the modal (scroll, cycle). ESC is already
    // wired by the owning module, so we leave it alone.
    if (event.key !== "Escape") event.stopPropagation();
    return;
  }

  const route = parseHash();
  const page = route.page || "home";
  const key = event.key;

  if (key === "ArrowLeft" || key === "ArrowRight") {
    const delta = key === "ArrowRight" ? 1 : -1;
    if (page === "tasks" && route.sub) {
      event.preventDefault();
      navigateTask(route, delta);
      return;
    }
    event.preventDefault();
    switchPage(page, delta);
    return;
  }

  if (key === "ArrowUp" || key === "ArrowDown") {
    const delta = key === "ArrowDown" ? 1 : -1;
    if (page === "tasks" && !route.sub) {
      event.preventDefault();
      cycleCategory(route, delta);
      return;
    }
    if (page === "trace") {
      event.preventDefault();
      navigateTrace(delta);
      return;
    }
    return;
  }

  if (key === "Escape") {
    if (page === "tasks" && route.sub) {
      event.preventDefault();
      writeHash({ page: "tasks" });
    }
  }
}

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return Boolean(el.isContentEditable);
}

function openModal() {
  const lb = document.getElementById("image-lightbox");
  if (lb && !lb.classList.contains("hidden")) return lb;
  const fm = document.getElementById("file-modal");
  if (fm && !fm.classList.contains("hidden")) return fm;
  return null;
}

function switchPage(current, delta) {
  const idx = PAGE_ORDER.indexOf(current);
  const base = idx < 0 ? 0 : idx;
  const next = PAGE_ORDER[(base + delta + PAGE_ORDER.length) % PAGE_ORDER.length];
  if (next === current) return;
  writeHash({ page: next });
}

function cycleCategory(route, delta) {
  const current = (route.query && route.query.cat) || "";
  const idx = CATEGORY_ORDER.indexOf(current);
  const base = idx < 0 ? 0 : idx;
  const next = CATEGORY_ORDER[(base + delta + CATEGORY_ORDER.length) % CATEGORY_ORDER.length];
  writeHash({ page: "tasks", query: next ? { cat: next } : {} });
}

async function navigateTask(route, delta) {
  let data;
  try {
    data = await getJSON(tasksListUrl());
  } catch (err) {
    console.error("task shortcut fetch", err);
    return;
  }
  const tasks = (data && data.tasks) || [];
  if (!tasks.length) return;
  const currentId = (route.sub || "").split("/")[0];
  const idx = tasks.findIndex((t) => t.task_id === currentId);
  if (idx < 0) return;
  const next = tasks[(idx + delta + tasks.length) % tasks.length];
  writeHash({ page: "tasks", sub: next.task_id });
}

function navigateTrace(delta) {
  const list = document.getElementById("run-list");
  if (!list) return;
  const cards = Array.from(list.querySelectorAll(".run-card"));
  if (!cards.length) return;
  const activeIdx = cards.findIndex((card) => card.classList.contains("active"));
  const base = activeIdx < 0 ? (delta > 0 ? -1 : 0) : activeIdx;
  const targetIdx = (base + delta + cards.length) % cards.length;
  const target = cards[targetIdx];
  if (!target) return;
  target.click();
  // Keep the focused card in view so rapid presses don't scroll off.
  if (typeof target.scrollIntoView === "function") {
    target.scrollIntoView({ block: "nearest" });
  }
}
