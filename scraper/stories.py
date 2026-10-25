"""Instagram story + feed post PNGs per weekend day with Romanians who scored/assisted.

Reads site/data.json, renders a 1080x1920 HTML card per day with headless
Chromium (Playwright) and writes site/stories/YYYY-MM-DD.png plus a
1080x1350 feed post YYYY-MM-DD-post.png, and an
index.json the site uses to list them. Days with no goals/assists get no
story (and a stale PNG for that day is removed).

Usage:
    python stories.py                         # Fri–Sun of the current weekend
    python stories.py --dates 2026-10-23 2026-10-24
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "site" / "data.json"
OUT_DIR = ROOT / "site" / "stories"
HANDLE = "@renasterea.nationalei"
KEEP_DAYS = 70          # prune story PNGs older than this

DAYS = ["LUNI", "MARȚI", "MIERCURI", "JOI", "VINERI", "SÂMBĂTĂ", "DUMINICĂ"]
# Instagram formats: story 9:16, feed post 4:5 (largest portrait the feed shows)
FORMATS = {"story": {"height": 1920, "suffix": ""},
           "post": {"height": 1350, "suffix": "-post"}}
RESULT_LABEL = {"W": "VICTORIE", "D": "EGAL", "L": "ÎNFRÂNGERE"}
MONTHS = ["IANUARIE", "FEBRUARIE", "MARTIE", "APRILIE", "MAI", "IUNIE", "IULIE",
          "AUGUST", "SEPTEMBRIE", "OCTOMBRIE", "NOIEMBRIE", "DECEMBRIE"]


def collect(data: dict, day: str) -> list[dict]:
    """Club matches on `day` where a tracked player scored or assisted,
    biggest contribution first."""
    out = []
    for p in data.get("players", []):
        for r in p.get("results", []):
            if r["date"] != day or r.get("is_national"):
                continue
            g, a = r.get("player_goals") or 0, r.get("player_assists") or 0
            if not (g or a):
                continue
            out.append({
                "name": p["name"], "team": p.get("team"), "team_logo": p.get("team_logo"),
                "goals": g, "assists": a,
                "home": r["home_team"], "away": r["away_team"], "score": r["score"],
                "home_logo": r.get("home_logo"), "away_logo": r.get("away_logo"),
                "competition": r.get("competition", ""), "rating": r.get("rating"),
                "result": r.get("result") if r.get("result") in RESULT_LABEL else None,
            })
    out.sort(key=lambda e: (-(e["goals"] + e["assists"]), -e["goals"], e["name"]))
    return out


def weekend_dates(today: date) -> list[str]:
    """Fri–Sun of the most recent weekend, not past today (Mon–Thu -> last weekend)."""
    fri = today - timedelta(days=(today.weekday() - 4) % 7)
    return [str(fri + timedelta(days=i)) for i in range(3) if fri + timedelta(days=i) <= today]


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _crest(url: str | None, label: str, cls: str) -> str:
    if url:
        return f'<img class="{cls}" src="{escape(url)}" alt="">'
    initials = "".join(w[0] for w in label.split()[:2]).upper()
    return f'<span class="{cls} crest-fallback">{escape(initials)}</span>'


def _card(e: dict) -> str:
    pills = []
    if e["goals"]:
        pills.append(f'<span class="pill goal">{plural(e["goals"], "GOL", "GOLURI")}</span>')
    if e["assists"]:
        pills.append(f'<span class="pill assist">'
                     f'{plural(e["assists"], "PASĂ DE GOL", "PASE DE GOL")}</span>')
    rating = f'<span class="rating">{escape(e["rating"])}</span>' if e["rating"] else ""
    result_tag = (f'<span class="result">{RESULT_LABEL[e["result"]]}</span>'
                  if e["result"] else "")
    own = e["team_logo"] or (e["home_logo"] if e["home"] == e["team"] else e["away_logo"])
    return f"""
    <div class="card res-{e["result"] or "N"}">
      {result_tag}
      {_crest(own, e["team"] or e["name"], "club")}
      <div class="body">
        <div class="name">{escape(e["name"])}</div>
        <div class="pills">{"".join(pills)}{rating}</div>
        <div class="match">
          {_crest(e["home_logo"], e["home"], "mini")}
          <span class="team">{escape(e["home"])}</span>
          <span class="score">{escape(e["score"])}</span>
          <span class="team">{escape(e["away"])}</span>
          {_crest(e["away_logo"], e["away"], "mini")}
        </div>
        <div class="comp">{escape(e["competition"])}</div>
      </div>
    </div>"""


def render_html(day: str, entries: list[dict], fmt: str = "story") -> str:
    d = date.fromisoformat(day)
    cards = "".join(_card(e) for e in entries)
    compact = "compact" if len(entries) >= 6 else ""   # smaller header, more card room
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: 1080px; height: {FORMATS[fmt]["height"]}px; }}
  body {{
    --s: 1;   /* shrunk in render_png until the cards fit */
    font-family: Inter, sans-serif; color: #fff; overflow: hidden; position: relative;
    background: radial-gradient(120% 70% at 85% 0%, #1c3d7a 0%, #0b1d3a 45%, #060f22 100%);
  }}
  .flag {{ position: absolute; top: 0; left: 0; right: 0; height: 18px; display: flex; }}
  .flag i {{ flex: 1; }}
  .flag i:nth-child(1) {{ background: #002B7F; }}
  .flag i:nth-child(2) {{ background: #FCD116; }}
  .flag i:nth-child(3) {{ background: #CE1126; }}
  .wrap {{ position: absolute; top: 230px; bottom: 250px; left: 72px; right: 72px;
           display: flex; flex-direction: column; }}
  .kicker {{ font-weight: 800; letter-spacing: .32em; font-size: 26px; color: #FCD116; }}
  .day {{ font-family: 'Bebas Neue', sans-serif; font-size: 190px; line-height: .9;
          margin-top: 34px; }}
  .date {{ font-family: 'Bebas Neue', sans-serif; font-size: 58px; letter-spacing: .06em;
           color: rgba(255,255,255,.7); }}
  .sub {{ font-size: 28px; color: rgba(255,255,255,.75); margin-top: 14px; }}
  .cards {{ flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; justify-content: center;
            gap: calc(26px * var(--s)); margin-top: 36px; }}
  .card {{ position: relative; display: flex; align-items: center; gap: calc(34px * var(--s));
           background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12);
           border-left: 8px solid #FCD116; border-radius: 28px;
           padding: calc(28px * var(--s)) calc(34px * var(--s)); }}
  .res-W {{ --res: #2ecc71; }}  .res-D {{ --res: #8a93a6; }}
  .res-L {{ --res: #ef4a5a; }}  .res-N {{ --res: #FCD116; }}
  .card {{ border-left-color: var(--res); }}
  .result {{ position: absolute; top: calc(22px * var(--s)); right: calc(26px * var(--s));
             font-weight: 800; font-size: calc(20px * var(--s)); letter-spacing: .12em;
             color: var(--res); border: 2px solid var(--res); border-radius: 8px;
             padding: calc(4px * var(--s)) calc(10px * var(--s)); }}
  .club {{ width: calc(132px * var(--s)); height: calc(132px * var(--s)); flex: none;
           object-fit: contain; background: #fff; border-radius: 50%;
           padding: calc(16px * var(--s)); }}
  .body {{ min-width: 0; flex: 1; }}
  .name {{ font-family: 'Bebas Neue', sans-serif; font-size: calc(70px * var(--s));
           line-height: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .pills {{ display: flex; gap: 12px; margin-top: calc(12px * var(--s)); align-items: center; }}
  .pill {{ font-weight: 800; font-size: calc(26px * var(--s)); letter-spacing: .04em;
           padding: calc(7px * var(--s)) calc(18px * var(--s)); border-radius: 999px; }}
  .goal {{ background: #FCD116; color: #1a1300; }}
  .assist {{ background: #4f8cff; color: #fff; }}
  .rating {{ font-weight: 800; font-size: calc(24px * var(--s)); color: rgba(255,255,255,.85);
             border: 2px solid rgba(255,255,255,.45); border-radius: 10px;
             padding: calc(3px * var(--s)) calc(10px * var(--s)); }}
  .match {{ display: flex; align-items: center; gap: 12px; margin-top: calc(16px * var(--s));
            font-size: calc(30px * var(--s)); font-weight: 700; }}
  .match .team {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                  max-width: 290px; }}
  .match .score {{ background: var(--res); color: #06101f; border-radius: 10px; padding: 2px 14px; }}
  .mini {{ width: calc(44px * var(--s)); height: calc(44px * var(--s)); flex: none;
           object-fit: contain; background: #fff; border-radius: 50%; padding: 4px; }}
  .crest-fallback {{ display: inline-flex; align-items: center; justify-content: center;
                     color: #0b1d3a; font-weight: 800; font-size: 60%; }}
  .comp {{ font-size: calc(22px * var(--s)); color: rgba(255,255,255,.55);
           margin-top: calc(8px * var(--s)); }}
  .compact .wrap {{ top: 200px; }}
  .compact .day {{ font-size: 120px; margin-top: 24px; }}
  .compact .date {{ font-size: 44px; }}
  .compact .sub {{ display: none; }}
  .compact .cards {{ margin-top: 24px; }}
  /* feed post: nothing overlays it, so no safe zones; always compact header */
  .post .wrap {{ top: 64px; bottom: 56px; }}
  .post .day {{ font-size: 120px; margin-top: 22px; }}
  .post .date {{ font-size: 44px; }}
  .post .sub {{ display: none; }}
  .post .cards {{ margin-top: 24px; }}
  .post .handle {{ margin-top: 22px; font-size: 30px; }}
  .handle {{ text-align: center; font-weight: 800; font-size: 34px; letter-spacing: .04em;
             margin-top: 30px; }}
  .handle b {{ color: #FCD116; }}
</style></head><body class="{fmt} {compact}">
  <div class="flag"><i></i><i></i><i></i></div>
  <div class="wrap">
    <div class="kicker">ROMÂNII DIN STRĂINĂTATE</div>
    <div class="day">{DAYS[d.weekday()]}</div>
    <div class="date">{d.day} {MONTHS[d.month - 1]} {d.year}</div>
    <div class="sub">Goluri și pase de gol în campionatele străine</div>
    <div class="cards">{cards}</div>
    <div class="handle"><b>{HANDLE.split('.')[0]}</b>.{HANDLE.split('.', 1)[1]}</div>
  </div>
</body></html>"""


