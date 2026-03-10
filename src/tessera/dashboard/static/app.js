/* Tessera Dashboard */

const POLL_INTERVAL = 10000;

let savingsChart = null;
let _statPrev = {};
let _currentSessionId = "";

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

function animateCount(el, from, to, duration = 600) {
  if (from === to) { el.textContent = to.toLocaleString(); return; }
  const start = performance.now();
  function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(from + (to - from) * ease).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function relativeTime(unix) {
  if (!unix) return "";
  const diff = Date.now() - unix * 1000;
  if (diff < 60000)    return "just now";
  if (diff < 3600000)  return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return new Date(unix * 1000).toLocaleDateString();
}

function shortDate(unix) {
  if (!unix) return "";
  return new Date(unix * 1000).toLocaleString([], {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// ── Session selector ──────────────────────────────────────────────────────────

async function loadSessions() {
  const sessions = await fetchJSON("/api/sessions");
  const sel = document.getElementById("session-select");
  const current = sel.value;
  sel.innerHTML = '<option value="">All sessions</option>';
  sessions.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.id;
    const date = s.started_at ? shortDate(s.started_at) : s.id.slice(0, 8);
    const saved = s.chars_saved > 0 ? ` · ${(s.chars_saved / 1000).toFixed(1)}k saved` : "";
    opt.textContent = `${date}${saved}`;
    sel.appendChild(opt);
  });
  if (current) sel.value = current;
}

// ── Stats ─────────────────────────────────────────────────────────────────────

async function loadStats() {
  const s = await fetchJSON("/api/stats");
  const fields = {
    files: "stat-files",
    symbols: "stat-symbols",
    edges: "stat-edges",
    sessions: "stat-sessions",
  };
  for (const [key, id] of Object.entries(fields)) {
    const val = s[key] ?? 0;
    animateCount(document.getElementById(id), _statPrev[key] ?? 0, val);
    _statPrev[key] = val;
  }
  const pathEl = document.getElementById("project-path");
  if (s.project_root) pathEl.textContent = s.project_root;
  document.getElementById("last-updated").textContent =
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Token savings chart ───────────────────────────────────────────────────────

async function loadSavings() {
  const rows = await fetchJSON("/api/savings");
  const active = rows.filter(r => r.chars_saved > 0 || r.chars_read_total > 0);

  const labels   = active.map(r => r.started_at ? shortDate(r.started_at) : r.id.slice(0, 8));
  const data     = active.map(r => r.chars_saved || 0);
  const totalSaved = data.reduce((a, b) => a + b, 0);
  const totalRead  = active.reduce((a, r) => a + (r.chars_read_total || 0), 0);
  const pct = totalRead > 0 ? Math.round((totalSaved / totalRead) * 100) : 0;

  document.getElementById("savings-summary").textContent = totalSaved > 0
    ? `${totalSaved.toLocaleString()} chars · ${pct}% reduction`
    : "No savings data yet";

  const ctx = document.getElementById("savings-chart").getContext("2d");

  if (savingsChart) {
    savingsChart.data.labels = labels;
    savingsChart.data.datasets[0].data = data;
    savingsChart.update("active");
    return;
  }

  savingsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: "rgba(14, 107, 86, 0.75)",
        hoverBackgroundColor: "#be5a28",
        borderRadius: 5,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#182022",
          titleColor: "rgba(255,255,255,0.7)",
          bodyColor: "#fff",
          padding: 10,
          callbacks: {
            label: ctx => `${ctx.raw.toLocaleString()} chars saved`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#8A9198", font: { size: 10 }, maxRotation: 40 },
          border: { display: false },
        },
        y: {
          grid: { color: "#D9DEE3", lineWidth: 1 },
          ticks: {
            color: "#8A9198",
            font: { size: 11 },
            callback: v => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v,
          },
          border: { display: false },
        },
      },
    },
  });
}

// ── Hot files ─────────────────────────────────────────────────────────────────

