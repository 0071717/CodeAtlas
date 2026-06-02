#!/usr/bin/env python3

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

root = Path(__file__).resolve().parents[2]
domain_map = root / "atlas" / "global" / "domain-map.yaml"

if not domain_map.exists():
    print(f"Missing domain map: {domain_map}", file=sys.stderr)
    sys.exit(1)

with domain_map.open("r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

domains = data.get("domains", [])

for domain in domains:
    domain_id = domain.get("id")
    if domain_id:
        print(domain_id)
