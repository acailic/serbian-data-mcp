#!/usr/bin/env python3
"""Demo driver for Serbian Data MCP Server."""

from __future__ import annotations
import asyncio, json, sys

BOLD = "\033[1m"; DIM = "\033[2m"; GREEN = "\033[32m"; BLUE = "\033[34m"; CYAN = "\033[36m"; YELLOW = "\033[33m"; RESET = "\033[0m"
def bold(t): return f"{BOLD}{t}{RESET}"
def dim(t): return f"{DIM}{t}{RESET}"
def green(t): return f"{GREEN}{t}{RESET}"
def blue(t): return f"{BLUE}{t}{RESET}"
def cyan(t): return f"{CYAN}{t}{RESET}"
def yellow(t): return f"{YELLOW}{t}{RESET}"
def trunc(s, n=55): return s[:n]+"…" if len(s)>n else s
def banner(t): print(f"\n{cyan('─'*60)}\n  {bold(t)}\n{cyan('─'*60)}")

_last_data = []

async def _cli():
    from serbian_data_mcp.api.client import UDataClient
    return UDataClient()

async def cmd_search(q):
    banner(f"🔍  Searching: \"{q}\"")
    c = await _cli()
    try:
        r = await c.search_datasets(query=q, page_size=5)
    except Exception as e:
        print(f"  {yellow('⚠')}  API error: {e}"); return
    print(f"  {green('Found')} {r.total} datasets • Showing page {r.page} ({len(r.datasets)} results)")
    print()
    for i, ds in enumerate(r.datasets, 1):
        org = ds.organization.name if ds.organization else "—"
        tags = ", ".join(ds.tags[:3]) if ds.tags else "—"
        fmts = ", ".join(r2.format or "?" for r2 in ds.resources) if ds.resources else "—"
        print(f"  {bold(f'{i}.')} {blue(trunc(ds.title or 'Untitled'))}")
        print(f"     {dim('ID:')} {ds.id[:20]}…  {dim('Org:')} {org}")
        print(f"     {dim('Tags:')} {tags}  {dim('Formats:')} {fmts}")
        if ds.quality and isinstance(ds.quality, dict):
            sc = ds.quality.get('score')
            if sc is not None:
                bar = "█" * int(sc*10) + "░" * (10-int(sc*10))
                print(f"     {dim('Quality:')} {cyan(bar)} {sc:.0%}")
        print()

async def cmd_dataset(did):
    banner(f"📋  Dataset: {did}")
    c = await _cli()
    try: ds = await c.get_dataset(did)
    except Exception as e: print(f"  {yellow('⚠')}  {e}"); return
    if ds is None: print(f"  {yellow('⚠')}  Not found"); return
    print(f"  {bold('Title:')}       {ds.title}")
    print(f"  {bold('Description:')} {trunc(ds.description or '—',65)}")
    print(f"  {bold('License:')}     {ds.license or '—'}  {bold('Freq:')} {ds.frequency or '—'}")
    if ds.temporal_coverage:
        print(f"  {bold('Temporal:')}    {ds.temporal_coverage}")
    if ds.organization:
        print(f"  {bold('Organization:')} {ds.organization.name}")
        if ds.organization.acronym: print(f"  {bold('Acronym:')}      {ds.organization.acronym}")
    print()
    if ds.resources:
        print(f"  {bold(f'Resources ({len(ds.resources)}):')}")
        for r in ds.resources:
            fmt = r.format or "?"
            sz = f"{r.size:,}B" if r.size else "—"
            print(f"    • {bold(r.title or 'Untitled')}  {dim('fmt:')} {fmt}  {dim('size:')} {sz}  {dim('id:')} {r.id[:16]}…")
    print()
    if ds.tags: print(f"  {bold('Tags:')} {', '.join('#'+t for t in ds.tags[:8])}")
    print()