# Shrink the card scale until the card stack fits its box (any player count).
FIT_JS = """() => {
  const box = document.querySelector('.cards');
  let s = 1;
  while (box.scrollHeight > box.clientHeight + 1 && s > 0.4) {
    s -= 0.02;
    document.body.style.setProperty('--s', s.toFixed(2));
  }
}"""


def render_png(html: str, out: Path, height: int = 1920) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": height})
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.evaluate(FIT_JS)
        page.screenshot(path=str(out), full_page=False)
        browser.close()


def _write_index(data: dict, today: date) -> None:
    cutoff = str(today - timedelta(days=KEEP_DAYS))
    items = []
    for png in OUT_DIR.glob("????-??-??*.png"):
        if png.name[:10] < cutoff:
            png.unlink()
    for png in sorted(OUT_DIR.glob("????-??-??.png"), reverse=True):
        post = OUT_DIR / f"{png.stem}{FORMATS['post']['suffix']}.png"
        items.append({"date": png.stem, "file": f"stories/{png.name}",
                      "post": f"stories/{post.name}" if post.exists() else None,
                      "players": len(collect(data, png.stem))})
    (OUT_DIR / "index.json").write_text(json.dumps(items, indent=1), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="*", help="YYYY-MM-DD days (default: current weekend)")
    ap.add_argument("--html", action="store_true", help="also write the .html next to each PNG")
    args = ap.parse_args(argv)

    today = date.today()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for day in args.dates or weekend_dates(today):
        entries = collect(data, day)
        for fmt, spec in FORMATS.items():
            out = OUT_DIR / f"{day}{spec['suffix']}.png"
            if not entries:
                out.unlink(missing_ok=True)
                continue
            html = render_html(day, entries, fmt)
            if args.html:
                out.with_suffix(".html").write_text(html, encoding="utf-8")
            render_png(html, out, spec["height"])
            print(f"  {day}: {len(entries)} players -> {out.relative_to(ROOT)}")
        if not entries:
            print(f"  {day}: no goals/assists — no story")
    _write_index(data, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
