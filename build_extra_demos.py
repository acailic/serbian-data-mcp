"""Build demo pages for population pyramid and electricity consumption."""

import asyncio
import httpx
import zipfile
import io
import json
import os
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUT = Path("exports/demo")


async def fetch_json(url: str, timeout: int = 120) -> list[dict]:
    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.get(url)
        ct = resp.headers.get("content-type", "")
        if "zip" in ct:
            z = zipfile.ZipFile(io.BytesIO(resp.content))
            fname = z.namelist()[0]
            return json.loads(z.read(fname))
        content = resp.content.decode("utf-8-sig")
        return json.loads(content)


# Shared theme
THEME = {
    "paper_bgcolor": "#0a0a1a",
    "plot_bgcolor": "#0f0f28",
    "font": {"family": "Inter, sans-serif", "color": "#e8e8f0"},
    "colorway": ["#ffab00", "#42a5f5", "#66bb6a", "#ef5350", "#ab47bc", "#26c6da"],
}

AXIS = {
    "gridcolor": "rgba(255,255,255,0.06)",
    "zerolinecolor": "rgba(255,255,255,0.12)",
    "tickfont": {"size": 11, "color": "#9898b8"},
}


def wrap_html(fig_list: list[go.Figure], title: str, subtitle: str, meta: str = "") -> str:
    """Wrap multiple Plotly figures into a dark-themed HTML page."""
    figs_html = "\n".join(f.to_html(full_html=False, include_plotlyjs=False) for f in fig_list)
    return f"""<!DOCTYPE html>
<html lang="sr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{meta}">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root {{ --bg: #0a0a1a; --card: #111128; --border: rgba(255,255,255,0.06); --accent: #ffab00;
         --text: #e8e8f0; --muted: #6868a0; --red: #ef5350; --green: #66bb6a; --blue: #42a5f5; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
header {{ padding: 80px 24px 40px; max-width: 1100px; margin: 0 auto; text-align: center; }}
header h1 {{ font-size: 2.4rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px; }}
header h1 span {{ color: var(--accent); }}
header p {{ color: var(--muted); font-size: 1.05rem; max-width: 600px; margin: 0 auto; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;
           max-width: 900px; margin: 24px auto 0; }}
.stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; text-align: center; }}
.stat .num {{ font-size: 1.6rem; font-weight: 800; }}
.stat .num.gold {{ color: var(--accent); }}
.stat .num.red {{ color: var(--red); }}
.stat .num.green {{ color: var(--green); }}
.stat .num.blue {{ color: var(--blue); }}
.stat .lbl {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }}
.charts {{ max-width: 1100px; margin: 0 auto; padding: 20px 24px 60px; }}
.charts > div {{ margin-bottom: 32px; }}
.charts h2 {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 12px; color: var(--text); }}
nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(10,10,26,0.85);
      backdrop-filter: blur(16px); border-bottom: 1px solid var(--border); padding: 0 24px; height: 56px;
      display: flex; align-items: center; justify-content: space-between; }}
nav .brand {{ font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 8px; }}
nav .brand span {{ font-size: 1.1rem; }}
nav a {{ color: #9898b8; font-size: 0.85rem; font-weight: 500; text-decoration: none; margin-left: 20px; }}
nav a:hover {{ color: var(--accent); }}
footer {{ max-width: 1100px; margin: 0 auto; padding: 20px 24px 40px; border-top: 1px solid var(--border);
          font-size: 0.78rem; color: var(--muted); text-align: center; }}
</style>
</head>
<body>
<nav>
  <div class="brand">🇷🇸 <span>Serbian Data MCP</span></div>
  <div>
    <a href="index.html">All Demos</a>
  </div>
</nav>
<header>
  <h1>{title}</h1>
  <p>{subtitle}</p>
</header>
<div class="charts">
{figs_html}
</div>
<footer>
  Podaci: Републички завод за статистику (РЗС) · data.gov.rs · Serbian Data MCP
</footer>
</body>
</html>"""


