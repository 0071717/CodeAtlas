#!/usr/bin/env python3
"""Create a lightweight offline graph.html browser for CodeAtlas graph.json."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()


def read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_html(bundle: dict[str, Any]) -> str:
    nodes = bundle.get("nodes", [])
    edges = bundle.get("edges", [])
    safe_json = html.escape(json.dumps({"nodes": nodes, "edges": edges, "summary": bundle.get("summary", {})}))
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>CodeAtlas Graph</title>
<style>
body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 2rem; line-height: 1.45; }}
input {{ box-sizing: border-box; width: 100%; padding: .7rem; margin: 1rem 0; font-size: 1rem; }}
.node {{ border-bottom: 1px solid #ddd; padding: .45rem 0; }}
.badge {{ border: 1px solid #777; border-radius: .4rem; padding: .1rem .35rem; margin-left: .4rem; font-size: .8rem; }}
.meta {{ color: #555; font-size: .9rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .75rem; }}
.card {{ border: 1px solid #ddd; border-radius: .5rem; padding: .75rem; }}
</style>
</head>
<body>
<h1>CodeAtlas Graph</h1>
<p>Offline browser generated from deterministic CodeAtlas artifacts. Use this for navigation; use typed artifacts and validators for authority.</p>
<div class="grid">
  <div class="card"><b id="node-count"></b><br/>nodes</div>
  <div class="card"><b id="edge-count"></b><br/>edges</div>
</div>
<input id="q" placeholder="Filter nodes by id, type, repo, file, or label" />
<div id="nodes"></div>
<script type="application/json" id="graph-data">{safe_json}</script>
<script>
const bundle = JSON.parse(document.getElementById('graph-data').textContent);
const nodes = bundle.nodes || [];
const edges = bundle.edges || [];
document.getElementById('node-count').textContent = nodes.length;
document.getElementById('edge-count').textContent = edges.length;
function label(n) {{ return n.label || n.name || n.path || n.function || n.id; }}
function render() {{
  const q = document.getElementById('q').value.toLowerCase();
  const rows = nodes.filter(n => JSON.stringify(n).toLowerCase().includes(q)).slice(0, 500);
  document.getElementById('nodes').innerHTML = rows.map(n =>
    `<div class="node"><b>${{label(n)}}</b><span class="badge">${{n.type || n.kind || 'unknown'}}</span>` +
    `<div class="meta">${{n.id}} · ${{n.repo || ''}} · ${{n.file || ''}}</div></div>`
  ).join('');
}}
document.getElementById('q').addEventListener('input', render);
render();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create atlas/visualizer/graph.html from graph.json")
    parser.add_argument("--graph", default="atlas/visualizer/graph.json")
    parser.add_argument("--out", default="atlas/visualizer/graph.html")
    args = parser.parse_args()

    bundle = read(ROOT / args.graph, {})
    if not bundle:
        raise SystemExit(f"Could not read {args.graph}. Run codeatlas_v2_canonical.py graph-report first.")
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(bundle), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