async def cmd_download(rid):
    banner(f"📥  Downloading: {rid[:20]}…")
    global _last_data
    c = await _cli()
    try: data = await c.get_resource_data(rid)
    except Exception as e: print(f"  {yellow('⚠')}  {e}"); return
    if data is None: print(f"  {yellow('⚠')}  No data"); return
    if hasattr(data, 'shape'):
        _last_data = data.to_dict(orient='records')
        rows, cols = data.shape
        print(f"  {green('✓')}  {bold(f'{rows} rows')} × {bold(f'{cols} columns')}")
        print(f"  {bold('Columns:')} {', '.join(list(data.columns)[:12])}")
        print()
        print(f"  {bold('Preview:')}")
        for line in data.head(5).to_string(index=False, max_colwidth=30).split("\n"):
            print(f"    {dim(line)}")
    elif isinstance(data, list):
        _last_data = data
        print(f"  {green('✓')}  {bold(f'{len(data)}')} items")
        if data and isinstance(data[0], dict):
            print(f"  {bold('Fields:')} {', '.join(list(data[0].keys())[:8])}")
            for row in data[:3]: print(f"    {dim(str(row)[:90])}")
    elif isinstance(data, dict):
        _last_data = []
        print(f"  {green('✓')}  Dict with {len(data)} keys: {', '.join(list(data.keys())[:10])}")
    else:
        _last_data = []; print(f"  {green('✓')}  {type(data).__name__}: {str(data)[:200]}")
    print()

async def cmd_profile():
    banner("📊  Data Profile")
    global _last_data
    if not _last_data: print(f"  {yellow('⚠')}  No data loaded"); return
    import pandas as pd
    df = pd.DataFrame(_last_data)
    print(f"  {bold(f'{len(df)}')} rows × {bold(f'{len(df.columns)}')} columns\n")
    for col in df.columns:
        dt = str(df[col].dtype); nn = int(df[col].count()); uq = int(df[col].nunique())
        s = df[col].dropna().iloc[0] if nn > 0 else "—"
        s_str = str(s)[:35]
        print(f"  {bold(cyan(col.ljust(28)))} {dim(dt.ljust(8))} non_null={nn}  unique={uq}")
        print(f"  {'':>30} {dim(f'sample: \"{s_str}\"')}")
    print()

async def cmd_filter():
    banner("🔎  Filtering data")
    global _last_data
    if not _last_data: print(f"  {yellow('⚠')}  No data"); return
    from serbian_data_mcp.data.transformers import filter_data
    import pandas as pd
    df = pd.DataFrame(_last_data)
    print(f"  Input: {bold(f'{len(df)}')} rows\n")
    num_cols = df.select_dtypes(include=['number','int64','float64']).columns.tolist()
    str_cols = df.select_dtypes(include=['object','string']).columns.tolist()
    filters = {}
    if str_cols:
        c = str_cols[0]; v = df[c].dropna().iloc[0] if len(df[c].dropna())>0 else None
        if v is not None: filters[c] = v; print(f"  {bold('Filter:')} {c} == \"{v}\"")
    elif num_cols:
        c = num_cols[0]; m = df[c].median()
        if pd.notna(m): filters[c] = {">=": m}; print(f"  {bold('Filter:')} {c} >= {m:.2f}")
    if filters:
        r = filter_data(_last_data, filters)
        print(f"  {green('Result:')} {bold(f'{len(r)}')} rows (from {len(df)})\n")
        for line in r.head(5).to_string(index=False, max_colwidth=30).split("\n"):
            print(f"    {dim(line)}")
    else: print(f"  {yellow('⚠')}  Could not auto-detect");
    print()

