// Thin fetch wrapper with URL-keyed dedupe cache.
//
// Returning the same Promise for in-flight requests means switching
// pages quickly (Tasks → Results → Tasks) doesn't refetch
// /api/aggregate twice. ``refresh: true`` bypasses both the in-flight
// cache and the server-side mtime cache (the FAB refresh button).

const inFlight = new Map();
const completed = new Map();

export async function getJSON(url, { refresh = false, noStore = false } = {}) {
  if (refresh) {
    completed.delete(url);
    inFlight.delete(url);
  } else if (completed.has(url)) {
    return completed.get(url);
  } else if (inFlight.has(url)) {
    return inFlight.get(url);
  }
  let fullUrl = refresh
    ? url + (url.includes("?") ? "&" : "?") + "refresh=1"
    : url;
  if (noStore) {
    fullUrl += (fullUrl.includes("?") ? "&" : "?") + "_=" + Date.now();
  }
  const promise = requestJSON(fullUrl, { noStore })
    .then(async (response) => {
      if (!response.ok) {
        const body = await response.text().catch(() => "");
        const error = new Error(`HTTP ${response.status}: ${body || response.statusText}`);
        error.status = response.status;
        throw error;
      }
      return response.json();
    })
    .then((data) => {
      completed.set(url, data);
      inFlight.delete(url);
      return data;
    })
    .catch((err) => {
      inFlight.delete(url);
      throw err;
    });
  inFlight.set(url, promise);
  return promise;
}

function requestJSON(url, { noStore = false } = {}) {
  if (typeof fetch === "function") {
    return fetch(url, {
      headers: { Accept: "application/json" },
      cache: noStore ? "no-store" : "default",
    });
  }
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.setRequestHeader("Accept", "application/json");
    if (noStore) xhr.setRequestHeader("Cache-Control", "no-store");
    xhr.onload = () => {
      resolve({
        ok: xhr.status >= 200 && xhr.status < 300,
        status: xhr.status,
        statusText: xhr.statusText,
        text: () => Promise.resolve(xhr.responseText),
        json: () => Promise.resolve(JSON.parse(xhr.responseText)),
      });
    };
    xhr.onerror = () => reject(new Error(`Network error while fetching ${url}`));
    xhr.ontimeout = () => reject(new Error(`Timed out while fetching ${url}`));
    xhr.send();
  });
}

export function invalidate(prefix) {
  for (const key of [...completed.keys()]) {
    if (key.startsWith(prefix)) completed.delete(key);
  }
  for (const key of [...inFlight.keys()]) {
    if (key.startsWith(prefix)) inFlight.delete(key);
  }
}

export function invalidateAll() {
  completed.clear();
  inFlight.clear();
}
