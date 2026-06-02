#!/usr/bin/env python3

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REQUIRED_DOMAIN_FILES = [
    "00-domain-scope.yaml",
    "01-backend-inventory.yaml",
    "02-frontend-inventory.yaml",
    "03-code-references.json",
    "04-technical-rules-backend.yaml",
    "04-technical-rules-frontend.yaml",
    "05-contract-mapping.yaml",
    "06-business-rules.yaml",
    "07-user-stories.yaml",
    "08-epics.yaml",
    "09-high-level-requirements.yaml",
    "10-contradictions.yaml",
    "11-dead-code-candidates.yaml",
    "12-review-notes.md",
]

REQUIRED_GLOBAL_FILES = [
    "frontend-inventory.yaml",
    "backend-inventory.yaml",
    "endpoint-index.yaml",
    "ui-route-index.yaml",
    "initial-domain-candidates.yaml",
    "domain-map.yaml",
]

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_file(path: Path):
    if path.suffix in [".yaml", ".yml"]:
        load_yaml(path)
    elif path.suffix == ".json":
        load_json(path)
    return True

def validate_global(root: Path) -> int:
    global_dir = root / "atlas" / "global"
    errors = []
    for filename in REQUIRED_GLOBAL_FILES:
        path = global_dir / filename
        if not path.exists():
            errors.append(f"Missing required global file: {path}")
            continue
        try:
            validate_file(path)
        except Exception as exc:
            errors.append(f"Invalid global file {path}: {exc}")

    if errors:
        print("Global validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Global validation passed.")
    return 0

def validate_domain(root: Path, domain_id: str) -> int:
    domain_dir = root / "atlas" / "domains" / domain_id
    errors = []

    if not domain_dir.exists():
        errors.append(f"Missing domain directory: {domain_dir}")
    else:
        for filename in REQUIRED_DOMAIN_FILES:
            path = domain_dir / filename
            if not path.exists():
                errors.append(f"Missing required file: {path}")
                continue
            try:
                validate_file(path)
            except Exception as exc:
                errors.append(f"Invalid file {path}: {exc}")

    if errors:
        print(f"Validation failed for domain: {domain_id}")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"Validation passed for domain: {domain_id}")
    return 0

def validate_all(root: Path) -> int:
    exit_code = validate_global(root)
    domain_root = root / "atlas" / "domains"

    if not domain_root.exists():
        print(f"Missing domains directory: {domain_root}")
        return 1

    for path in domain_root.iterdir():
        if path.is_dir() and not path.name.startswith("."):
            exit_code |= validate_domain(root, path.name)

    return exit_code

def main():
    root = Path(__file__).resolve().parents[2]

    if len(sys.argv) < 2:
        print("Usage: validate-artifacts.py <domain_id>|--all|--global")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        sys.exit(validate_all(root))
    if arg == "--global":
        sys.exit(validate_global(root))

    sys.exit(validate_domain(root, arg))

if __name__ == "__main__":
    main()
