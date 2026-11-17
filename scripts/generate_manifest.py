#!/usr/bin/env python3
"""SHA-256 manifest of data snapshots, scripts and result tables for Paper 4."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "MANIFEST.sha256"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files() -> list[Path]:
    return sorted((ROOT / "data").glob("*.tsv")) + sorted((ROOT / "scripts").glob("*.py")) \
        + sorted((ROOT / "results").glob("*.csv"))


def generate_manifest() -> int:
    entries = [(sha256_file(p), str(p.relative_to(ROOT))) for p in tracked_files()]
    MANIFEST_PATH.write_text("".join(f"{digest}  {rel}\n" for digest, rel in entries), encoding="utf-8")
    return len(entries)


def verify_manifest() -> list[str]:
    """Return a list of problems (empty if the manifest matches the files exactly)."""
    if not MANIFEST_PATH.is_file():
        return ["MANIFEST.sha256 is missing"]
    recorded = {}
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(maxsplit=1)
            recorded[rel] = digest
    problems = []
    current = {str(p.relative_to(ROOT)): p for p in tracked_files()}
    for rel, digest in recorded.items():
        if rel not in current:
            problems.append(f"listed but missing: {rel}")
        elif sha256_file(current[rel]) != digest:
            problems.append(f"hash mismatch: {rel}")
    for rel in current:
        if rel not in recorded:
            problems.append(f"present but not in manifest: {rel}")
    return problems


if __name__ == "__main__":
    print(f"Manifest written with {generate_manifest()} entries to {MANIFEST_PATH}")
