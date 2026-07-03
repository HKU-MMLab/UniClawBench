// WebUI bootstrap.
//
// Owns the route table, the legacy-hash compatibility shim, the
// topnav active state, and the refresh FAB. Each page module
// exposes ``mount(pageRoot, route)`` which is responsible for its
// own teardown via the ``data-page`` attribute.

import { parseHash, writeHash, onRouteChange } from "./lib/router.js";
import * as lightbox from "./lib/lightbox.js";
import * as filePreview from "./lib/file-preview.js";
import * as shortcuts from "./lib/shortcuts.js";
import { invalidateAll } from "./lib/api.js";
import { getPageRefresh } from "./lib/refresh.js";

export { registerPageRefresh } from "./lib/refresh.js";

const PAGES = {
  home: () => import("./pages/home.js").then((mod) => mod.mount),
  trace: () => import("./pages/trace/index.js").then((mod) => mod.mount),
  leaderboard: () => import("./pages/results.js").then((mod) => mod.mount),
  tasks: async (route) => {
    const mod = route.sub ? await import("./pages/tasks/detail.js") : await import("./pages/tasks/index.js");
    return mod.mount;
  },
};

const pageRoot = document.getElementById("page-root");
const topnavLinks = Array.from(document.querySelectorAll(".topnav-link"));

lightbox.init();
filePreview.init();
shortcuts.init();

function highlightTopnav(page) {
  for (const link of topnavLinks) {
    link.classList.toggle("active", link.dataset.page === page);
  }
}

async function render(parsed) {
  let { page, sub, query } = parsed;
  if (!page && window.location.pathname && window.location.pathname !== "/") {
    const pathParts = window.location.pathname.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
    const pathPage = pathParts[0];
    if (PAGES[pathPage]) {
      writeHash({ page: pathPage, sub: pathParts.slice(1).join("/"), query });
      return;
    }
  }
  // First load with empty hash → home.
  if (!page) {
    writeHash({ page: "home" });
    return;
  }
  // Compatibility for pre-rename bookmarks.
  if (page === "results") {
    writeHash({ page: "leaderboard", sub: sub || "model", query });
    return;
  }
  // Old demo bookmarks now land on Home; demos are an embedded Home section,
  // not a separate top-level page.
  if (page === "demo") {
    writeHash({ page: "home" });
    return;
  }
  // Legacy bookmark format (no leading /trace/ prefix) → rewrite.
  // Any hash whose first segment isn't a known page is treated as
  // a trace attempt path.
  if (!PAGES[page]) {
    const legacy = parts => parts ? parts.replace(/^#\/?/, "") : "";
    const tail = legacy(window.location.hash);
    writeHash({ page: "trace", sub: tail });
    return;
  }
  // Leaderboard sub-redirect: bare /leaderboard → /leaderboard/model.
  if (page === "leaderboard" && !sub) {
    writeHash({ page: "leaderboard", sub: "model" });
    return;
  }
  highlightTopnav(page);
  pageRoot.dataset.page = page + (sub ? `/${sub}` : "");
  try {
    const mount = await PAGES[page]({ page, sub, query });
    const result = mount(pageRoot, { page, sub, query });
    if (result && typeof result.catch === "function") {
      result.catch((err) => {
        console.error(`page mount failed: ${page}`, err);
        pageRoot.innerHTML = `<div class="error-stub">Page render failed: ${escapeHtml(err.message || err)}</div>`;
      });
    }
  } catch (err) {
    console.error(`page mount failed: ${page}`, err);
    pageRoot.innerHTML = `<div class="error-stub">Page render failed: ${escapeHtml(err.message || err)}</div>`;
  }
}

function escapeHtml(s) {
  return String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

onRouteChange(render);
render(parseHash());

// Refresh FAB — defers to the active page's refresh handler. The
// page is responsible for invalidating its API cache and re-fetching.
const fab = document.getElementById("refresh-fab");
fab?.addEventListener("click", async () => {
  const route = parseHash();
  const page = route.page || "home";
  const handler = getPageRefresh(page);
  if (!handler) {
    invalidateAll();
    await render(route);
    return;
  }
  fab.classList.add("loading");
  try {
    await handler(route);
  } catch (err) {
    console.error("refresh failed", err);
  } finally {
    fab.classList.remove("loading");
  }
});
