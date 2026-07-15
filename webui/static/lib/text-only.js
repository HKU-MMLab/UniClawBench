// Shared task-capability manifest for the live WebUI and static export.
//
// Text-only means a model need not perform visual or audio reasoning itself.
// Tasks may still use deterministic OCR, DOM/API/CLI output, or create visual
// artifacts programmatically. Keep the list as task IDs rather than category
// prefixes because the subset deliberately spans several task families.

import { getJSON } from "./api.js";

const MANIFEST_URL = "static/data/text-only-tasks.json";
let cachedIds = null;

export async function getTextOnlyTaskIds({ refresh = false } = {}) {
  if (!refresh && cachedIds) return cachedIds;
  const payload = await getJSON(MANIFEST_URL, { refresh, noStore: refresh });
  const ids = Array.isArray(payload?.task_ids) ? payload.task_ids : [];
  cachedIds = new Set(ids.filter((id) => typeof id === "string" && id));
  return cachedIds;
}

export function isTextOnlyEnabled(query = {}) {
  return query.text === "only";
}
