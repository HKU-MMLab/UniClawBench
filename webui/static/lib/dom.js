// Tiny hyperscript-style helpers for building DOM trees in pages/*.
//
// ``h('div.results-card', { onclick }, [...children])`` returns an
// HTMLElement. Tag accepts ``tag.cls1.cls2#id`` shorthand. ``children``
// is null-tolerant so caller can ``cond && h(...)`` without filtering.

export function h(spec, props, children) {
  const { tag, id, classList } = parseSpec(spec);
  const el = document.createElement(tag);
  if (id) el.id = id;
  for (const cls of classList) el.classList.add(cls);
  if (props && typeof props === "object" && !Array.isArray(props) && !(props instanceof Node)) {
    applyProps(el, props);
  } else if (props !== undefined && props !== null) {
    children = props;
  }
  if (children !== undefined && children !== null) appendChildren(el, children);
  return el;
}

function parseSpec(spec) {
  const out = { tag: "div", id: "", classList: [] };
  if (!spec) return out;
  const match = String(spec).match(/^([a-z][a-z0-9-]*)?((?:[.#][a-z0-9_-]+)*)$/i);
  if (!match) {
    out.tag = spec;
    return out;
  }
  if (match[1]) out.tag = match[1];
  const rest = match[2] || "";
  for (const piece of rest.match(/[.#][a-z0-9_-]+/gi) || []) {
    if (piece.startsWith("#")) out.id = piece.slice(1);
    else out.classList.push(piece.slice(1));
  }
  return out;
}

function applyProps(el, props) {
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class" || key === "className") {
      for (const cls of String(value).split(/\s+/).filter(Boolean)) {
        el.classList.add(cls);
      }
    } else if (key === "style" && typeof value === "object") {
      Object.assign(el.style, value);
    } else if (key === "dataset" && typeof value === "object") {
      for (const [k, v] of Object.entries(value)) el.dataset[k] = v;
    } else if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "html") {
      el.innerHTML = value;
    } else if (key in el && typeof el[key] !== "function") {
      try { el[key] = value; } catch { el.setAttribute(key, value); }
    } else {
      el.setAttribute(key, value);
    }
  }
}

function appendChildren(el, children) {
  if (Array.isArray(children)) {
    for (const child of children) appendChild(el, child);
  } else {
    appendChild(el, children);
  }
}

function appendChild(el, child) {
  if (child === null || child === undefined || child === false) return;
  if (child instanceof Node) el.appendChild(child);
  else el.appendChild(document.createTextNode(String(child)));
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