async function loadHotFiles() {
  const qs = _currentSessionId
    ? `?session_id=${encodeURIComponent(_currentSessionId)}&limit=10`
    : "?limit=10";
  const rows = await fetchJSON(`/api/files/top${qs}`);
  const container = document.getElementById("hot-files-list");
  container.innerHTML = "";

  if (!rows.length) {
    container.innerHTML = '<div class="feed-empty">No file activity yet.</div>';
    document.getElementById("hot-files-meta").textContent = "";
    return;
  }

  const max = rows[0].hit_count;
  document.getElementById("hot-files-meta").textContent = `top ${rows.length}`;

  rows.forEach(r => {
    const pct   = Math.round((r.hit_count / max) * 100);
    const parts = r.file_path.replace(/\\/g, "/").split("/");
    const fname = parts[parts.length - 1];
    const dir   = parts.length > 1 ? parts[parts.length - 2] + "/" : "";

    const item = document.createElement("div");
    item.className = "hot-file-row";
    item.title = r.file_path;
    item.innerHTML = `
      <div class="hot-file-name">
        <span class="hot-file-dir">${dir}</span>${fname}
      </div>
      <div class="hot-file-bar-wrap">
        <div class="hot-file-bar" style="width:${pct}%"></div>
      </div>
      <div class="hot-file-count">${r.hit_count}</div>
    `;
    container.appendChild(item);
  });
}

// ── Decisions ─────────────────────────────────────────────────────────────────

async function loadDecisions() {
  const qs = _currentSessionId
    ? `?session_id=${encodeURIComponent(_currentSessionId)}`
    : "";
  const rows = await fetchJSON(`/api/decisions${qs}`);
  const container = document.getElementById("decisions-list");
  container.innerHTML = "";
  document.getElementById("decisions-count").textContent =
    rows.length ? `${rows.length} locked` : "";

  if (!rows.length) {
    container.innerHTML = '<div class="decision-empty">No decisions recorded yet.</div>';
    return;
  }

  rows.slice(0, 20).forEach(d => {
    let files = [];
    try { files = JSON.parse(d.files || "[]"); } catch {}

    const card = document.createElement("div");
    card.className = "decision-card";
    card.innerHTML = `
      <div class="decision-body">${d.summary}</div>
      <div class="decision-meta">
        ${d.scope ? `<span class="decision-tag decision-scope">${d.scope}</span>` : ""}
        ${files.length ? `<span class="decision-tag decision-files">${files.length} file${files.length !== 1 ? "s" : ""}</span>` : ""}
        ${d.created_at ? `<span class="decision-time">${relativeTime(d.created_at)}</span>` : ""}
      </div>
    `;
    container.appendChild(card);
  });
}

// ── Plans ─────────────────────────────────────────────────────────────────────

async function loadPlans() {
  const plans = await fetchJSON("/api/plans");
  const container = document.getElementById("plans-list");
  container.innerHTML = "";

  if (!plans.length) {
    container.innerHTML = '<p class="feed-empty">No plans found.</p>';
    return;
  }

  plans.forEach(p => {
    const done  = p.checklist.filter(i => i.status === "done").length;
    const total = p.checklist.length;
    const pct   = total ? Math.round((done / total) * 100) : 0;
    const status     = p.plan?.status ?? "none";
    const badgeClass = status === "done" ? "plan-badge-done" : "plan-badge-active";
    const badgeLabel = status === "none" ? "no plan" : status;
    const hasItems   = total > 0;

    const card = document.createElement("div");
    card.className = "plan-card" + (hasItems ? " plan-expandable" : "");
    card.innerHTML = `
      <div class="plan-card-header">
        <span class="plan-card-title">${p.project} / ${p.subtask}</span>
        <div class="plan-header-right">
          <span class="plan-badge ${badgeClass}">${badgeLabel}</span>
          ${hasItems ? '<span class="plan-chevron">&#8964;</span>' : ""}
        </div>
      </div>
      <div class="checklist-bar">
        <div class="checklist-fill" style="width:${pct}%"></div>
      </div>
      <p class="plan-meta">${done}/${total} tasks complete</p>
      ${hasItems ? `<ul class="plan-checklist">${
        p.checklist.map(i => `
          <li class="checklist-item checklist-${i.status || "pending"}">
            <span class="checklist-icon">${i.status === "done" ? "&#10003;" : "&#9675;"}</span>
            <span class="checklist-text">${i.description || ""}</span>
          </li>`).join("")
      }</ul>` : ""}
    `;

    if (hasItems) {
      card.querySelector(".plan-card-header").addEventListener("click", () => {
        card.classList.toggle("plan-expanded");
      });
    }

    container.appendChild(card);
  });
}

