// Per-page refresh handler registry.
//
// Lives in its own module so pages can register at import time without
// racing main.js's top-level body (ES modules execute imported modules
// before the importer's body runs).

const handlers = new Map();

export function registerPageRefresh(page, fn) {
  handlers.set(page, fn);
}

export function getPageRefresh(page) {
  return handlers.get(page);
}
