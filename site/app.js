"use strict";

// Repo used by the Refresh Highlights button (override via window.__OWNER_REPO__).
const OWNER_REPO = window.__OWNER_REPO__ || "rebelmachina/romanian-football-tracker";
const POS = { Goalkeeper: "GK", Defender: "DEF", Midfielder: "MID", Forward: "FWD" };

// League strength: curated top order, then UEFA-ish country coefficient for the rest.
const TOP_LEAGUES = [
  "Serie A (Italy)", "LaLiga (Spain)", "Eredivisie (Netherlands)",
  "Liga Portugal (Portugal)", "Jupiler Pro League (Belgium)",
  "Super Lig (Turkey)", "Super League (Greece)",
  "Championship (England)", "Serie B (Italy)", "LaLiga2 (Spain)", "2. Bundesliga (Germany)",
  "Ekstraklasa (Poland)", "Premiership (Scotland)", "Ligat ha'Al (Israel)",
];
const COUNTRY_RANK = {
  England: 1, Italy: 2, Spain: 3, Germany: 4, France: 5, Netherlands: 6,
  Portugal: 7, Belgium: 8, Turkey: 9, Greece: 10, Russia: 11, Scotland: 12,
  Poland: 13, Israel: 14, Serbia: 15, Cyprus: 16, Hungary: 17, Slovakia: 18,
  Slovenia: 19, Azerbaijan: 20, Bulgaria: 21, Lithuania: 22, Armenia: 23,
  Kazakhstan: 24, Malta: 25,
  "Saudi Arabia": 40, USA: 41, Qatar: 42, "United Arab Emirates": 43, China: 44,
  Thailand: 45, Vietnam: 46, Jordan: 47, Oman: 48, Cambodia: 49,
};
function groupRank(group) {
  const i = TOP_LEAGUES.indexOf(group);
  if (i >= 0) return i;
  const m = group.match(/\(([^)]+)\)\s*$/);
  return 100 + (COUNTRY_RANK[m ? m[1] : ""] ?? 90);
}

const YT_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><rect x="1" y="4.6" width="22" height="14.8" rx="4.2" fill="#FF0000"/><path d="M9.9 8.4v7.2l6-3.6z" fill="#fff"/></svg>`;
const FS_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><rect x="2" y="2.5" width="20" height="19" rx="4.6" fill="#f5471e"/><path d="M13.2 4.7l-6 8.2h3.7l-1.1 5.9 5.9-8.1h-3.6z" fill="#fff"/></svg>`;

