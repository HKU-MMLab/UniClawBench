// Task detail page — left 2/3 prompt + eval rule (separate cards),
// right 1/3 asset cards (skills, .privacy, sources, references).
//
// Asset cards only render when the payload reports them as present.
// Text-file rows (md/txt/json/yaml/log) open in the file preview modal;
// image rows open in the lightbox. Tree rendering uses an ASCII
// ``tree``-style prefix (├── / │ / └──) laid out as a single flat list
// so the viewer reads like plain terminal output instead of nested
// <details> accordions.

import { getJSON } from "../../lib/api.js";
import { h, clear, escapeHtml } from "../../lib/dom.js";
import { bytes } from "../../lib/format.js";
import { writeHash } from "../../lib/router.js";
import { renderMarkdown } from "../../lib/markdown.js";
import { canPreview } from "../../lib/file-preview.js";

const IMAGE_RE = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;

function taskDetailUrl(taskId) {
  const base =
    typeof window !== "undefined" &&
    typeof window.CLAWBENCH_STATIC_TASK_DETAIL_BASE === "string" &&
    window.CLAWBENCH_STATIC_TASK_DETAIL_BASE;
  if (base) {
    return `${base.replace(/\/+$/, "")}/${encodeURIComponent(taskId)}.json`;
  }
  return `/api/task/${encodeURIComponent(taskId)}`;
}

export async function mount(root, route) {
  const taskId = (route.sub || "").split("/")[0];
  if (!taskId) {
    clear(root);
    root.appendChild(h("div.error-stub", "Missing task id."));
    return;
  }
  clear(root);
  const page = h("div.task-detail-page", [
    buildBack(),
    h("div.loading-stub", `Loading ${taskId}…`),
  ]);
  root.appendChild(page);

  let payload;
  try {
    payload = await getJSON(taskDetailUrl(taskId));
  } catch (err) {
    clear(page);
    page.appendChild(buildBack());
    page.appendChild(h("div.error-stub", `Failed to load task: ${err.message || err}`));
    return;
  }

  clear(page);
  page.appendChild(buildBack());
  page.appendChild(buildHead(payload));

  const grid = h("div.task-detail-grid", [
    buildMain(payload),
    buildAside(payload),
  ]);
  page.appendChild(grid);

  fillMarkdown(grid, payload);
}

function buildBack() {
  return h("a.task-detail-back", {
    href: "#/tasks",
    onclick: (event) => {
      event.preventDefault();
      writeHash({ page: "tasks" });
    },
  }, "← Back to tasks");
}

function buildHead(payload) {
  const taskYaml = payload.task_yaml || {};
  const meta = h("div.task-detail-meta");
  meta.appendChild(h("span.pill", payload.category.split("_")[0]));
  if (taskYaml.timeout_seconds) {
    meta.appendChild(h("span", `timeout ${taskYaml.timeout_seconds}s`));
  }
  if (taskYaml.success_threshold) {
    meta.appendChild(h("span", `threshold ${taskYaml.success_threshold}`));
  }
  return h("div.task-detail-head", [
    h("h2", payload.task_id),
    meta,
  ]);
}

function buildMain(payload) {
  const main = h("div.task-detail-main");
  main.appendChild(h("section.detail-card", [
    h("div.detail-card-head", h("h3", "Task Prompt")),
    h(`div.detail-card-body.task-prompt-pre#prompt-${payload.task_id}`, payload.prompt || "—"),
  ]));
  if (payload.eval_rule_md) {
    main.appendChild(h("section.detail-card", [
      h("div.detail-card-head", h("h3", "Eval Rule")),
      h(
        "div.detail-card-body",
        h(`div.markdown-body#evalrule-${payload.task_id}`, h("div.loading-stub", "Rendering…")),
      ),
    ]));
  }
  return main;
}

function buildAside(payload) {
  const aside = h("div.task-detail-aside");
  const assets = payload.assets || {};
  if (Array.isArray(assets.skills)) {
    const list = h("ul.skills-list");
    if (assets.skills.length) {
      for (const slug of assets.skills) list.appendChild(h("li", slug));
    } else {
      list.appendChild(h("li", h("em", "(skills/ present, no slugs)")));
    }
    aside.appendChild(buildAssetCard(
      "skills",
      `${assets.skills.length} skill${assets.skills.length === 1 ? "" : "s"}`,
      list,
    ));
  }
  const privacyInfo = normalizePrivacyInfo(assets.privacy);
  if (privacyInfo) {
    const list = h("ul.privacy-list");
    if (privacyInfo.count) {
      list.appendChild(h("li", `${privacyInfo.count} private variable${privacyInfo.count === 1 ? "" : "s"} declared`));
    } else {
      list.appendChild(h("li", h("em", "(file present, no entries)")));
    }
    aside.appendChild(buildAssetCard(
      ".privacy",
      `${privacyInfo.count} var${privacyInfo.count === 1 ? "" : "s"}`,
      list,
    ));
  }
  if (Array.isArray(assets.sources)) {
    aside.appendChild(buildAssetCard("sources", countTree(assets.sources), buildTree(assets.sources)));
  }
  if (Array.isArray(assets.references)) {
    aside.appendChild(buildAssetCard("references", countTree(assets.references), buildTree(assets.references)));
  }
  if (!aside.children.length) {
    aside.appendChild(h("div.asset-card", h("div.asset-card-title", "No assets")));
  }
  return aside;
}