async def build_population_pyramid() -> str:
    print("  Loading Census 2022 age/sex data...")
    url = "https://opendata.stat.gov.rs/data/WcfJsonRestService.Service1.svc/dataset/3104020201IND01/1/json"
    data = await fetch_json(url)

    # Filter: Serbia total, by sex, all settlement types
    rs_rows = [r for r in data if r.get("IDTer") == "RS" and r.get("IDPol", 0) != 0 and r.get("IDTipNaselja") == "0"]

    # Build pyramid dict
    pyramid = {}
    for r in rs_rows:
        age = r["nStarGrupa"]
        if age in ("Укупно", "Пунолетни (18+)"):
            continue
        sex = r["nPol"]
        pyramid.setdefault(age, {})[sex] = int(r["vrednost"])

    # Sort age groups numerically
    def age_sort_key(age: str) -> tuple[int, int]:
        if "–" in age:
            parts = age.replace(" и више година", "").split("–")
            return (0, int(parts[0]))
        return (99, 0)

    ages = sorted(pyramid.keys(), key=age_sort_key)

    males = [-pyramid[a]["Мушко"] for a in ages]  # negative for left side
    females = [pyramid[a]["Женско"] for a in ages]
    labels = [a.replace(" и више година", "85+") for a in ages]

    # 1. Population Pyramid
    fig1 = go.Figure()
    fig1.add_trace(
        go.Bar(
            y=labels,
            x=males,
            orientation="h",
            name="Мушкарци",
            marker_color="#42a5f5",
            hovertemplate="<b>%{y}</b><br>Мушки: %{x:,} општина<br>",
        )
    )
    fig1.add_trace(
        go.Bar(
            y=labels,
            x=females,
            orientation="h",
            name="Женско",
            marker_color="#ef5350",
            hovertemplate="<b>%{y}</b><br>Женско: %{x:,}<br>",
        )
    )
    fig1.update_layout(
        **THEME,
        barmode="overlay",
        title={"text": "Пирамида становништва Србије — Попис 2022", "font": {"size": 16}},
        xaxis_title="Становништво",
        xaxis=dict(
            **AXIS,
            tickformat=",",
            ticksuffix=" ",
            range=[-300000, 300000],
        ),
        yaxis=dict(**AXIS, dtick=1),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        margin={"l": 100, "r": 40, "t": 60, "b": 40},
        height=700,
        hoverlabel={"bgcolor": "#1a1a3e", "font_size": 13},
    )

    # 2. Age Distribution Bar (stacked)
    fig2 = go.Figure()
    m_vals = [-pyramid[a]["Мушко"] for a in ages]
    f_vals = [pyramid[a]["Женско"] for a in ages]
    [abs(m) + abs(f) for m, f in zip(m_vals, f_vals, strict=False)]

    fig2.add_trace(
        go.Bar(
            x=labels,
            y=[pyramid[a]["Мушко"] for a in ages],
            name="Мушки",
            marker_color="#42a5f5",
            hovertemplate="%{x}<br>Мушки: %{y:,}",
        )
    )
    fig2.add_trace(
        go.Bar(
            x=labels,
            y=[pyramid[a]["Женско"] for a in ages],
            name="Женско",
            marker_color="#ef5350",
            hovertemplate="%{x}<br>Женско: %{y:,}",
        )
    )
    # Ratio line
    ratios = [pyramid[a]["Женско"] / max(pyramid[a]["Мушко"], 1) for a in ages]
    fig2.add_trace(
        go.Scatter(
            x=labels,
            y=ratios,
            name="Однос Ж/М",
            mode="lines+markers",
            line={"color": "#ffab00", "width": 2},
            yaxis="y2",
            hovertemplate="%{x}<br>Ж/М: %{y:.2f}",
        )
    )

    fig2.update_layout(
        **THEME,
        barmode="stack",
        title={"text": "Старосна структура — Опажање по групама", "font": {"size": 14}},
        yaxis=dict(**AXIS, title="Број становника", side="left", tickformat=","),
        yaxis2=dict(
            **AXIS,
            title="Однос Ж/М",
            side="right",
            overlaying="y",
            range=[0.5, 2.5],
        ),
        xaxis=dict(**AXIS, tickangle=45, title="Старосна група"),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        margin={"l": 80, "r": 80, "t": 60, "b": 80},
        height=550,
    )

    # 3. Broad category comparison
    categories = [
        ("0–19 (Омладина)", "0–4", "5–9", "10–14", "15–19"),
        ("20–39 (Млади одрасли)", "20–24", "25–29", "30–34", "35–39"),
        ("40–64 (Средовечни)", "40–44", "45–49", "50–54", "55–59", "60–64"),
        ("65+ (Стари)", "65–69", "70–74", "75–79", "80–84", "85 и више година"),
    ]
    cat_names, cat_vals = [], []
    for name, *age_list in categories:
        total = sum(pyramid[a]["Мушко"] + pyramid[a]["Женско"] for a in age_list)
        cat_names.append(name)
        cat_vals.append(total)

    total_all = sum(cat_vals)
    pct_vals = [v / total_all * 100 for v in cat_vals]

    colors = ["#66bb6a", "#42a5f5", "#ffab00", "#ef5350"]
    fig3 = go.Figure(
        go.Pie(
            labels=[f"{n}<br>{v:,} ({p:.1f}%)" for n, v, p in zip(cat_names, cat_vals, pct_vals, strict=False)],
            values=pct_vals,
            marker_colors=colors,
            textinfo="label",
            textfont={"size": 12, "color": "#e8e8f0"},
            hole=0.4,
            hovertemplate="<b>%{label}</b><extra></extra>",
        )
    )
    fig3.update_layout(
        **THEME,
        title={"text": "Старосне категорије Србије — Попис 2022", "font": {"size": 14}},
        legend={"font": {"size": 11}},
        margin={"t": 50},
        height=500,
        showlegend=False,
    )

    # Stats
    total_m = sum(pyramid[a]["Мушко"] for a in ages)
    total_f = sum(pyramid[a]["Женско"] for a in ages)
    total = total_m + total_f
    youth = sum(pyramid[a]["Мушко"] + pyramid[a]["Женско"] for a in ages if a in ("0–4", "5–9", "10–14", "15–19"))
    working = sum(
        pyramid[a]["Мушко"] + pyramid[a]["Женско"]
        for a in ages
        if any(x in a for x in ["20–24", "25–29", "30–34", "35–39", "40–44", "45–49", "50–54", "55–59", "60–64"])
    )
    elderly = total - youth - working
    dep_ratio = (youth + elderly) / working * 100

    stats_html = f"""
<div class="stats">
  <div class="stat"><div class="num gold">{total:,}</div><div class="lbl">Укупно становника</div></div>
  <div class="stat"><div class="num blue">{total_m:,}</div><div class="lbl">Мушкарци ({total_m / total * 100:.1f}%)</div></div>
  <div class="stat"><div class="num red">{total_f:,}</div><div class="lbl">Женско ({total_f / total * 100:.1f}%)</div></div>
  <div class="stat"><div class="num green">{youth / total * 100:.1f}%</div><div class="lbl">Омладина (0–19)</div></div>
  <div class="stat"><div class="num">{dep_ratio:.1f}</div><div class="lbl">Однос зависности</div></div>
  <div class="stat"><div class="num red">{elderly / total * 100:.1f}%</div><div class="lbl">Стари (65+)</div></div>
</div>"""

    html = wrap_html(
        [fig1, fig2, fig3],
        title="Пирамида <span>становништва</span> Србије",
        subtitle="Попис 2022 — Становништво према старости и полу · 6,65 miliona stanovnika · 202 opština",
        meta="Population pyramid of Serbia Census 2022 — age and sex distribution with demographic analysis",
    )

    # Insert stats after header
    html = html.replace("</header>", f"</header>{stats_html}")

    path = OUT / "07_population_pyramid.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✅ {path}")
    return str(path)


