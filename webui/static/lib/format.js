// Formatting helpers — numbers, durations, file sizes.

export function pct(value, { digits = 0, dash = "—" } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return dash;
  return (value * 100).toFixed(digits) + "%";
}

export function score(value, { digits = 2, dash = "—" } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return dash;
  return Number(value).toFixed(digits);
}

export function bytes(size) {
  if (size === null || size === undefined) return "";
  if (size < 1024) return size + " B";
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
  if (size < 1024 * 1024 * 1024) return (size / 1024 / 1024).toFixed(1) + " MB";
  return (size / 1024 / 1024 / 1024).toFixed(2) + " GB";
}

// 1234 → "1.2K" · 1234567 → "1.2M" · null/undef → dash
export function tokens(value, { dash = "—" } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return dash;
  const v = Number(value);
  if (v < 1000) return v.toFixed(0);
  if (v < 1_000_000) return (v / 1000).toFixed(1) + "K";
  return (v / 1_000_000).toFixed(2) + "M";
}

// 15234 ms → "15.2s" · 125000 ms → "2m 05s" · 3725000 → "1h 02m" · null → dash
export function duration(ms, { dash = "—" } = {}) {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return dash;
  const s = Number(ms) / 1000;
  if (s < 60) return s.toFixed(1) + "s";
  if (s < 3600) {
    const m = Math.floor(s / 60);
    const rs = Math.round(s - m * 60);
    return `${m}m ${String(rs).padStart(2, "0")}s`;
  }
  const h = Math.floor(s / 3600);
  const rm = Math.round((s - h * 3600) / 60);
  return `${h}h ${String(rm).padStart(2, "0")}m`;
}

export function categoryLabel(slug) {
  if (!slug) return "";
  const cleaned = slug.replace(/^\d+_?/, "").replace(/_/g, " ");
  const titled = cleaned.replace(/\b\w/g, (c) => c.toUpperCase());
  // Render standalone language tokens as acronyms: "Zh" → "ZH", "En" → "EN".
  return titled.replace(/\b(Zh|En)\b/g, (m) => m.toUpperCase());
}

const PROVIDER_PREFIXES = [
  "provider-all-new",
  "provider-all",
  "provider-primary",
  "native-openai-proxy",
  "proxy-example",
  "proxy-usage",
  "model-provider",
  "model-router",
  "api-proxy",
  "proxy",
];

const MODEL_DISPLAY_OVERRIDES = {
  "aws.claude-sonnet-4.6": "claude-sonnet-4.6",
  "aws-claude-sonnet-4-6": "claude-sonnet-4.6",
  "aws.claude-opus-4.6": "claude-opus-4.6",
  "aws-claude-opus-4-6": "claude-opus-4.6",
  "gpt-5-4-controller": "gpt-5.4",
};

export function displayModelName(value) {
  if (!value) return "";
  let label = String(value).trim();
  if (label.includes("/")) label = label.split("/").pop() || label;
  label = label.replaceAll("_", "-");

  let changed = true;
  while (changed) {
    changed = false;
    const lower = label.toLowerCase();
    for (const rawPrefix of PROVIDER_PREFIXES) {
      const prefix = rawPrefix.toLowerCase().replaceAll("_", "-");
      for (const sep of ["-", "."]) {
        const token = `${prefix}${sep}`;
        if (lower.startsWith(token)) {
          label = label.slice(token.length);
          changed = true;
          break;
        }
      }
      if (changed) break;
    }
  }

  label = stripToModelToken(label);

  const lower = label.toLowerCase();
  if (Object.prototype.hasOwnProperty.call(MODEL_DISPLAY_OVERRIDES, lower)) {
    return MODEL_DISPLAY_OVERRIDES[lower];
  }
  return restoreVersionDots(label);
}

function stripToModelToken(label) {
  const match = label.match(/claude-|gpt-\d|gemini-\d|qwen\d|kimi-k\d|minimax-m\d/i);
  if (match && match.index > 0) return label.slice(match.index);
  return label;
}

function restoreVersionDots(label) {
  const rules = [
    [/^(claude-(?:opus|sonnet))-(\d+)[.-](\d+)(?:-.+)?$/i, "$1-$2.$3"],
    [/^(gemini)-(\d+)-(\d+)-(.+)$/i, "$1-$2.$3-$4"],
    [/^(qwen\d+)-(\d+)(-.+)$/i, "$1.$2$3"],
    [/^(kimi-k\d+)-(\d+)$/i, "$1.$2"],
    [/^(minimax-m\d+)-(\d+)$/i, "$1.$2"],
  ];
  for (const [pattern, replacement] of rules) {
    const next = label.replace(pattern, replacement);
    if (next !== label) return next;
  }
  const gpt = label.match(/^(gpt)-(\d+)-(\d+)(?:-(mini|nano|controller))?$/i);
  if (gpt) {
    const suffix = gpt[4] && gpt[4].toLowerCase() !== "controller" ? `-${gpt[4]}` : "";
    return `${gpt[1]}-${gpt[2]}.${gpt[3]}${suffix}`;
  }
  return label;
}
