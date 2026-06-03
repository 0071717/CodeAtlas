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

REQUIRED_MAP_FILES = [
    "repo-map.yaml",
    "domain-map.yaml",
    "code-references.yaml",
    "backend-map.yaml",
    "frontend-map.yaml",
    "api-map.yaml",
    "schema-map.yaml",
    "call-graph.yaml",
    "ui-flow-map.yaml",
    "data-access-map.yaml",
    "validation-map.yaml",
    "permission-map.yaml",
    "error-map.yaml",
    "state-map.yaml",
    "integration-map.yaml",
]

REQUIRED_FACT_FILES = [
    "technical-facts.yaml",
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


def validate_named_files(base_dir: Path, filenames: list[str], label: str) -> tuple[int, list[str]]:
    errors = []
    for filename in filenames:
        path = base_dir / filename
        if not path.exists():
            errors.append(f"Missing required {label} file: {path}")
            continue
        try:
            validate_file(path)
        except Exception as exc:
            errors.append(f"Invalid {label} file {path}: {exc}")
    return (1 if errors else 0, errors)


def validate_global(root: Path) -> int:
    exit_code, errors = validate_named_files(root / "atlas" / "global", REQUIRED_GLOBAL_FILES, "global")
    if errors:
        print("Global validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Global validation passed.")
    return exit_code


def validate_map(root: Path) -> int:
    map_code, map_errors = validate_named_files(root / "atlas" / "map", REQUIRED_MAP_FILES, "map")
    fact_code, fact_errors = validate_named_files(root / "atlas" / "facts", REQUIRED_FACT_FILES, "fact")
    errors = map_errors + fact_errors
    if errors:
        print("Code Map / technical facts validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Code Map / technical facts validation passed.")
    return map_code | fact_code


def validate_domain(root: Path, domain_id: str) -> int:
    domain_dir = root / "atlas" / "domains" / domain_id
    errors = []
    if not domain_dir.exists():
        errors.append(f"Missing domain directory: {domain_dir}")
    else:
        _, errors = validate_named_files(domain_dir, REQUIRED_DOMAIN_FILES, "domain")
    if errors:
        print(f"Validation failed for domain: {domain_id}")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"Validation passed for domain: {domain_id}")
    return 0


def validate_all(root: Path) -> int:
    exit_code = validate_global(root)
    exit_code |= validate_map(root)
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
        print("Usage: validate-artifacts.py <domain_id>|--all|--global|--map")
        sys.exit(1)
    arg = sys.argv[1]
    if arg == "--all":
        sys.exit(validate_all(root))
    if arg == "--global":
        sys.exit(validate_global(root))
    if arg == "--map":
        sys.exit(validate_map(root))
    sys.exit(validate_domain(root, arg))


if __name__ == "__main__":
    main()
