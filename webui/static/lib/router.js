// URL hash router for the WebUI shell.
//
// Hash format: ``#/<page>[/<sub>][?<query>]``
//
// Routing is single-source-of-truth: the visible URL drives all UI
// state. ``writeHash`` uses ``replaceState`` so subsequent calls
// don't pollute the back-stack — only user-initiated nav (clicking a
// topnav link or hitting back) creates history entries.

export function parseHash(raw = window.location.hash) {
  const cleaned = String(raw || "").replace(/^#\/?/, "");
  if (!cleaned) return { page: "", sub: "", query: {} };
  const [pathPart, queryPart = ""] = cleaned.split("?");
  const segments = pathPart.split("/").filter(Boolean);
  const page = segments[0] || "";
  const sub = segments.slice(1).join("/");
  const query = {};
  if (queryPart) {
    for (const [k, v] of new URLSearchParams(queryPart).entries()) {
      query[k] = v;
    }
  }
  return { page, sub, query };
}

export function buildHash({ page, sub = "", query = {} }) {
  let path = "/" + page;
  if (sub) path += "/" + sub.replace(/^\/+/, "");
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const qsStr = qs.toString();
  return "#" + path + (qsStr ? "?" + qsStr : "");
}

export function writeHash(parts, { replace = true } = {}) {
  const next = buildHash(parts);
  if (next === window.location.hash) return;
  if (replace) {
    // ``replaceState`` does NOT fire ``hashchange``, so notify
    // listeners ourselves. Without this, the initial redirect from
    // ``#`` to ``#/trace`` would never trigger a render.
    history.replaceState(null, "", next);
    notify();
  } else {
    window.location.hash = next;
  }
}

function notify() {
  const parsed = parseHash();
  for (const fn of listeners) {
    try {
      fn(parsed);
    } catch (err) {
      console.error("router listener", err);
    }
  }
}

const listeners = new Set();
let bound = false;

function ensureBound() {
  if (bound) return;
  window.addEventListener("hashchange", () => {
    const parsed = parseHash();
    for (const fn of listeners) {
      try {
        fn(parsed);
      } catch (err) {
        console.error("router listener", err);
      }
    }
  });
  bound = true;
}

export function onRouteChange(fn) {
  ensureBound();
  listeners.add(fn);
  return () => listeners.delete(fn);
}
