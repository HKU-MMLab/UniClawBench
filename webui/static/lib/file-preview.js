// Text-file preview modal.
//
// Complements ``lightbox.js`` (which handles images) by rendering
// md/txt/json/yaml/log/csv/html content inline. Rendering:
//   - .md                → rendered markdown
//   - .json              → pretty-printed JSON
//   - .jsonl/.ndjson     → one pretty-printed JSON value per line
//   - .csv/.tsv          → compact table preview
//   - .html/.htm         → sandboxed iframe
//   - .yaml/.yml/.txt/.log → plain <pre>
//
// Body-level click delegation picks up any ``.file-preview-trigger``.

import { renderMarkdown } from "./markdown.js";
import { escapeHtml } from "./dom.js";

const TEXT_EXT = /\.(md|markdown|txt|log|json|jsonl|ndjson|ya?ml|csv|tsv|html?|xml|env|toml|ini|py|js|ts|css)$/i;

let inited = false;
let dom = null;

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

export function init() {
  if (inited) return;
  inited = true;
  dom = {
    root: document.getElementById("file-modal"),
    backdrop: document.getElementById("file-modal-backdrop"),
    close: document.getElementById("file-modal-close"),
    title: document.getElementById("file-modal-title"),
    body: document.getElementById("file-modal-body"),
    open: document.getElementById("file-modal-open"),
  };
  if (!dom.root) return;
  dom.backdrop?.addEventListener("click", hide);
  dom.close?.addEventListener("click", hide);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !dom.root.classList.contains("hidden")) {
      event.preventDefault();
      event.stopImmediatePropagation();
      hide();
    }
  });
  document.body.addEventListener("click", async (event) => {
    const trigger = event.target.closest(".file-preview-trigger");
    if (!trigger) return;
    event.preventDefault();
    const url = trigger.dataset.previewUrl || trigger.getAttribute("href");
    const name = trigger.dataset.previewName || url?.split("/").pop() || "preview";
    await show(url, name);
  });
}

export function canPreview(name) {
  return TEXT_EXT.test(name || "");
}

export async function show(url, name) {
  if (!dom?.root || !url) return;
  dom.title.textContent = name;
  dom.open.href = url;
  dom.body.innerHTML = `<div class="loading-stub">Loading…</div>`;
  dom.root.classList.remove("hidden");
  dom.root.setAttribute("aria-hidden", "false");
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const text = await response.text();
    await renderInto(dom.body, name, text, url);
  } catch (err) {
    dom.body.innerHTML = `<div class="error-stub">Failed to load: ${escapeHtml(err.message || err)}</div>`;
  }
}

export function hide() {
  if (!dom?.root) return;
  dom.root.classList.add("hidden");
  dom.root.setAttribute("aria-hidden", "true");
  dom.body.innerHTML = "";
  dom.title.textContent = "";
}

async function renderInto(body, name, text, url) {
  const lower = name.toLowerCase();
  if (/\.(md|markdown)$/.test(lower)) {
    const baseUrl = url.replace(/[^/]*$/, "");
    try {
      const html = await renderMarkdown(text, { baseUrl });
      body.innerHTML = `<div class="markdown-body file-preview-md">${html}</div>`;
    } catch (err) {
      body.innerHTML = `<pre class="file-preview-pre">${escapeHtml(text)}</pre>`;
    }
    return;
  }
  if (/\.json$/.test(lower)) {
    let pretty = text;
    try {
      pretty = JSON.stringify(JSON.parse(text), null, 2);
    } catch (_) {
      /* leave raw */
    }
    body.innerHTML = `<pre class="file-preview-pre">${escapeHtml(pretty)}</pre>`;
    return;
  }
  if (/\.(jsonl|ndjson)$/.test(lower)) {
    const pretty = String(text || "").split(/\r?\n/).map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return "";
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch (_) {
        return line;
      }
    }).join("\n");
    body.innerHTML = `<pre class="file-preview-pre">${escapeHtml(pretty)}</pre>`;
    return;
  }
  if (/\.(csv|tsv)$/.test(lower)) {
    body.innerHTML = renderDelimitedTable(text, lower.endsWith(".tsv") ? "\t" : ",");
    return;
  }
  if (/\.html?$/.test(lower)) {
    body.innerHTML = `<iframe class="file-preview-frame" src="${escapeAttr(url)}" title="${escapeAttr(name)}" sandbox="" referrerpolicy="no-referrer"></iframe>`;
    return;
  }
  body.innerHTML = `<pre class="file-preview-pre">${escapeHtml(text)}</pre>`;
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
    if (ch === '"') quoted = true;
    else if (ch === delimiter) {
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

function renderDelimitedTable(text, delimiter) {
  const rows = parseDelimitedRows(text, delimiter).slice(0, 80);
  if (!rows.length) return `<pre class="file-preview-pre">${escapeHtml(text || "")}</pre>`;
  const maxCols = Math.min(24, Math.max(...rows.map((row) => row.length)));
  const header = rows[0] || [];
  const body = rows.slice(1);
  const headerHtml = Array.from({ length: maxCols }, (_, i) => `<th>${escapeHtml(header[i] ?? "")}</th>`).join("");
  const bodyHtml = body.map((row) => (
    `<tr>${Array.from({ length: maxCols }, (_, i) => `<td>${escapeHtml(row[i] ?? "")}</td>`).join("")}</tr>`
  )).join("");
  return `
    <div class="result-table-wrap">
      <table class="result-table">
        <thead><tr>${headerHtml}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>
  `;
}
