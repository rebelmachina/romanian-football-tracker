"use strict";

// Repo used by the Refresh Highlights button (override via window.__OWNER_REPO__).
const OWNER_REPO = window.__OWNER_REPO__ || "rebelmachina/romanian-football-tracker";
const POS = { Goalkeeper: "GK", Defender: "DEF", Midfielder: "MID", Forward: "FWD" };

let STATE = { players: [], filter: "" };

function posAbbr(p) { return POS[p] || "UNK"; }

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function teamMark(name, myTeam) {
  const a = String(name || "").toLowerCase();
  const b = String(myTeam || "").toLowerCase();
  const mine = b && (a.includes(b) || b.includes(a));
  return `<span class="${mine ? "mine" : ""}">${esc(name)}</span>`;
}

function contribBadges(r) {
  const g = r.player_goals || 0, a = r.player_assists || 0;
  const out = [];
  if (g > 0)
    out.push(`<span class="ga goals" title="${g} gol${g > 1 ? "uri" : ""} în acest meci">⚽${g > 1 ? "×" + g : ""}</span>`);
  if (a > 0)
    out.push(`<span class="ga assists" title="${a} pas${a > 1 ? "e" : "ă"} decisiv${a > 1 ? "e" : "ă"}">👟${a > 1 ? "×" + a : ""}</span>`);
  return out.join("");
}

function resultRow(r, myTeam) {
  const links = [];
  if (r.youtube_url)
    links.push(`<a class="yt" href="${esc(r.youtube_url)}" target="_blank" rel="noopener" title="Highlights YouTube">▶</a>`);
  if (r.flashscore_url)
    links.push(`<a href="${esc(r.flashscore_url)}" target="_blank" rel="noopener" title="Flashscore">↗</a>`);
  const fix = `${teamMark(r.home_team, myTeam)} <span class="sc">${esc(r.score)}</span> ${teamMark(r.away_team, myTeam)}`;
  return `<div class="res">
    <span class="date">${esc(r.date)}</span>
    <span class="fix">${fix}</span>
    <span class="res-right">${contribBadges(r)}${links.join("")}</span>
  </div>`;
}

function formDots(results) {
  return results.slice(0, 5).map(r =>
    `<span class="dot ${esc(r.result || "")}">${esc(r.result || "·")}</span>`).join("");
}

function statBlock(s) {
  const cells = [
    ["g", s.goals, "goluri"],
    ["a", s.assists, "assist"],
    ["", s.appearances, "meciuri"],
    ["", s.minutes ? s.minutes + "'" : "—", "minute"],
  ];
  return cells.map(([cls, val, lbl]) =>
    `<div class="stat ${cls}"><b>${esc(val)}</b><span>${lbl}</span></div>`).join("");
}

function card(p) {
  const results = p.results || [];
  const shown = results.slice(0, 5).map(r => resultRow(r, p.team)).join("");
  const rest = results.slice(5).map(r => resultRow(r, p.team)).join("");
  const toggle = results.length > 5
    ? `<button class="showall" data-open="0">+ toate cele ${results.length} meciuri</button>
       <div class="more" hidden>${rest}</div>` : "";
  const rating = p.season_stats.rating && p.season_stats.rating !== "-"
    ? `<span class="rating">★ ${esc(p.season_stats.rating)}</span>` : "";
  return `<div class="card">
    <div class="card-top">
      <div>
        <div class="name">${esc(p.name)}</div>
        <div class="team">${esc(p.team || "—")} ${rating}</div>
      </div>
      <span class="pos ${posAbbr(p.position)}">${posAbbr(p.position)}</span>
    </div>
    <div class="stats">${statBlock(p.season_stats)}</div>
    <div class="form">${formDots(results)}</div>
    <div class="results">${shown}${toggle}</div>
  </div>`;
}

function matchesFilter(p, f) {
  if (!f) return true;
  return (p.name + " " + (p.team || "") + " " + (p.group || "")).toLowerCase().includes(f);
}

function render() {
  const app = document.getElementById("app");
  const f = STATE.filter.trim().toLowerCase();
  const groups = {};
  for (const p of STATE.players) {
    if (!matchesFilter(p, f)) continue;
    (groups[p.group || "Alții"] ??= []).push(p);
  }
  const names = Object.keys(groups).sort((a, b) =>
    groups[b].length - groups[a].length || a.localeCompare(b));
  if (!names.length) { app.innerHTML = `<p class="loading">Niciun rezultat.</p>`; return; }

  app.innerHTML = names.map(g => {
    const players = groups[g].sort((a, b) =>
      (b.season_stats.goals + b.season_stats.assists) - (a.season_stats.goals + a.season_stats.assists));
    const closed = localStorage.getItem("lg:" + g) === "closed" && !f;
    return `<section class="league">
      <div class="league-head" data-group="${esc(g)}">
        <span class="caret">${closed ? "▸" : "▾"}</span>
        <h2>${esc(g)}</h2>
        <span class="count">${players.length}</span>
      </div>
      <div class="grid" ${closed ? "hidden" : ""}>${players.map(card).join("")}</div>
    </section>`;
  }).join("");
}