function ytId(url) {
  const m = String(url || "").match(/(?:v=|youtu\.be\/|embed\/|shorts\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : null;
}
function ytEmbed(id) {
  const watch = `https://www.youtube.com/watch?v=${id}`;
  return `<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&modestbranding=1"` +
    ` title="Rezumat video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen"` +
    ` allowfullscreen loading="lazy"></iframe></div>` +
    `<a class="video-yt" href="${watch}" target="_blank" rel="noopener">` +
    `${YT_ICON} Nu se încarcă aici? Deschide pe YouTube ↗</a>`;
}

function playVideo(url) {
  const id = ytId(url);
  if (!id) { window.open(url, "_blank", "noopener"); return; }
  if (STATE.view === "arcade") {
    const slot = document.getElementById("mkvideo");
    if (slot) {
      slot.innerHTML = ytEmbed(id) +
        `<button class="video-close" data-close-video>× Închide videoul</button>`;
      slot.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else {
    const dlg = document.getElementById("video-modal");
    document.getElementById("video-slot").innerHTML = ytEmbed(id);
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
  }
}

function clearArcadeVideo() {
  const slot = document.getElementById("mkvideo");
  if (slot) slot.innerHTML = "";
}
function closeVideoModal() {
  const dlg = document.getElementById("video-modal");
  if (dlg) { dlg.close(); document.getElementById("video-slot").innerHTML = ""; }
}

let STATE = { players: [], filter: "", pos: "", league: "", range: "season",
              view: "classic", sel: 0, list: [], sortBy: "league", sortDir: "desc" };

function parseMarketValue(v) {
  const m = String(v || "").match(/([\d.]+)\s*([kmb])?/i);
  if (!m) return 0;
  return (parseFloat(m[1]) || 0) * ({ k: 1e3, m: 1e6, b: 1e9 }[(m[2] || "").toLowerCase()] || 1);
}
function sortKey(p) {
  const s = statsFor(p);
  switch (STATE.sortBy) {
    case "goals": return s.goals || 0;
    case "assists": return s.assists || 0;
    case "minutes": return s.minutes || 0;
    case "age": return p.age || 0;
    case "value": return parseMarketValue(p.market_value);
    default: return 0;
  }
}
function sortValueLabel(p) {
  const s = statsFor(p);
  switch (STATE.sortBy) {
    case "goals": return `${s.goals || 0} G`;
    case "assists": return `${s.assists || 0} A`;
    case "minutes": return `${s.minutes || 0}'`;
    case "age": return p.age ? `${p.age} ani` : "—";
    case "value": return p.market_value || "—";
    default: return "";
  }
}

function rangeCutoff(key) {
  const now = new Date();
  if (key === "ytd") return `${now.getFullYear()}-01-01`;
  const days = { "1y": 365, "2y": 730, "3y": 1095 }[key];
  if (!days) return null;
  return new Date(now.getTime() - days * 86400000).toISOString().slice(0, 10);
}

function resultsFor(p) {
  const all = p.results || [];
  const cut = rangeCutoff(STATE.range);
  return cut ? all.filter(r => r.date >= cut) : all;
}

function gaSum(p) { const s = statsFor(p); return (s.goals || 0) + (s.assists || 0); }

function statsFor(p) {
  if (STATE.range === "season") return p.season_stats || { goals: 0, assists: 0, appearances: 0, minutes: 0 };
  const rs = resultsFor(p);
  return {
    goals: rs.reduce((s, r) => s + (r.player_goals || 0), 0),
    assists: rs.reduce((s, r) => s + (r.player_assists || 0), 0),
    appearances: rs.filter(r => r.player_minutes).length,
    minutes: rs.reduce((s, r) => s + (r.player_minutes || 0), 0),
    rating: null,
  };
}

function posAbbr(p) { return POS[p] || "UNK"; }

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function initials(name) {
  return String(name || "?").trim().split(/\s+/).map(w => w[0]).slice(0, 2).join("").toUpperCase();
}

function crestStack(p) {
  let teams = (p.career_teams && p.career_teams.length) ? p.career_teams : [];
  if (!teams.length && p.team_logo) teams = [{ name: p.team, logo: p.team_logo, current: true }];
  if (!teams.length) return "";
  // current first (bigger, in front); past clubs fan out behind
  const badges = teams.map((t, i) =>
    `<img class="crest ${t.current ? "cur" : "past"}" style="z-index:${20 - i}"` +
    ` src="${esc(t.logo)}" alt="" title="${esc(t.name)}${t.current ? " (actual)" : ""}" loading="lazy">`
  ).join("");
  return `<span class="crests">${badges}</span>`;
}

function avatar(p, cls) {
  if (p.photo)
    return `<span class="avatar ${cls}" style="background-image:url('${esc(p.photo)}')"></span>`;
  return `<span class="avatar ${cls} ini pos-${posAbbr(p.position)}">${esc(initials(p.name))}</span>`;
}

function teamMark(name, myTeam) {
  const a = String(name || "").toLowerCase();
  const b = String(myTeam || "").toLowerCase();
  const mine = b && (a.includes(b) || b.includes(a));
  return `<span class="${mine ? "mine" : ""}">${esc(name)}</span>`;
}

function contribBadges(r) {
  const g = r.player_goals || 0, a = r.player_assists || 0;
  const gm = r.goal_minutes || [], am = r.assist_minutes || [];
  const out = [];
  if (g > 0) {
    const label = gm.length ? "⚽ " + gm.join(", ") : "⚽".repeat(Math.min(g, 4));
    out.push(`<span class="ga goals" title="${g} gol${g > 1 ? "uri" : ""} în acest meci">${label}</span>`);
  }
  if (a > 0) {
    const label = am.length ? "👟 " + am.join(", ") : "👟".repeat(Math.min(a, 4));
    out.push(`<span class="ga assists" title="${a} pas${a > 1 ? "e" : "ă"} decisiv${a > 1 ? "e" : "ă"}">${label}</span>`);
  }
  return out.join("");
}

function resultRow(r, myTeam) {
  const links = [];
  if (r.youtube_url)
    links.push(`<button class="icl ytbtn" data-yt="${esc(r.youtube_url)}" title="Vezi rezumatul aici">${YT_ICON}</button>`);
  if (r.flashscore_url)
    links.push(`<a class="icl" href="${esc(r.flashscore_url)}" target="_blank" rel="noopener" title="Deschide pe Flashscore">${FS_ICON}</a>`);
  const flag = r.is_national ? `<span title="Meci la națională">🇷🇴</span> ` : "";
  const fix = `${flag}${teamMark(r.home_team, myTeam)} <span class="sc">${esc(r.score)}</span> ${teamMark(r.away_team, myTeam)}`;
  return `<div class="res${r.is_national ? " nat" : ""}">
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
  const results = resultsFor(p);
  const stats = statsFor(p);
  const rows = results.map(r => resultRow(r, p.team));
  const first = rows.slice(0, 5).join("") ||
    '<div class="res"><span class="muted">Niciun meci în această perioadă</span></div>';
  const expandable = results.length > 5
    ? `<div class="more" hidden>${rows.join("")}</div>
       <button class="showall" data-open="0" data-count="${results.length}">+ toate cele ${results.length} meciuri</button>`
    : "";
  const rating = stats.rating && stats.rating !== "-"
    ? `<span class="rating">★ ${esc(stats.rating)}</span>` : "";
  const bio = [];
  if (p.age) bio.push(`${p.age} ani`);
  if (p.market_value) bio.push(`<b class="mv">${esc(p.market_value)}</b>`);
  const bioLine = bio.length ? `<div class="bio">${bio.join(" · ")}</div>` : "";
  const crest = crestStack(p);
  const nt = p.nt && p.nt.caps
    ? `<div class="nt" title="Statistici la echipa națională a României">
         <span class="nt-flag">🇷🇴</span> Națională
         <b>${p.nt.caps}</b> meciuri · <b>${p.nt.goals}</b> G · <b>${p.nt.assists}</b> A
       </div>` : "";
  return `<div class="card">
    <div class="card-top">
      ${avatar(p, "sm")}
      <div class="who">
        <div class="name">${esc(p.name)}</div>
        <div class="team">${crest}<span class="tn">${esc(p.team || "—")}</span> ${rating}</div>
        ${bioLine}
      </div>
      <span class="pos ${posAbbr(p.position)}">${posAbbr(p.position)}</span>
    </div>
    <div class="stats">${statBlock(stats)}</div>
    ${nt}
    <div class="form">${formDots(results)}</div>
    <div class="results"><div class="res-first">${first}</div>${expandable}</div>
  </div>`;
}

function matchesFilter(p, f) {
  if (STATE.pos && p.position !== STATE.pos) return false;
  if (STATE.league && p.group !== STATE.league) return false;
  if (!f) return true;
  return (p.name + " " + (p.team || "") + " " + (p.group || "")).toLowerCase().includes(f);
}

function anyFilterActive() {
  return !!(STATE.filter.trim() || STATE.pos || STATE.league);
}

function filteredPlayers() {
  const f = STATE.filter.trim().toLowerCase();
  return STATE.players.filter(p => matchesFilter(p, f));
}

const RANGE_LABEL = {
  season: "în acest sezon", ytd: "anul acesta", "1y": "în ultimul an",
  "2y": "în ultimii 2 ani", "3y": "în ultimii 3 ani",
};
function updateSummary() {
  const totalGoals = STATE.players.reduce((s, p) => s + (statsFor(p).goals || 0), 0);
  document.getElementById("summary").textContent =
    `${STATE.players.length} jucători · ${totalGoals} goluri ${RANGE_LABEL[STATE.range] || ""}`;
}

function render() {
  updateSummary();
  if (STATE.view === "arcade") renderArcade();
  else renderClassic();
}

function renderClassic() {
  const app = document.getElementById("app");
  const f = STATE.filter.trim().toLowerCase();
  const groups = {};
  for (const p of filteredPlayers()) (groups[p.group || "Alții"] ??= []).push(p);
  const names = Object.keys(groups).sort((a, b) =>
    groupRank(a) - groupRank(b) || a.localeCompare(b));
  if (!names.length) { app.innerHTML = `<p class="loading">Niciun rezultat.</p>`; return; }

  app.innerHTML = names.map(g => {
    const players = groups[g].sort((a, b) => gaSum(b) - gaSum(a));
    const closed = localStorage.getItem("lg:" + g) === "closed" && !anyFilterActive();
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

function lastName(name) { const t = String(name || "").split(/\s+/); return t[t.length - 1]; }

const SORT_OPTIONS = [
  ["league", "Ligă"], ["goals", "Goluri"], ["assists", "Assist-uri"],
  ["minutes", "Minute jucate"], ["age", "Vârstă"], ["value", "Valoare de piață"],
];
function sortBarHTML() {
  const opts = SORT_OPTIONS.map(([v, l]) =>
    `<option value="${v}" ${STATE.sortBy === v ? "selected" : ""}>${l}</option>`).join("");
  const isLeague = STATE.sortBy === "league";
  const dir = STATE.sortDir === "asc" ? "↑ crescător" : "↓ descrescător";
  return `<div class="mk-sort">
    <span>Sortează:</span>
    <select id="mk-sortby">${opts}</select>
    <button id="mk-sortdir" class="mk-dir" ${isLeague ? "disabled" : ""}>${dir}</button>
  </div>`;
}

function renderArcade() {
  const app = document.getElementById("app");
  const list = filteredPlayers().slice();
  if (STATE.sortBy === "league") {
    list.sort((a, b) => groupRank(a.group || "") - groupRank(b.group || "") ||
      (a.group || "").localeCompare(b.group || "") || gaSum(b) - gaSum(a));
  } else {
    const dir = STATE.sortDir === "asc" ? 1 : -1;
    list.sort((a, b) => (sortKey(a) - sortKey(b)) * dir || a.name.localeCompare(b.name));
  }
  STATE.list = list;
  if (!list.length) { app.innerHTML = `<p class="loading">Niciun rezultat.</p>`; return; }
  if (STATE.sel >= list.length) STATE.sel = 0;

  const showMetric = STATE.sortBy !== "league";
  const tiles = list.map((p, i) => `
    <button class="mk-tile${i === STATE.sel ? " sel" : ""}" data-idx="${i}" title="${esc(p.name)}">
      ${avatar(p, "face")}
      <span class="mk-name">${esc(lastName(p.name))}</span>
      <span class="pos mk-pos ${posAbbr(p.position)}">${posAbbr(p.position)}</span>
      ${showMetric ? `<span class="mk-metric">${esc(sortValueLabel(p))}</span>` : ""}
    </button>`).join("");

  app.innerHTML = `
    <div class="mk-bar">
      <p class="mk-hint">🎮 Săgețile <b>← ↑ ↓ →</b> sau click pentru a alege un jucător.</p>
      ${sortBarHTML()}
    </div>
    <div class="mk">
      <div class="mk-grid" id="mkgrid">${tiles}</div>
      <aside class="mk-panel">
        <div id="mkcard">${card(list[STATE.sel])}</div>
        <div id="mkvideo" class="mk-video"></div>
      </aside>
    </div>`;
  scrollSelIntoView();
}

function scrollSelIntoView() {
  const el = document.querySelector(".mk-tile.sel");
  if (el) el.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function gridCols() {
  const tiles = document.querySelectorAll(".mk-tile");
  if (tiles.length < 2) return 1;
  const top0 = tiles[0].offsetTop;
  let c = 0;
  for (const t of tiles) { if (t.offsetTop === top0) c++; else break; }
  return Math.max(1, c);
}

function updateSel(next) {
  const n = STATE.list.length;
  if (!n) return;
  STATE.sel = Math.max(0, Math.min(n - 1, next));
  document.querySelectorAll(".mk-tile").forEach((el, i) => el.classList.toggle("sel", i === STATE.sel));
  const cardEl = document.getElementById("mkcard");
  if (cardEl) cardEl.innerHTML = card(STATE.list[STATE.sel]);
  clearArcadeVideo();
  scrollSelIntoView();
}

function onKey(e) {
  if (STATE.view !== "arcade") return;
  if (document.activeElement && document.activeElement.id === "filter") return;
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
  e.preventDefault();
  const cols = gridCols();
  const d = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -cols, ArrowDown: cols }[e.key];
  updateSel(STATE.sel + d);
}

function setView(v) {
  STATE.view = v; STATE.sel = 0;
  closeVideoModal();
  document.querySelectorAll(".view-btn").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  try { localStorage.setItem("view", v); } catch {}
  render();
}

function initVideoModal() {
  const dlg = document.getElementById("video-modal");
  dlg.addEventListener("close", () => { document.getElementById("video-slot").innerHTML = ""; });
  dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
}

function initView() {
  let v = "classic";
  try { v = localStorage.getItem("view") || "classic"; } catch {}
  STATE.view = v;
  document.querySelectorAll(".view-btn").forEach(b => b.classList.toggle("active", b.dataset.view === v));
}

function onClick(e) {
  const themeBtn = e.target.closest(".theme-btn");
  if (themeBtn) { applyTheme(themeBtn.dataset.theme); return; }
  const viewBtn = e.target.closest(".view-btn");
  if (viewBtn) { setView(viewBtn.dataset.view); return; }
  if (e.target.closest("#mk-sortdir")) {
    STATE.sortDir = STATE.sortDir === "asc" ? "desc" : "asc"; STATE.sel = 0; render(); return;
  }
  const ytbtn = e.target.closest(".ytbtn");
  if (ytbtn) { playVideo(ytbtn.dataset.yt); return; }
  if (e.target.closest("[data-close-video]")) { clearArcadeVideo(); return; }
  if (e.target.closest("[data-close-modal]")) { closeVideoModal(); return; }
  const tile = e.target.closest(".mk-tile");
  if (tile) { updateSel(+tile.dataset.idx); return; }
  const showall = e.target.closest(".showall");
  if (showall) {
    const container = showall.closest(".results");
    const first = container.querySelector(".res-first");
    const more = container.querySelector(".more");
    const expand = showall.dataset.open !== "1";
    more.hidden = !expand;
    if (first) first.hidden = expand;
    if (expand) more.scrollTop = 0;
    showall.dataset.open = expand ? "1" : "0";
    showall.textContent = expand ? "− mai puține" : `+ toate cele ${showall.dataset.count} meciuri`;
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

function populateLeagues() {
  const leagues = [...new Set(STATE.players.map(p => p.group).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));
  const sel = document.getElementById("filter-league");
  sel.innerHTML = `<option value="">Toate ligile</option>` +
    leagues.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join("");
}

function boot(data) {
  STATE.players = data.players || [];
  populateLeagues();
  if (data.updated_at) {
    document.getElementById("updated").textContent =
      "Actualizat: " + new Date(data.updated_at).toLocaleString("ro-RO",
        { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  render();
}

initTheme();
initIntro();
initView();
initVideoModal();
document.addEventListener("click", onClick);
document.addEventListener("keydown", onKey);
document.getElementById("refresh").addEventListener("click", triggerHighlights);
function onFilterChange() { if (STATE.view === "arcade") STATE.sel = 0; render(); }
document.getElementById("filter").addEventListener("input", e => {
  STATE.filter = e.target.value; onFilterChange();
});
document.getElementById("filter-pos").addEventListener("change", e => {
  STATE.pos = e.target.value; onFilterChange();
});
document.getElementById("filter-league").addEventListener("change", e => {
  STATE.league = e.target.value; onFilterChange();
});
document.getElementById("range").addEventListener("change", e => {
  STATE.range = e.target.value; onFilterChange();
});
document.addEventListener("change", e => {   // arcade sort (dynamic element → delegated)
  if (e.target.id === "mk-sortby") { STATE.sortBy = e.target.value; STATE.sel = 0; render(); }
});

fetch("./data.json")
  .then(r => r.ok ? r.json() : Promise.reject())
  .catch(() => fetch("./data.sample.json").then(r => r.json()))
  .then(boot)
  .catch(() => {
    document.getElementById("app").innerHTML =
      `<p class="loading">Nu s-au putut încărca datele.</p>`;
  });