async def build_electricity() -> str:
    print("  Loading electricity balance data...")
    url = "https://opendata.stat.gov.rs/data/WcfJsonRestService.Service1.svc/dataset/040201IND06/1/json"
    data = await fetch_json(url)

    target = "Електрична енергија (укупно), ТЈ"
    elec = [r for r in data if r.get("nEnergenti") == target and r.get("vrednost") is not None]

    # Consumption sectors
    sectors = [
        "Финална потрошња - Домаћинства",
        "Финална потрошња - Индустрија",
        "Финална потрошња - Саобраћај",
        "Финална потрошња - Пољопривреда",
        "Финална потрошња - Грађевинарство",
        "Финална потрошња - Остали потрошачи",
    ]
    sector_labels = ["Domaćinstva", "Industrija", "Saobraćaj", "Poljoprivreda", "Građevinarstvo", "Ostalo"]
    sector_colors = ["#ffab00", "#42a5f5", "#26c6da", "#66bb6a", "#ab47bc", "#78909c"]

    # Production sources
    prod_sources = [
        "Производња енергије трансформацијом - Термоелектране",
        "Производња енергије трансформацијом - Хидроелектране",
        "Производња енергије трансформацијом - Термоелектране-топлане (ТЕ-ТО)",
        "Производња енергије трансформацијом - Ветроелектране",
        "Производња енергије трансформацијом - Соларне електране",
    ]
    prod_labels = ["Termoelektrane", "Hidroelektrane", "TE-TO", "Vetar", "Solarne"]
    prod_colors = ["#ef5350", "#42a5f5", "#ffab00", "#26c6da", "#66bb6a"]

    pop_approx = {
        str(y): p
        for y, p in [
            (2010, 7186862),
            (2011, 7120066),
            (2012, 7100000),
            (2013, 7160000),
            (2014, 7130000),
            (2015, 7090000),
            (2016, 7050000),
            (2017, 7020000),
            (2018, 6980000),
            (2019, 6940000),
            (2020, 6900000),
            (2021, 6870000),
            (2022, 6830000),
            (2023, 6760000),
            (2024, 6710000),
        ]
    }

    years = sorted({r["god"] for r in elec})

    # Build data arrays
    sector_data = {s: [] for s in sectors}
    total_cons, kwh_cap = [], []
    prod_data = {s: [] for s in prod_sources}
    total_prod = []

    for year in years:
        by_flow = {r["nTokovi2017"]: r["vrednost"] for r in elec if r["god"] == year}

        for s in sectors:
            sector_data[s].append(by_flow.get(s, 0) or 0)
        t = sum(sector_data[s][-1] for s in sectors)
        total_cons.append(t)
        p = pop_approx.get(int(year), 7000000)
        kwh_cap.append(t * 277778 / p)

        for s in prod_sources:
            prod_data[s].append(by_flow.get(s, 0) or 0)
        total_prod.append(sum(prod_data[s][-1] for s in prod_sources))

    # 1. Stacked area — consumption by sector
    fig1 = go.Figure()
    for s, label, color in zip(sectors, sector_labels, sector_colors, strict=False):
        fig1.add_trace(
            go.Scatter(
                x=years,
                y=sector_data[s],
                name=label,
                stackgroup="one",
                fillcolor=color,
                line={"width": 0},
                hovertemplate=f"{label}<br>%{{x}}: %{{y:,.0f}} TJ",
            )
        )
    fig1.update_layout(
        **THEME,
        title={"text": "Fina potrošnja električne energije po sektorima (TJ)", "font": {"size": 14}},
        yaxis=dict(**AXIS, title="Terađuli (TJ)", tickformat=","),
        xaxis=dict(**AXIS, title="Godina"),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        margin={"t": 60, "b": 40},
        height=500,
        hoverlabel={"bgcolor": "#1a1a3e"},
    )

    # 2. kWh per capita line
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=years,
            y=kwh_cap,
            mode="lines+markers+text",
            line={"color": "#ffab00", "width": 3},
            marker={"size": 8, "color": "#ffab00"},
            text=[f"{v:,.0f}" for v in kwh_cap],
            textposition="top center",
            textfont={"size": 10, "color": "#ffab00"},
            hovertemplate="Godina %{x}<br>%{y:,.0f} kWh/stanovniku",
        )
    )
    # EU average reference line
    fig2.add_hline(
        y=4200,
        line_dash="dash",
        line_color="#66bb6a",
        annotation_text="EU prosek ≈ 5,500 kWh",
        annotation_position="top right",
        annotation_font={"color": "#66bb6a", "size": 11},
    )
    fig2.update_layout(
        **THEME,
        title={"text": "Potrošnja električne energije po stanovniku (kWh/godišnje)", "font": {"size": 14}},
        yaxis=dict(**AXIS, title="kWh po stanovniku", tickformat=","),
        xaxis=dict(**AXIS, title="Godina"),
        margin={"t": 60, "b": 40},
        height=450,
        showlegend=False,
    )

    # 3. Production mix — stacked bar
    fig3 = go.Figure()
    for s, label, color in zip(prod_sources, prod_labels, prod_colors, strict=False):
        fig3.add_trace(
            go.Bar(
                x=years,
                y=prod_data[s],
                name=label,
                marker_color=color,
                hovertemplate=f"{label}<br>%{{x}}: %{{y:,.0f}} TJ",
            )
        )
    fig3.update_layout(
        **THEME,
        barmode="stack",
        title={"text": "Proizvodnja električne energije po izvorima (TJ)", "font": {"size": 14}},
        yaxis=dict(**AXIS, title="Terađuli (TJ)", tickformat=","),
        xaxis=dict(**AXIS, title="Godina"),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        margin={"t": 60, "b": 40},
        height=500,
    )

    # 4. 2024 sector pie
    idx_2024 = years.index("2024")
    vals_2024 = [sector_data[s][idx_2024] for s in sectors]
    fig4 = go.Figure(
        go.Pie(
            labels=[f"{label}<br>{v:,.0f} TJ" for label, v in zip(sector_labels, vals_2024, strict=False)],
            values=vals_2024,
            marker_colors=sector_colors,
            textinfo="label",
            textfont={"size": 11, "color": "#e8e8f0"},
            hole=0.4,
        )
    )
    fig4.update_layout(
        **THEME,
        title={"text": "Struktura potrošnje — 2024", "font": {"size": 14}},
        showlegend=False,
        margin={"t": 50},
        height=450,
    )

    # Stats
    latest_tj = total_cons[-1]
    latest_kwh = kwh_cap[-1]
    hh_tj = sector_data[sectors[0]][-1]
    ind_tj = sector_data[sectors[1]][-1]
    growth = (total_cons[-1] - total_cons[0]) / total_cons[0] * 100

    stats_html = f"""
<div class="stats">
  <div class="stat"><div class="num gold">{latest_kwh:,.0f}</div><div class="lbl">kWh/stanovniku (2024)</div></div>
  <div class="stat"><div class="num blue">{latest_tj:,.0f}</div><div class="lbl">TJ ukupno (2024)</div></div>
  <div class="stat"><div class="num">{hh_tj / latest_tj * 100:.0f}%</div><div class="lbl">Domaćinstva</div></div>
  <div class="stat"><div class="num">{ind_tj / latest_tj * 100:.0f}%</div><div class="lbl">Industrija</div></div>
  <div class="stat"><div class="num green">{growth:+.1f}%</div><div class="lbl">Rast 2010→2024</div></div>
  <div class="stat"><div class="num">{len(years)}</div><div class="lbl">Godina podataka</div></div>
</div>"""

    html = wrap_html(
        [fig1, fig2, fig3, fig4],
        title="Потрошња <span>електричне енергије</span> Србије",
        subtitle="Energetski bilans RZS 2010–2024 — Fina potrošnja po sektorima i proizvodnja po izvorima · Terađuli",
        meta="Serbia electricity consumption per capita and by sector 2010-2024 from RZS energy balance data",
    )
    html = html.replace("</header>", f"</header>{stats_html}")

    path = OUT / "08_electricity.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✅ {path}")
    return str(path)


