"""Render results/demo.json into report/index.html, a one-page summary of the prototype."""

import html
import json
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "results" / "demo.json").read_text())


def n(x, d=0):
    return f"{x:,.{d}f}"


def verdict_chip(pct):
    ok = pct >= 100
    return f'<span class="chip {"ok" if ok else "short"}">{"met" if ok else "short"}</span>'


def compare_row(label, before, after):
    return f"""
    <div class="cmp">
      <div class="cmp-label">{label}</div>
      <div class="cmp-cell"><span class="cmp-k">VillageOS today</span><span class="num">{n(before)}%</span>{verdict_chip(before)}</div>
      <div class="cmp-arrow" aria-hidden="true">→</div>
      <div class="cmp-cell"><span class="cmp-k">With the climate pack</span><span class="num">{n(after)}%</span>{verdict_chip(after)}</div>
    </div>"""


def stack(parts, total, unit):
    segs = "".join(
        f'<div class="seg {cls}" style="width:{max(v / total * 100, 0):.2f}%" title="{html.escape(name)}: {n(v)} {unit}"></div>'
        for name, v, cls in parts if v > 0
    )
    legend = "".join(
        f'<li><span class="sw {cls}"></span>{html.escape(name)} <span class="num">{n(v)}</span> {unit}</li>'
        for name, v, cls in parts if v > 0
    )
    return f'<div class="stack" role="img" aria-label="breakdown">{segs}</div><ul class="legend">{legend}</ul>'


sites_html = []
for r in data:
    today, pack, c = r["villageosToday"], r["climatePack"], r["climate"]
    w, e, s = pack["water"], pack["energy"], pack["water"]["sources"]
    demand = w["domesticDemandM3PerYear"] + w["irrigationDemandM3PerYear"]
    water_parts = [
        ("Rain harvest", s["rain"]["m3PerYear"], "c-rain"),
        ("Groundwater", s["groundwater"]["m3PerYear"], "c-ground"),
        ("Recycled wastewater", s["reuse"]["m3PerYear"], "c-reuse"),
        ("Desalination", s["desalination"]["m3PerYear"], "c-desal"),
        ("Still short", w["shortfallM3PerYear"], "c-gap"),
    ]
    energy_total = max(e["consumptionMwhPerYear"], e["generationMwhPerYear"])
    energy_parts = [
        ("Base use (VillageOS)", e["baseConsumptionMwhPerYear"], "c-base"),
        ("Cooling", e["coolingMwhPerYear"], "c-cool"),
        ("Water supply", e["waterMwhPerYear"], "c-water"),
    ]
    gen_pct = e["generationMwhPerYear"] / energy_total * 100
    coast = "coastal, can desalinate" if c["seawaterAccess"] else "inland, no seawater"
    note = (
        f"Recycled water covers all irrigation, so desalination is only needed for drinking water: a plant of about {n(w['desalinationCapacityM3PerDay'])} m³ a day."
        if c["seawaterAccess"] else
        f"Recycled water lifts coverage, but {n(w['shortfallM3PerYear'])} m³ a year has no source until the site states a sustainable groundwater yield. Groundwater is set to 0 by default."
    )
    sites_html.append(f"""
  <section class="site">
    <header class="site-head">
      <h2>{html.escape(r['site'])}</h2>
      <p class="meta">{coast} · <span class="num">{n(c['rainfallMmPerYear'])}</span> mm rain a year · <span class="num">{n(c['coolingDegreeDays'])}</span> cooling degree days · profile <code>{r['profile']}</code></p>
    </header>
    <div class="cmps">
      {compare_row("Water demand covered", today['water']['percentOfWaterDemand'], w['percentOfWaterDemand'])}
      {compare_row("Energy: generation ÷ consumption", today['energy']['percentOfConsumption'], e['percentOfConsumption'])}
    </div>
    <div class="breakdowns">
      <figure>
        <figcaption>Where the water comes from <span class="unit">m³ a year, demand <span class="num">{n(demand)}</span></span></figcaption>
        {stack(water_parts, demand, "m³")}
        <p class="note">{note}</p>
      </figure>
      <figure>
        <figcaption>What the electricity is for <span class="unit">MWh a year</span></figcaption>
        <div class="gen-wrap">
          {stack(energy_parts, energy_total, "MWh")}
          <div class="gen-line" style="left:{gen_pct:.2f}%"><span>solar <span class="num">{n(e['generationMwhPerYear'])}</span></span></div>
        </div>
        <p class="note">To be net positive the site needs about <span class="num">{n(e['arrayAreaForNetPositiveM2'])}</span> m² of panels; VillageOS's estimate places <span class="num">{n(today['energy']['solarPvAreaM2'])}</span> m².</p>
      </figure>
    </div>
  </section>""")

