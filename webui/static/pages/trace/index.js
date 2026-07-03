// Trace page mount.
//
// Inserts the Trace layout (sidebar filters + run list, main panels)
// into pageRoot, then defers to ``legacy.js`` for the heavy lifting.
// The legacy module handles its own state (allRuns, activePath) so
// re-mounting after a Tasks/Results detour keeps the user's filters
// and the currently-selected attempt.

import { bootTrace, refreshTrace } from "./legacy.js";
import { registerPageRefresh } from "../../lib/refresh.js";

const LAYOUT_HTML = `
<div class="layout">
  <aside class="sidebar">
    <section class="filter-panel">
      <div class="filter-head">Filters</div>
      <label class="filter-row">
        <span>Backend</span>
        <select id="filter-backend"></select>
      </label>
      <label class="filter-row">
        <span>Model</span>
        <select id="filter-model"></select>
      </label>
      <label class="filter-row">
        <span>Status</span>
        <select id="filter-status">
          <option value="all">All</option>
          <option value="running">Running</option>
          <option value="pass">Pass</option>
          <option value="fail">Fail</option>
          <option value="executor_incomplete">Executor Incomplete</option>
          <option value="global_timeout">Global Timeout</option>
          <option value="stopped">Stopped</option>
          <option value="budget_exhausted">Budget Exhausted</option>
          <option value="rate_limit">Rate Limit (429)</option>
          <option value="infra_error">Infra Error</option>
          <option value="pre_exec_failed">Pre-Exec Failed</option>
        </select>
      </label>
      <label class="filter-row">
        <span>Task Category</span>
        <select id="filter-category"></select>
      </label>
      <label class="filter-row search">
        <span>Task Search</span>
        <input id="filter-task" type="search" placeholder="task id, model, or category" />
      </label>
    </section>
    <div id="run-list" class="run-list"></div>
  </aside>
  <main class="content">
    <section id="summary" class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Attempt Review</div>
        <h2>Select a run</h2>
        <p>The main view shows one task at a time, with setting-level averages, execution flow, saved artifacts, and supervisor decisions.</p>
      </div>
      <div id="quick-stats" class="quick-stats"></div>
    </section>

    <section class="panel">
      <div class="panel-head flow-panel-head">
        <span>
          <h3>Execution Flow</h3>
          <span class="panel-note">Agent transcript, tool usage, runtime probes, and Codex-guided continuation decisions</span>
        </span>
        <div class="flow-controls">
          <label id="attempt-select-wrap" class="attempt-select hidden">
            <span>Attempt</span>
            <select id="attempt-select"></select>
          </label>
          <div class="flow-filter-group" aria-label="Execution flow filter">
            <button type="button" class="flow-filter-btn active" data-flow-filter="all">All</button>
            <button type="button" class="flow-filter-btn" data-flow-filter="executor">Executor</button>
            <button type="button" class="flow-filter-btn" data-flow-filter="user">User</button>
            <button type="button" class="flow-filter-btn" data-flow-filter="supervisor">Supervisor</button>
          </div>
          <label class="ios-toggle" for="flow-show-tools">
            <span>Show Tools</span>
            <input id="flow-show-tools" type="checkbox" />
            <span class="ios-toggle-track" aria-hidden="true"></span>
          </label>
        </div>
      </div>
      <div class="flow-shell">
        <div id="timeline" class="timeline"></div>
        <aside id="exec-timeline-panel" class="exec-timeline collapsed" aria-label="Execution Timeline">
          <button type="button" class="exec-timeline-toggle" aria-expanded="false" title="Toggle Execution Timeline">
            <span class="exec-timeline-toggle-icon" aria-hidden="true">▸</span>
            <span class="exec-timeline-toggle-label">Execution Timeline</span>
          </button>
          <div class="exec-timeline-body"></div>
        </aside>
      </div>
    </section>

    <details id="grading-panel" class="panel panel-collapsible">
      <summary class="panel-head collapsible-head">
        <span>
          <h3 id="grading-title">Supervisor Assessment</h3>
          <span id="grading-note" class="panel-note">Codex supervisor verdicts, rationale, and safe feedback</span>
        </span>
      </summary>
      <div id="checkpoints" class="checkpoints"></div>
    </details>

    <details class="panel panel-collapsible">
      <summary class="panel-head collapsible-head">
        <span>
          <h3>Saved Results</h3>
          <span class="panel-note">Any notes, screenshots, logs, and other saved artifacts under the task result directory</span>
        </span>
      </summary>
      <div id="outputs" class="outputs"></div>
    </details>
  </main>
</div>
`;

export async function mount(root, route) {
  // Re-render layout every time so DOM ids are fresh after another
  // page (Results/Tasks) cleared pageRoot.
  root.innerHTML = LAYOUT_HTML;
  await bootTrace();
}

registerPageRefresh("trace", async () => {
  await refreshTrace();
});