async def update_index():
    """Add new demos to index.html."""
    index_path = OUT / "index.html"
    if not index_path.exists():
        return

    content = index_path.read_text(encoding="utf-8")

    new_cards = """
    <div class="demo-card" onclick="location.href='07_population_pyramid.html'">
        <div class="emoji">👤</div>
        <h3>Пирамида становништва</h3>
        <p>Попис 2022 — старосна и полна структура, 6.65M становnika, 202 opština</p>
        <div class="tags"><span class="tag">demografija</span><span class="tag">Попис 2022</span><span class="tag">piramida</span></div>
    </div>
    <div class="demo-card" onclick="location.href='08_electricity.html'">
        <div class="emoji">⚡</div>
        <h3>Потрошња енергије</h3>
        <p>Energetski bilans 2010–2024 — потрошња по секторима, kWh по становнику, производња по изvorima</p>
        <div class="tags"><span class="tag">енергетика</span><span class="tag">RZS</span><span class="tag">15 godina</span></div>
    </div>"""

    # Insert before closing </div> of demo-grid (look for the last demo card pattern)
    if "06_real_estate" in content and "07_population" not in content:
        # Find the end of the last card before the grid closes
        content = content.rstrip()
        # Simple approach: append before </body>
        content = content.replace("</body>", f"{new_cards}\n</body>")
        index_path.write_text(content, encoding="utf-8")
        print(f"  ✅ {index_path}")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print("Demo 7: Population Pyramid")
    await build_population_pyramid()

    print("Demo 8: Electricity Consumption")
    await build_electricity()

    print("Updating index...")
    await update_index()

    print("\n" + "=" * 60)
    print("ALL EXTRA DEMOS DONE")


if __name__ == "__main__":
    asyncio.run(main())