// ── Actions feed ──────────────────────────────────────────────────────────────

const BADGE_CLASS = {
  read:     "badge-read",
  edit:     "badge-edit",
  scan:     "badge-scan",
  continue: "badge-continue",
  retrieve: "badge-retrieve",
};

async function loadActions() {
  const qs = _currentSessionId
    ? `?session_id=${encodeURIComponent(_currentSessionId)}`
    : "";
  const rows = await fetchJSON(`/api/actions${qs}`);

  // Action type distribution pills
  const counts = {};
  rows.forEach(r => {
    const type = (r.action_type || "other").toLowerCase().replace(/^graph_/, "");
    counts[type] = (counts[type] || 0) + 1;
  });
  const countsEl = document.getElementById("action-type-counts");
  countsEl.innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([type, n]) => {
      const cls = BADGE_CLASS[type] || "badge-default";
      return `<span class="type-pill ${cls}">${type} <strong>${n}</strong></span>`;
    })
    .join("");

  const feed = document.getElementById("actions-feed");
  feed.innerHTML = "";

  if (!rows.length) {
    feed.innerHTML = '<div class="feed-empty">No activity yet.</div>';
    return;
  }

  rows.slice(0, 50).forEach(r => {
    const raw   = (r.action_type || "").toLowerCase().replace(/^graph_/, "");
    const badge = BADGE_CLASS[raw] || "badge-default";
    const label = raw || r.action_type;
    const file  = r.file_path ? r.file_path.split("/").slice(-2).join("/") : "";
    const query = (r.query || "").slice(0, 72);

    const row = document.createElement("div");
    row.className = "action-row";
    row.innerHTML = `
      <span class="action-badge ${badge}">${label}</span>
      <div class="action-body">
        ${file  ? `<div class="action-file">${file}</div>`   : ""}
        ${query ? `<div class="action-query">${query}</div>` : ""}
      </div>
      <span class="action-time">${relativeTime(r.created_at)}</span>
    `;
    feed.appendChild(row);
  });
}

// ── Poll loop ─────────────────────────────────────────────────────────────────

async function refresh() {
  await Promise.allSettled([
    loadStats(),
    loadSessions(),
    loadSavings(),
    loadDecisions(),
    loadPlans(),
    loadActions(),
    loadHotFiles(),
    loadGraphInfo(),
    loadTokenSummary(),
    loadGraphTree(),
  ]);
}

// ── Session filter wiring ─────────────────────────────────────────────────────

function updateFilterHint() {
  const hint = document.getElementById("filter-hint");
  const sel  = document.getElementById("session-select");
  if (_currentSessionId) {
    const label = sel.options[sel.selectedIndex]?.textContent || "selected session";
    hint.textContent = `Filtered: ${label}`;
    hint.classList.add("filter-hint-active");
  } else {
    hint.textContent = "Showing all sessions";
    hint.classList.remove("filter-hint-active");
  }
}

document.getElementById("session-select").addEventListener("change", e => {
  _currentSessionId = e.target.value;
  document.getElementById("session-clear").style.display = _currentSessionId ? "inline-flex" : "none";
  updateFilterHint();
  Promise.allSettled([loadActions(), loadDecisions(), loadHotFiles()]);
});

document.getElementById("session-clear").addEventListener("click", () => {
  _currentSessionId = "";
  document.getElementById("session-select").value = "";
  document.getElementById("session-clear").style.display = "none";
  updateFilterHint();
  Promise.allSettled([loadActions(), loadDecisions(), loadHotFiles()]);
});

// init
document.getElementById("session-clear").style.display = "none";
refresh();
setInterval(refresh, POLL_INTERVAL);