function onClick(e) {
  const themeBtn = e.target.closest(".theme-btn");
  if (themeBtn) { applyTheme(themeBtn.dataset.theme); return; }
  const showall = e.target.closest(".showall");
  if (showall) {
    const more = showall.nextElementSibling;
    const open = showall.dataset.open === "1";
    more.hidden = open;
    showall.dataset.open = open ? "0" : "1";
    showall.textContent = open
      ? `+ toate cele ${more.children.length + 5} meciuri` : "− mai puține";
    return;
  }
  const head = e.target.closest(".league-head");
  if (head) {
    const grid = head.nextElementSibling;
    grid.hidden = !grid.hidden;
    head.querySelector(".caret").textContent = grid.hidden ? "▸" : "▾";
    localStorage.setItem("lg:" + head.dataset.group, grid.hidden ? "closed" : "open");
  }
}

function getToken() { try { return localStorage.getItem("gh_token"); } catch { return null; } }
function setToken(t) { try { t ? localStorage.setItem("gh_token", t) : localStorage.removeItem("gh_token"); } catch {} }

async function triggerHighlights() {
  const btn = document.getElementById("refresh");
  let token = window.__GH_TOKEN__ || getToken();
  if (!token) {
    const entered = prompt(
      "Pentru a porni actualizarea highlights direct din pagină, lipește un GitHub " +
      "fine-grained token cu permisiunea Actions: Write pe acest repo.\n\n" +
      "Se salvează DOAR în acest browser (localStorage) — niciodată în site. " +
      "Anulează pentru a deschide în schimb pagina Actions.");
    if (!entered) {
      window.open(`https://github.com/${OWNER_REPO}/actions/workflows/highlights.yml`, "_blank");
      return;
    }
    token = entered.trim();
    setToken(token);
  }
  btn.disabled = true; btn.textContent = "Se declanșează…";
  try {
    const res = await fetch(
      `https://api.github.com/repos/${OWNER_REPO}/actions/workflows/highlights.yml/dispatches`,
      { method: "POST",
        headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28" },
        body: JSON.stringify({ ref: "main" }) });
    if (res.status === 204) {
      btn.textContent = "✓ Pornit (~2 min)";
    } else if (res.status === 401 || res.status === 403) {
      setToken(null);
      btn.textContent = "Token invalid";
      alert("Tokenul a fost respins și șters. Încearcă din nou cu unul valid (Actions: Write).");
    } else {
      btn.textContent = "Eșuat (" + res.status + ")";
    }
  } catch { btn.textContent = "Eroare rețea"; }
  finally { setTimeout(() => { btn.disabled = false; btn.textContent = "↻ Highlights"; }, 4000); }
}

/* ---- Theme (system / light / dark) ---- */
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === "light" || mode === "dark") root.setAttribute("data-theme", mode);
  else root.removeAttribute("data-theme");
  document.querySelectorAll(".theme-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.theme === mode));
  try { localStorage.setItem("theme", mode); } catch {}
}
function initTheme() {
  let mode = "system";
  try { mode = localStorage.getItem("theme") || "system"; } catch {}
  applyTheme(mode);
}

/* ---- Intro / cheatsheet dialog ---- */
function openIntro() {
  const d = document.getElementById("intro");
  if (typeof d.showModal === "function") d.showModal();
  else d.setAttribute("open", "");
}
function initIntro() {
  const dlg = document.getElementById("intro");
  document.getElementById("help").addEventListener("click", openIntro);
  document.getElementById("intro-close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); }); // backdrop
  let seen = false;
  try { seen = localStorage.getItem("seen_intro") === "1"; } catch {}
  if (!seen) {
    openIntro();
    try { localStorage.setItem("seen_intro", "1"); } catch {}
  }
}

function boot(data) {
  STATE.players = data.players || [];
  const totalGoals = STATE.players.reduce((s, p) => s + (p.season_stats?.goals || 0), 0);
  document.getElementById("summary").textContent =
    `${STATE.players.length} jucători · ${totalGoals} goluri în acest sezon`;
  if (data.updated_at) {
    document.getElementById("updated").textContent =
      "Actualizat: " + new Date(data.updated_at).toLocaleString("ro-RO",
        { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  render();
}

initTheme();
initIntro();
document.addEventListener("click", onClick);
document.getElementById("refresh").addEventListener("click", triggerHighlights);
document.getElementById("filter").addEventListener("input", e => {
  STATE.filter = e.target.value; render();
});

fetch("./data.json")
  .then(r => r.ok ? r.json() : Promise.reject())
  .catch(() => fetch("./data.sample.json").then(r => r.json()))
  .then(boot)
  .catch(() => {
    document.getElementById("app").innerHTML =
      `<p class="loading">Nu s-au putut încărca datele.</p>`;
  });
