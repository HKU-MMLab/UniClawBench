// Markdown wrapper around vendored marked.min.js.
//
// Loaded via classic <script> on first use so Trace/Results don't pay
// the 38KB cost — only Tasks detail needs it. Image src paths get
// rewritten relative to ``baseUrl`` so eval_rule.md can refer to
// ``../sources/foo.png`` and the browser fetches it from the task's exported
// injection tree (or the live server's /injection/ route).

let loadingPromise = null;

function ensureLoaded() {
  if (window.marked) return Promise.resolve(window.marked);
  if (loadingPromise) return loadingPromise;
  loadingPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("./vendor/marked.min.js?v=multipage_1", import.meta.url).toString();
    script.onload = () => resolve(window.marked);
    script.onerror = () => {
      loadingPromise = null;
      reject(new Error("failed to load marked.min.js"));
    };
    document.head.appendChild(script);
  });
  return loadingPromise;
}

export async function renderMarkdown(source, { baseUrl = "" } = {}) {
  if (!source) return "";
  const marked = await ensureLoaded();
  marked.setOptions({ gfm: true, breaks: false, headerIds: false, mangle: false });
  let html = marked.parse(source);
  if (baseUrl) html = rewriteRelativeUrls(html, baseUrl);
  return sanitizeHtml(html);
}

function rewriteRelativeUrls(html, baseUrl) {
  // Resolve relative ``src=`` and ``href=`` against ``baseUrl`` so
  // images embedded in eval_rule.md resolve into the static export's
  // injection/<cat>/<task>/<asset_type>/ tree, even when the site is served
  // from a GitHub Pages subpath.
  const base = new URL(baseUrl, window.location.href);
  return html
    .replace(/(<img\b[^>]*\bsrc=)(["'])([^"']+)\2/gi, (match, prefix, quote, value) =>
      `${prefix}${quote}${absolutize(value, base)}${quote}`)
    .replace(/(<a\b[^>]*\bhref=)(["'])([^"']+)\2/gi, (match, prefix, quote, value) =>
      `${prefix}${quote}${absolutize(value, base)}${quote}`);
}

function absolutize(value, base) {
  if (!value || /^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith("#") || value.startsWith("/")) {
    return value;
  }
  try {
    return new URL(value, base).pathname + (new URL(value, base).search || "");
  } catch {
    return value;
  }
}

function sanitizeHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = String(html || "");

  const blockedTags = new Set([
    "base",
    "button",
    "embed",
    "form",
    "iframe",
    "input",
    "link",
    "meta",
    "object",
    "script",
    "select",
    "style",
    "textarea",
  ]);
  for (const el of Array.from(template.content.querySelectorAll("*"))) {
    const tag = el.tagName.toLowerCase();
    if (blockedTags.has(tag)) {
      el.remove();
      continue;
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on") || name === "srcdoc") {
        el.removeAttribute(attr.name);
        continue;
      }
      if (["href", "src", "xlink:href", "formaction"].includes(name) && !isSafeUrl(attr.value, tag, name)) {
        el.removeAttribute(attr.name);
      }
    }
    if (tag === "a") {
      el.setAttribute("rel", "noopener noreferrer");
      if (el.getAttribute("target") === "_blank") el.setAttribute("target", "_blank");
    }
  }
  return template.innerHTML;
}

function isSafeUrl(value, tag, attrName) {
  const raw = String(value || "").trim();
  if (!raw || raw.startsWith("#") || raw.startsWith("/") || raw.startsWith("./") || raw.startsWith("../")) return true;
  const lower = raw.toLowerCase();
  if (lower.startsWith("data:")) return tag === "img" && /^data:image\/(?:png|jpe?g|gif|webp|svg\+xml);/i.test(raw);
  if (/^(https?:|mailto:)/i.test(raw)) return true;
  if (attrName === "src" && /^(blob:)/i.test(raw)) return tag === "img";
  return false;
}
