/* Tessera Dashboard — new sections JS */

let tokenChart = null;
let _scanPollTimer = null;

// ── Live Token Monitor ────────────────────────────────────────────────────────

async function loadBenchLog() {
  let data;
  try {
    data = await fetchJSON("/api/bench-log");
  } catch (e) {
    return;
  }

  const fmt = n => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);

  const el = id => document.getElementById(id);
  el("monitor-saved").textContent    = fmt(data.saved || 0);
  el("monitor-read").textContent     = fmt(data.without_graph || 0);
  el("monitor-pct").textContent      = `${data.savings_pct || 0}%`;
  el("monitor-sessions").textContent = String(data.sessions_logged || 0);
  el("monitor-entries").textContent  = String((data.entries || []).length);

  const tbody = el("monitor-tbody");
  tbody.innerHTML = "";
  (data.entries || []).slice(0, 15).forEach(e => {
    const tr = document.createElement("tr");
    const sid = (e.session_id || "").slice(0, 8);
    const ts  = e.created_at ? new Date(e.created_at * 1000).toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit",
    }) : "";
    tr.innerHTML = `
      <td>${sid}</td>
      <td>${e.turn_number ?? "—"}</td>
      <td>${fmt(e.chars_saved || 0)}</td>
      <td>${fmt(e.chars_read_total || 0)}</td>
      <td>${ts}</td>
    `;
    tbody.appendChild(tr);
  });

  if (!data.entries || !data.entries.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="5" style="text-align:center;color:var(--os-muted);padding:1rem">No token data yet.</td>';
    tbody.appendChild(tr);
  }
}

// ── Information Graph ─────────────────────────────────────────────────────────

async function loadGraphInfo() {
  let rows;
  try {
    rows = await fetchJSON("/api/graph/nodes");
  } catch (e) {
    return;
  }

  const tbody = document.getElementById("graph-nodes-tbody");
  tbody.innerHTML = "";

  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="3" style="text-align:center;color:var(--os-muted);padding:1rem">No graph data — run a scan.</td>';
    tbody.appendChild(tr);
    return;
  }

  const fmt = n => n >= 1024 ? `${(n / 1024).toFixed(1)}k` : String(n || 0);
  rows.slice(0, 60).forEach(r => {
    const parts = (r.path || "").replace(/\\/g, "/").split("/");
    const name  = parts[parts.length - 1];
    const dir   = parts.length > 1 ? "…/" + parts[parts.length - 2] + "/" : "";
    const tr    = document.createElement("tr");
    tr.title    = r.path || "";
    tr.innerHTML = `
      <td title="${r.path || ""}"><span style="color:var(--os-muted)">${dir}</span>${name}</td>
      <td>${r.extension || "—"}</td>
      <td>${fmt(r.size)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function _startScanPoll() {
  const statusEl = document.getElementById("scan-status");
  const btn = document.getElementById("btn-scan");

  if (_scanPollTimer) clearInterval(_scanPollTimer);
  _scanPollTimer = setInterval(async () => {
    let st;
    try { st = await fetchJSON("/api/scan/status"); } catch { return; }
    if (!st.running) {
      clearInterval(_scanPollTimer);
      _scanPollTimer = null;
      btn.disabled = false;
      if (st.result && st.result.ok) {
        const { files_scanned: scanned = 0, files_skipped: skipped = 0, total = 0 } = st.result;
        statusEl.textContent = `Scan complete — ${scanned} updated, ${skipped} unchanged, ${total} total.`;
        loadGraphInfo();
      } else if (st.result) {
        statusEl.textContent = `Scan error: ${st.result.error || "unknown"}`;
      } else {
        statusEl.textContent = "";
      }
    }
  }, 1500);
}

document.getElementById("btn-scan").addEventListener("click", async () => {
  const btn = document.getElementById("btn-scan");
  const statusEl = document.getElementById("scan-status");
  btn.disabled = true;
  statusEl.textContent = "Starting scan…";
  try {
    const res = await fetch("/api/scan", { method: "POST" });
    if (res.status === 409) {
      statusEl.textContent = "Scan already running…";
    } else {
      statusEl.textContent = "Scanning…";
    }
    _startScanPoll();
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
    btn.disabled = false;
  }
});

document.getElementById("btn-refresh-graph").addEventListener("click", () => {
  loadGraphInfo();
});

// ── Token Usage Summary ───────────────────────────────────────────────────────

async function loadTokenSummary() {
  let data;
  try {
    data = await fetchJSON("/api/token-summary");
  } catch (e) {
    return;
  }

  document.getElementById("token-summary-meta").textContent =
    data.event_count ? `${data.event_count} events · ${(data.total_chars / 1000).toFixed(1)}k chars` : "";

  // Session chips
  const chipsEl = document.getElementById("session-chips");
  chipsEl.innerHTML = "";
  Object.entries(data.by_session || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .forEach(([sid, saved]) => {
      const chip = document.createElement("span");
      chip.className = "session-chip";
      chip.textContent = `${sid.slice(0, 8)} · ${(saved / 1000).toFixed(1)}k`;
      chipsEl.appendChild(chip);
    });

  // Chart
  const entries = (data.entries || []).slice(0, 20).reverse();
  const labels  = entries.map((e, i) => `t${e.turn_number ?? i}`);
  const values  = entries.map(e => e.chars_saved || 0);

  const ctx = document.getElementById("token-chart").getContext("2d");
  if (tokenChart) {
    tokenChart.data.labels = labels;
    tokenChart.data.datasets[0].data = values;
    tokenChart.update("active");
  } else {
    tokenChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: "rgba(14, 107, 86, 0.75)",
          hoverBackgroundColor: "#be5a28",
          borderRadius: 4,
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
            titleColor: "rgba(255,255,255,0.6)",
            bodyColor: "#fff",
            padding: 10,
            callbacks: { label: c => `${c.raw.toLocaleString()} chars saved` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#5e6a6f", font: { size: 10 } },
            border: { display: false },
          },
          y: {
            grid: { color: "rgba(212,216,203,0.6)", lineWidth: 1 },
            ticks: {
              color: "#5e6a6f",
              font: { size: 10 },
              callback: v => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v,
            },
            border: { display: false },
          },
        },
      },
    });
  }

  // Detail table
  const tbody = document.getElementById("token-detail-tbody");
  tbody.innerHTML = "";
  if (!data.entries || !data.entries.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="4" style="text-align:center;color:var(--os-muted);padding:1rem">No data yet.</td>';
    tbody.appendChild(tr);
    return;
  }
  data.entries.slice(0, 20).forEach(e => {
    const tr = document.createElement("tr");
    const fmt = n => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n || 0);
    tr.innerHTML = `
      <td>${(e.session_id || "").slice(0, 8)}</td>
      <td>${e.turn_number ?? "—"}</td>
      <td>${fmt(e.chars_saved)}</td>
      <td>${fmt(e.chars_read_total)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Graph Tree ────────────────────────────────────────────────────────────────

async function loadGraphTree() {
  let data;
  try {
    data = await fetchJSON("/api/graph/tree");
  } catch (e) {
    return;
  }
  const pre = document.getElementById("graph-tree-pre");
  pre.textContent = data.tree || "(empty)";
  document.getElementById("graph-tree-meta").textContent =
    data.edge_count ? `${data.edge_count} edges` : "";
}

// ── Init: 5s bench-log interval ───────────────────────────────────────────────

loadBenchLog();
setInterval(loadBenchLog, 5000);
