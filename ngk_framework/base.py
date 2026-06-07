from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

FACT_ID_RE = re.compile(r"\bfact\.[A-Za-z0-9_.:/-]+")
INLINE_FACT_ID_RE = re.compile(r"\[(fact\.[A-Za-z0-9_.:/-]+)\]")
CITATION_BLOCK_RE = re.compile(r"<atlas_citations>\s*(.*?)\s*</atlas_citations>", re.S)
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping malformed or non-object rows.

    Atlas artifact directories are optional and may contain experimental files.
    ngk should still build every usable part of the cache when one row is bad.
    """
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def load_yaml_or_json(path: Path) -> Any:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_id(row: dict[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value:
            return str(value)
    return ""


def json_pointer(path: Path, key: str, index: int) -> str:
    return f"{path.as_posix()}#/{key}/{index}"


def compact_json(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clean_fact_id(value: Any) -> str:
    return str(value).strip().rstrip(".,;:)]}>")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"sha256:[0-9a-fA-F]{64}", value or ""))


def file_hash_candidates(path: Path, start_line: int | None = None, end_line: int | None = None) -> set[str]:
    """Return whole-file and span-content hashes for a source file.

    Atlas producers have historically hashed either entire files or the exact
    line-addressed source span. Supporting both keeps drift checks compatible
    across skeleton artifacts without making missing hash metadata fatal.
    """
    data = path.read_bytes()
    hashes = {sha256_bytes(data)}
    if start_line is not None and end_line is not None:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = lines[max(start_line - 1, 0) : min(end_line, len(lines))]
        span_text = "\n".join(selected)
        hashes.add(sha256_bytes(span_text.encode("utf-8")))
        hashes.add(sha256_bytes((span_text + "\n").encode("utf-8")))
    return hashes


@dataclass
class Evidence:
    evidence_id: str
    fact_id: str
    path: str = ""
    start_line: int | None = None
    end_line: int | None = None
    pointer: str = ""
    method: str = ""
    span_id: str = ""
    repo_id: str = ""


@dataclass
class Fact:
    fact_id: str
    claim: str
    type: str = "unknown"
    confidence: str = "unknown"
    atlas_file: str = ""
    atlas_pointer: str = ""
    subject_id: str = ""
    raw: dict[str, Any] | None = None


class Workspace:
    def __init__(self, root: Path, atlas_dir: str = ".atlas", ngk_dir: str = ".ngk") -> None:
        self.root = root.resolve()
        self.atlas = (self.root / atlas_dir).resolve()
        self.ngk = (self.root / ngk_dir).resolve()
        self.cache = self.ngk / "cache"
        self.sessions = self.ngk / "sessions"
        self.db = self.cache / "atlas.db"
        self.source_root = self.atlas.parent if self.atlas.name == ".atlas" else self.root

