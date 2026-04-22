// Kai miniapp UI
(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) { try { tg.ready(); tg.expand(); } catch (_) {} }

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  // ---------- tabs ----------
  $$(".tab").forEach((t) => {
    t.addEventListener("click", () => {
      $$(".tab").forEach((x) => x.classList.remove("active"));
      $$(".pane").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      const target = t.dataset.tab;
      document.querySelector(`.pane[data-pane="${target}"]`).classList.add("active");
      loadTab(target);
    });
  });

  // ---------- helpers ----------
  function fmt(n, digits = 2) {
    if (typeof n !== "number") return "—";
    return n.toFixed(digits);
  }
  function timeAgo(iso) {
    if (!iso) return "—";
    const t = new Date(iso).getTime();
    const sec = Math.max(0, (Date.now() - t) / 1000);
    if (sec < 60) return Math.floor(sec) + "с назад";
    if (sec < 3600) return Math.floor(sec / 60) + "м назад";
    if (sec < 86400) return Math.floor(sec / 3600) + "ч назад";
    return Math.floor(sec / 86400) + "д назад";
  }
  // Compute base path so the app works under any prefix (/, /kai/, etc.)
  const BASE = (() => {
    const p = window.location.pathname || "/";
    return p.endsWith("/") ? p : p.replace(/[^/]*$/, "");
  })();
  async function fetchJSON(path) {
    const url = BASE + path.replace(/^\//, "");
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + " " + r.status);
    return r.json();
  }

  const RU_CHEM = {
    dopamine: "дофамин", serotonin: "серотонин", cortisol: "кортизол",
    oxytocin: "окситоцин", norepinephrine: "норэпинефрин", melatonin: "мелатонин",
  };
  const RU_TEMP = {
    openness: "открытость", conscientiousness: "сознательность",
    extraversion: "экстраверсия", agreeableness: "доброжелательность",
    neuroticism: "невротичность",
  };
  const HORIZONS = { immediate: "сейчас", shortterm: "ближнее", longterm: "дальнее", existential: "экзистенциальное" };

  // ---------- renderers ----------
  function renderState(d) {
    $("#kai-name").textContent = d.name || "Kai";
    $("#kai-age").textContent = `${d.days_alive} дн.`;
    $("#kai-concept").textContent = d.self_concept || "";

    const bars = $("#chem-bars");
    bars.innerHTML = "";
    Object.entries(d.neuro).forEach(([k, v]) => {
      const row = document.createElement("div");
      row.className = "chem-row";
      const pct = Math.max(0, Math.min(1, v)) * 100;
      row.innerHTML =
        `<span>${RU_CHEM[k] || k}</span>` +
        `<div class="chem-bar-bg"><div class="chem-bar-fill" style="width:${pct}%"></div></div>` +
        `<span class="v">${fmt(v)}</span>`;
      bars.appendChild(row);
    });
    $("#neuro-words").textContent = d.neuro_words || "";

    $("#mood-label").textContent = d.mood.label || "—";
    $("#mood-dur").textContent = `${fmt(d.mood.duration_hours, 1)} ч`;

    const drives = $("#drives");
    drives.innerHTML = "";
    [["к общению", d.drives.social], ["к творчеству", d.drives.create], ["к исследованию", d.drives.explore]]
      .forEach(([k, v]) => {
        drives.insertAdjacentHTML("beforeend",
          `<div class="k">${k}</div><div class="v">${fmt(v)}</div>`);
      });

    const r = $("#resources");
    r.innerHTML = "";
    const rs = d.resources;
    [
      ["бюджет осталось", `$${fmt(rs.api_budget_remaining_usd, 3)}`],
      ["потрачено сегодня", `$${fmt(rs.api_spent_today_usd, 3)}`],
      ["размер памяти", rs.memory_size + ""],
      ["аптайм", `${fmt(rs.uptime_hours, 1)} ч`],
      ["ошибок за час", rs.error_rate_1h + ""],
      ["сплю", d.is_sleeping ? "да" : "нет"],
    ].forEach(([k, v]) => {
      r.insertAdjacentHTML("beforeend", `<div class="k">${k}</div><div class="v">${v}</div>`);
    });

    // bond pane: refresh from same payload
    const b = $("#brother");
    b.innerHTML = "";
    const bm = d.brother;
    [
      ["глубина связи", fmt(bm.relationship_depth)],
      ["настроение в последний раз", bm.last_seen_mood || "—"],
      ["часов с последнего", fmt(bm.hours_since_last, 1)],
      ["всего сообщений", bm.total_messages + ""],
    ].forEach(([k, v]) => {
      b.insertAdjacentHTML("beforeend", `<div class="k">${k}</div><div class="v">${v}</div>`);
    });
    $("#ling-hints").textContent = bm.linguistic_hints || "";

    const tEl = $("#temperament");
    tEl.innerHTML = "";
    Object.entries(d.temperament).forEach(([k, v]) => {
      const pct = Math.max(0, Math.min(1, v)) * 100;
      tEl.insertAdjacentHTML("beforeend",
        `<div class="temp-row"><span>${RU_TEMP[k] || k}</span>` +
        `<div class="chem-bar-bg"><div class="chem-bar-fill" style="width:${pct}%"></div></div>` +
        `<span class="v">${fmt(v)}</span></div>`);
    });

    const vEl = $("#values");
    vEl.innerHTML = "";
    d.values_top.forEach((v) => {
      vEl.insertAdjacentHTML("beforeend", `<li>${v.name} <span class="muted small">(${fmt(v.weight)})</span></li>`);
    });
    $("#meta-words").textContent = d.meta_words || "";

    $("#updated").textContent = "обновлено " + new Date().toLocaleTimeString("ru-RU");
  }

  async function loadState() {
    try { renderState(await fetchJSON("api/state")); }
    catch (e) { console.error(e); }
  }

  async function loadMemory() {
    try {
      const recent = await fetchJSON("api/recent");
      const recEl = $("#recent");
      recEl.innerHTML = "";
      if (!recent.items.length) {
        recEl.innerHTML = '<p class="empty">тишина пока</p>';
      } else {
        recent.items.slice(0, 25).forEach((m) => {
          const tags = (m.tags || "").split(",").filter(Boolean);
          const tagHtml = tags.map((t) => `<span class="tag">${t}</span>`).join(" ");
          recEl.insertAdjacentHTML("beforeend",
            `<div class="item">${escapeHtml(m.text || "")}` +
            `<div class="meta">${timeAgo(m.timestamp)} ${tagHtml}` +
            (m.emotion ? ` · ${m.emotion}` : "") + `</div></div>`);
        });
      }
      const cr = await fetchJSON("api/creations");
      const cEl = $("#creations");
      cEl.innerHTML = "";
      if (!cr.items.length) {
        cEl.innerHTML = '<p class="empty">пока ничего не создал</p>';
      } else {
        cr.items.slice().reverse().forEach((c) => {
          cEl.insertAdjacentHTML("beforeend",
            `<div class="creation"><div class="form">${c.form} · ${timeAgo(c.ts)}</div>${escapeHtml(c.text)}</div>`);
        });
      }
    } catch (e) { console.error(e); }
  }

  async function loadMind() {
    try {
      const n = await fetchJSON("api/narrative");
      $("#narrative").textContent = n.current_story || "история ещё формируется";
      $("#narrative-ts").textContent = n.last_updated ? "обновлено " + timeAgo(n.last_updated) : "";

      const cur = await fetchJSON("api/curiosity");
      const curEl = $("#curiosity");
      curEl.innerHTML = "";
      if (!cur.items.length) curEl.innerHTML = '<p class="empty">все вопросы пока ясны</p>';
      cur.items.forEach((q) => {
        curEl.insertAdjacentHTML("beforeend",
          `<div class="item">${escapeHtml(q.text)}<div class="meta">вес ${fmt(q.weight)} · ${timeAgo(q.asked_at)}</div></div>`);
      });

      const b = await fetchJSON("api/beliefs");
      const bEl = $("#beliefs");
      bEl.innerHTML = "";
      if (!b.items.length) bEl.innerHTML = '<p class="empty">убеждений пока нет</p>';
      b.items.forEach((bi) => {
        const pct = Math.max(0, Math.min(1, bi.confidence)) * 100;
        bEl.insertAdjacentHTML("beforeend",
          `<div class="item">${escapeHtml(bi.text)}` +
          `<div class="meta">уверенность ${fmt(bi.confidence)}` +
          `<span class="confidence-bar"><span style="width:${pct}%"></span></span> · подтверждений ${bi.evidence}</div></div>`);
      });

      const p = await fetchJSON("api/predictions");
      $("#calibration").textContent = `точность прогнозов: ${fmt(p.calibration)}`;
      const pEl = $("#predictions");
      pEl.innerHTML = "";
      if (!p.items.length) pEl.innerHTML = '<p class="empty">прогнозов нет</p>';
      p.items.slice().reverse().forEach((pr) => {
        const status = pr.resolved ? (pr.correct ? "✓ сбылось" : "✗ нет") : "ожидает";
        pEl.insertAdjacentHTML("beforeend",
          `<div class="item"><b>${escapeHtml(pr.about)}</b>: ${escapeHtml(pr.expected)}` +
          `<div class="meta">${status} · к ${timeAgo(pr.by_when)} · уверенность ${fmt(pr.confidence)}</div></div>`);
      });

      const g = await fetchJSON("api/goals");
      const gEl = $("#goals");
      gEl.innerHTML = "";
      Object.keys(HORIZONS).forEach((h) => {
        const list = g[h] || [];
        if (!list.length) return;
        const block = document.createElement("div");
        block.className = "horizon-block";
        block.innerHTML = `<div class="h">${HORIZONS[h]}</div>`;
        list.forEach((it) => {
          block.insertAdjacentHTML("beforeend",
            `<div class="item">${escapeHtml(it.text)}<div class="meta">вес ${fmt(it.weight)}</div></div>`);
        });
        gEl.appendChild(block);
      });
    } catch (e) { console.error(e); }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function loadTab(name) {
    if (name === "state" || name === "bond") loadState();
    if (name === "memory") loadMemory();
    if (name === "mind") loadMind();
  }

  // initial + auto-refresh of state every 30s
  loadState();
  setInterval(() => {
    const active = document.querySelector(".tab.active").dataset.tab;
    loadTab(active);
  }, 30000);
})();