assumptions = data[0]["climatePack"]["assumptions"]
india = data[1]["climatePack"]["assumptions"]
rows = []
for name, a in assumptions.items():
    value = f"{a['value']:g} {html.escape(a['unit'])}"
    if india[name]["value"] != a["value"]:
        value = f"UAE {a['value']:g} · India {india[name]['value']:g} {html.escape(a['unit'])}"
        src = f"UAE: {html.escape(a['source'])}<br>India: {html.escape(india[name]['source'])}"
    else:
        src = html.escape(a["source"])
    sourced = a["sourced"] and "no source recorded" not in a["source"].lower()
    chip = '<span class="chip ok">sourced</span>' if sourced else '<span class="chip open">open question</span>'
    rows.append(f"<tr><td><code>{name}</code></td><td class='num'>{value}</td><td>{chip}</td><td class='src'>{src}</td></tr>")

page = f"""<title>VillageOS ClimatePack</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a single research brief, one measured column; each site is a band with a before/after row and two breakdown bars. */
:root {{
  --bg: #f6f8f9; --surface: #ffffff; --fg: #15212a; --muted: #586874; --line: #dbe3e8;
  --water: #1f7a8c; --reuse: #4fa3a5; --rain: #8fc6d4; --ground: #6b8e9e; --desal: #134e5e;
  --heat: #c56a1b; --cool: #e0a45a; --base: #9aa8b2; --gap: #c8453c;
  --ok: #1f7a4f; --ok-bg: #e3f2ea; --short: #a33a32; --short-bg: #f8e4e2; --open: #7a5a12; --open-bg: #f5ecd6;
  --display: "Space Grotesk", "Segoe UI", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0f171c; --surface: #16222a; --fg: #e3ebef; --muted: #9aabb5; --line: #2a3a44;
  --water: #4fb3c6; --reuse: #6cc2c2; --rain: #9fd3e0; --ground: #86a9b8; --desal: #2f8aa0;
  --heat: #e08a3c; --cool: #e8b36c; --base: #6f7f8a; --gap: #e06a60;
  --ok: #6fcf9b; --ok-bg: #173327; --short: #f0948b; --short-bg: #3a1e1b; --open: #e6c46f; --open-bg: #33290f;
  color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0f171c; --surface: #16222a; --fg: #e3ebef; --muted: #9aabb5; --line: #2a3a44;
  --water: #4fb3c6; --reuse: #6cc2c2; --rain: #9fd3e0; --ground: #86a9b8; --desal: #2f8aa0;
  --heat: #e08a3c; --cool: #e8b36c; --base: #6f7f8a; --gap: #e06a60;
  --ok: #6fcf9b; --ok-bg: #173327; --short: #f0948b; --short-bg: #3a1e1b; --open: #e6c46f; --open-bg: #33290f;
  color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.6 var(--body); }}
.wrap {{ max-width: 920px; margin: 0 auto; padding-block: 48px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 40px; }}
h1, h2, h3 {{ font-family: var(--display); font-weight: 600; text-wrap: balance; margin: 0; letter-spacing: -0.01em; }}
h1 {{ font-size: clamp(30px, 5vw, 44px); line-height: 1.1; }}
h2 {{ font-size: 24px; }}
h3 {{ font-size: 18px; }}
p {{ margin: 0; max-width: 66ch; }}
code {{ font-family: var(--mono); font-size: 0.88em; }}
.num {{ font-family: var(--mono); font-variant-numeric: tabular-nums; }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: 0.08em; text-transform: uppercase; color: var(--water); }}
.intro {{ display: grid; gap: 16px; }}
.lede {{ font-size: 18px; color: var(--fg); }}
.muted {{ color: var(--muted); }}
.gap-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
.gap-item {{ border-top: 3px solid var(--water); padding-top: 12px; display: grid; gap: 6px; }}
.gap-item.heat {{ border-color: var(--heat); }}
.site {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 24px; display: grid; gap: 24px; min-width: 0; }}
.site-head {{ display: grid; gap: 4px; }}
.meta {{ color: var(--muted); font-size: 13px; }}
.cmps {{ display: grid; gap: 10px; }}
.cmp {{ display: grid; grid-template-columns: minmax(150px, 1.2fr) 1fr auto 1fr; gap: 12px; align-items: center; padding: 12px 0; border-top: 1px solid var(--line); }}
.cmp-label {{ font-weight: 600; }}
.cmp-cell {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }}
.cmp-k {{ width: 100%; font-size: 12px; color: var(--muted); }}
.cmp-cell .num {{ font-size: 22px; font-weight: 500; }}
.cmp-arrow {{ color: var(--muted); font-size: 18px; }}
.chip {{ font: 500 11px/1 var(--mono); letter-spacing: 0.04em; text-transform: uppercase; padding: 4px 7px; border-radius: 4px; white-space: nowrap; }}
.chip.ok {{ background: var(--ok-bg); color: var(--ok); }}
.chip.short {{ background: var(--short-bg); color: var(--short); }}
.chip.open {{ background: var(--open-bg); color: var(--open); }}
.breakdowns {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }}
figure {{ margin: 0; display: grid; gap: 10px; min-width: 0; }}
figcaption {{ font-weight: 600; display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }}
.unit {{ font-weight: 400; font-size: 12px; color: var(--muted); }}
.stack {{ display: flex; height: 22px; border-radius: 4px; overflow: hidden; background: var(--line); }}
.seg {{ height: 100%; }}
.seg + .seg {{ box-shadow: inset 2px 0 0 var(--surface); }}
.legend {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: 13px; }}
.legend li {{ display: flex; align-items: center; gap: 8px; }}
.sw {{ width: 10px; height: 10px; border-radius: 2px; flex: none; }}
.c-rain {{ background: var(--rain); }} .c-ground {{ background: var(--ground); }} .c-reuse {{ background: var(--reuse); }}
.c-desal {{ background: var(--desal); }} .c-gap {{ background: var(--gap); }}
.c-base {{ background: var(--base); }} .c-cool {{ background: var(--cool); }} .c-water {{ background: var(--water); }}
.gen-wrap {{ position: relative; display: grid; gap: 10px; padding-top: 22px; }}
.gen-line {{ position: absolute; top: 0; height: 44px; border-left: 2px dashed var(--fg); }}
.gen-line span {{ position: absolute; top: 0; left: 6px; font-size: 12px; white-space: nowrap; color: var(--fg); }}
.note {{ font-size: 13px; color: var(--muted); }}
.panel {{ display: grid; gap: 14px; }}
.checks {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
.check {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--surface); display: grid; gap: 6px; }}
.check .big {{ font: 500 22px/1.2 var(--mono); color: var(--water); }}
.table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; min-width: 720px; font-size: 13px; }}
th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font: 500 11px/1.2 var(--mono); text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
td.src {{ color: var(--muted); max-width: 360px; }}
ol.limits {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; max-width: 70ch; }}
footer {{ font-size: 12px; color: var(--muted); display: grid; gap: 6px; border-top: 1px solid var(--line); padding-top: 16px; }}
a {{ color: var(--water); }}
a:focus-visible {{ outline: 2px solid var(--water); outline-offset: 2px; }}
@media (max-width: 560px) {{
  .cmp {{ grid-template-columns: 1fr 1fr; }}
  .cmp-label {{ grid-column: 1 / -1; }}
  .cmp-arrow {{ display: none; }}
  .site {{ padding: 18px; }}
}}
</style>

<div class="wrap">
  <header class="intro">
    <span class="eyebrow">Prototype · VillageOS pipeline node · Khokon Barua · November 2026</span>
    <h1>VillageOS ClimatePack</h1>
    <p class="lede">VillageOS judges a site's water by the rain it can catch and its energy by a flat 2,500 kWh per resident. For the hot, dry sites in the India and UAE pilots, both verdicts come out wrong. This prototype adds the water those places actually use and the electricity they actually need, and reruns VillageOS's own worked example in Dubai and Jaipur.</p>
    <div class="gap-list">
      <div class="gap-item"><h3>Water beyond rain</h3><p class="muted">Recycled wastewater for irrigation, groundwater up to a sustainable yield, and desalination where a site reaches the sea, with the energy each one takes.</p></div>
      <div class="gap-item heat"><h3>Energy for heat</h3><p class="muted">Cooling electricity from the site's cooling degree days, fetched from NASA POWER, the same provider VillageOS's climate registration calls.</p></div>
    </div>
  </header>

  <p class="muted">Both sites use the Willow Bend programme from VillageOS's LAND_INTAKE guide: 24 hectares, 320 residents, the same six programme shares. Only the climate changes.</p>

  {''.join(sites_html)}

  <section class="panel">
    <h2>How it fits VillageOS</h2>
    <div class="checks">
      <div class="check"><span class="big">exact</span><p class="muted">Reproduces the Willow Bend worked example before changing anything: 49,728 m³ harvest, 8,672 m³ irrigation shortfall, 91% of consumption.</p></div>
      <div class="check"><span class="big">20 tests</span><p class="muted">Pass, including the pipeline envelope, the manifest, and failing by port name on a missing or withheld input.</p></div>
      <div class="check"><span class="big">drop-in</span><p class="muted">A Python node on <code>vos.Service.Python.Shared</code>, the same contract as the Echo template, beside EnergyBalance and WaterReserve.</p></div>
    </div>
    <p class="muted">It also includes a draft Tributary registration that fetches cooling degree days onto a Site, written in the shape of <code>climate-averages</code>. It has not yet been run through the seed validator.</p>
  </section>

  <section class="panel">
    <h2>Every assumption, and where it came from</h2>
    <p class="muted">Following VillageOS's own rule that a figure says where it came from. The open questions are the research a summer would settle.</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Assumption</th><th>Value</th><th>Status</th><th>Source</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>Limits, and what a summer would settle</h2>
    <ol class="limits">
      <li>Annual totals hide the seasons. Jaipur's rain falls in a few monsoon months, so storage needs the daily rain VillageOS already fetches.</li>
      <li>Cooling uses a simple degree-day model. Humidity, building type and the study's wet-bulb figures should refine it.</li>
      <li>Air-conditioner efficiency, floor area per person, wastewater return and pump lift have no regional source yet. Pinning them for India and the UAE, with citations, is the core research.</li>
      <li>Today it is a pipeline node. Folded into the platform, its formulas would become derived properties on the shared study, judged by ranges like every other balance.</li>
    </ol>
  </section>

  <footer>
    <p>Climate: NASA POWER climatology, 2001–2025 (PRECTOTCORR, ALLSKY_SFC_SW_DWN, CDD18_3) at Dubai 25.20°N 55.27°E and Jaipur 26.91°N 75.79°E.</p>
    <p>Formulas: VillageOS Field Guide, Appendix D, and LAND_INTAKE.md §8 (ReGen-Villages/VillageOS-API). Code: AGPL-3.0, matching VillageOS-API.</p>
  </footer>
</div>
"""
out = HERE / "report"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page)
print("wrote", out / "index.html", len(page), "bytes")