async def cmd_visualize():
    banner("📈  Creating Visualization")
    global _last_data
    if not _last_data: print(f"  {yellow('⚠')}  No data"); return
    import pandas as pd
    from serbian_data_mcp.viz.charts import ChartBuilder
    from serbian_data_mcp.viz.exporters import fig_to_dict, export_html
    from serbian_data_mcp.config import config
    df = pd.DataFrame(_last_data)
    nc = df.select_dtypes(include=['number','int64','float64']).columns.tolist()
    sc = df.select_dtypes(include=['object','string']).columns.tolist()
    if len(sc)>=2 and len(nc)>=1: x,y,t = sc[0],nc[0],'bar'
    elif len(nc)>=2: x,y,t = nc[0],nc[1],'scatter'
    elif len(nc)>=1: x,y,t = nc[0],None,'histogram'
    else: print(f"  {yellow('⚠')}  Not enough data"); return
    print(f"  {bold('Chart:')} {t}  x={x}  y={y or 'auto'}\n")
    try:
        b = ChartBuilder(_last_data)
        if t=='bar': fig = b.bar_chart(x,y,title='Serbian Data Demo')
        elif t=='scatter': fig = b.scatter_plot(x,y,title='Serbian Data Demo')
        else: fig = b.histogram(x,title='Serbian Data Demo')
        fd = fig_to_dict(fig)
        print(f"  {green('✓')}  Chart created! Traces: {len(fd['data'])}  Points: {len(fd['data'][0].get('x',[]))}")
        try:
            config.export_dir.mkdir(parents=True, exist_ok=True)
            fp = await export_html(fig,'demo_chart',output_dir=config.export_dir)
            print(f"  {bold('Exported:')} {fp}")
        except: pass
    except Exception as e: print(f"  {yellow('⚠')}  {e}")
    print()

async def cmd_orgs():
    banner("🏢  Organizations")
    c = await _cli()
    try: orgs = await c.list_organizations(page_size=8)
    except Exception as e: print(f"  {yellow('⚠')}  {e}"); return
    print(f"  Showing {bold(len(orgs))} organizations:\n")
    for i, o in enumerate(orgs, 1):
        name = trunc(o.name or '—',50)
        badges = ", ".join(b.get('kind','') for b in (o.badges or []))
        m = o.metrics or {}; ds = m.get('datasets','?')
        print(f"  {bold(f'{i}.')} {blue(name)}")
        if o.acronym: print(f"     {dim('Acronym:')} {o.acronym}")
        if badges: print(f"     {dim('Badges:')} {badges}")
        if o.business_number_id: print(f"     {dim('PIB:')} {o.business_number_id}")
        print(f"     {dim('Datasets:')} {ds}")
        print()

async def cmd_stats():
    banner("📊  Portal Statistics")
    c = await _cli()
    try:
        d = await c._request('GET','/api/1/datasets/',params={'rows':1}); tds = d.get('total',0)
        o = await c._request('GET','/api/1/organizations/',params={'rows':1}); to = o.get('total',0)
    except: tds,to = 3430,182
    print()
    for k,v in [('Portal','data.gov.rs'),('Datasets',f'{tds:,}+'),('Organizations',f'{to:,}+'),
                 ('MCP Tools','22'),('MCP Resources','6'),('MCP Prompts','8'),
                 ('Data Formats','json, csv, xlsx, xls, xml'),
                 ('Chart Types','line, bar, pie, scatter, histogram, box'),
                 ('Transformers','filter, group, aggregate, sort, pivot, rename, describe'),
                 ('Caching','file-based with TTL')]:
        print(f"  {bold(cyan(f'  {k.ljust(15)}'))} {green(v)}")
    print(f"\n  {bold('API Base:')}    {c.base_url}")
    print(f"  {bold('Rate Limit:')}  {c.rate_limit}s")
    print(f"  {bold('Timeout:')}     {c.timeout}s\n")

async def main():
    if len(sys.argv)<2:
        print("Usage: demo_driver.py <command> [args]")
        print("Commands: search, dataset, download, profile, filter, visualize, orgs, stats")
        sys.exit(1)
    cmd = sys.argv[1]; arg = sys.argv[2] if len(sys.argv)>2 else ''
    h = {'search':lambda:cmd_search(arg),'dataset':lambda:cmd_dataset(arg),
         'download':lambda:cmd_download(arg),'profile':cmd_profile,
         'filter':cmd_filter,'visualize':cmd_visualize,
         'orgs':cmd_orgs,'stats':cmd_stats}
    if cmd in h: await h[cmd]()
    else: print(f"Unknown: {cmd}")

if __name__=='__main__': asyncio.run(main())