function normalizePrivacyInfo(value) {
  if (Array.isArray(value)) return { present: true, count: value.length };
  if (value && typeof value === "object" && value.present) {
    const count = Number.isFinite(Number(value.count)) ? Number(value.count) : 0;
    return { present: true, count };
  }
  return null;
}

function buildAssetCard(title, count, body) {
  return h("section.asset-card", [
    h("div.asset-card-head", [
      h("div.asset-card-title", title),
      h("div.asset-card-count", count),
    ]),
    h("div.asset-card-body", body),
  ]);
}

function countTree(nodes) {
  let files = 0;
  let dirs = 0;
  const walk = (list) => {
    for (const node of list) {
      if (node.is_dir) {
        dirs += 1;
        if (Array.isArray(node.children)) walk(node.children);
      } else {
        files += 1;
      }
    }
  };
  walk(nodes);
  if (!dirs) return `${files} file${files === 1 ? "" : "s"}`;
  return `${files} file${files === 1 ? "" : "s"} · ${dirs} dir${dirs === 1 ? "" : "s"}`;
}

// Flat ``tree``-style listing. ``ancestorsLast[i]`` is true when the
// ancestor at depth ``i`` was the last child of its parent — those levels
// render as spaces instead of ``│``.
function buildTree(nodes) {
  const wrap = h("div.file-tree");
  emitTreeRows(wrap, nodes, []);
  return wrap;
}

function emitTreeRows(host, nodes, ancestorsLast) {
  nodes.forEach((node, idx) => {
    const isLast = idx === nodes.length - 1;
    host.appendChild(buildTreeRow(node, ancestorsLast, isLast));
    if (node.is_dir && Array.isArray(node.children) && node.children.length) {
      emitTreeRows(host, node.children, ancestorsLast.concat(isLast));
    }
  });
}

function buildTreeRow(node, ancestorsLast, isLast) {
  const prefix = ancestorsLast.map((last) => (last ? "    " : "│   ")).join("");
  const branch = isLast ? "└── " : "├── ";
  const isImage = !node.is_dir && IMAGE_RE.test(node.name);
  const isText = !node.is_dir && canPreview(node.name);
  const nameSuffix = node.is_dir ? node.name + "/" : node.name;

  const row = h(node.is_dir ? "div.file-tree-row.dir" : "a.file-tree-row.file", [
    h("span.ft-prefix", prefix + branch),
    h("span.ft-name", nameSuffix),
  ]);
  if (!node.is_dir) {
    row.setAttribute("href", node.url);
    row.setAttribute("rel", "noopener");
    row.appendChild(h("span.ft-size", bytes(node.size)));
    if (isImage) {
      row.classList.add("image-preview-trigger");
      row.dataset.previewSrc = node.url;
      row.dataset.previewCaption = node.path || node.name;
    } else if (isText) {
      row.classList.add("file-preview-trigger");
      row.dataset.previewUrl = node.url;
      row.dataset.previewName = node.path || node.name;
    } else {
      // Non-previewable files open the raw asset in a new tab.
      row.setAttribute("target", "_blank");
    }
  }
  return row;
}

async function fillMarkdown(grid, payload) {
  const target = grid.querySelector(`#evalrule-${CSS.escape(payload.task_id)}`);
  if (!target || !payload.eval_rule_md) return;
  const staticBase =
    typeof window !== "undefined" &&
    typeof window.CLAWBENCH_STATIC_INJECTION_BASE === "string"
      ? window.CLAWBENCH_STATIC_INJECTION_BASE.replace(/\/+$/, "")
      : "/injection";
  const baseUrl = `${staticBase}/${payload.category}/${payload.task_id}/references/`;
  try {
    const html = await renderMarkdown(payload.eval_rule_md, { baseUrl });
    target.innerHTML = html;
  } catch (err) {
    target.innerHTML = `<div class="error-stub">Markdown render failed: ${escapeHtml(err.message || err)}</div>`;
  }
}
