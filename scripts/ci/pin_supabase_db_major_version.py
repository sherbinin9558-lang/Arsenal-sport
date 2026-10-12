#!/usr/bin/env python3
"""Pin a disposable Supabase restore config to the Production PostgreSQL major version."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

def pin_major_version(config_path: Path, major_version: int = 17) -> None:
    if major_version < 1:
        raise ValueError("major_version must be a positive integer")
    if not config_path.is_file():
        raise FileNotFoundError(f"Supabase config not found: {config_path}")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    db_headers = [i for i, line in enumerate(lines) if line.strip() == "[db]"]
    if len(db_headers) != 1:
        raise ValueError("Supabase config must contain exactly one [db] section")
    db_start = db_headers[0]
    db_end = next((i for i in range(db_start + 1, len(lines)) if re.match(r"^\s*\[", lines[i])), len(lines))
    version_lines = [i for i in range(db_start + 1, db_end) if re.match(r"^\s*major_version\s*=", lines[i])]
    if len(version_lines) > 1:
        raise ValueError("Supabase [db] section has duplicate major_version keys")
    desired = f"major_version = {major_version}"
    if version_lines:
        lines[version_lines[0]] = desired
    else:
        lines.insert(db_start + 1, desired)
    updated = "\n".join(lines) + "\n"
    match = re.search(r"(?ms)^\[db\]\s*(.*?)(?=^\[|\Z)", updated)
    if not match:
        raise ValueError("Unable to validate the [db] section after update")
    values = re.findall(r"(?m)^\s*major_version\s*=\s*(\d+)\s*$", match.group(1))
    if values != [str(major_version)]:
        raise ValueError(f"Failed to pin [db].major_version to {major_version}")
    config_path.write_text(updated, encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to supabase/config.toml")
    parser.add_argument("--major-version", type=int, default=17)
    args = parser.parse_args()
    try:
        pin_major_version(args.config, args.major_version)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Disposable restore target pinned to PostgreSQL {args.major_version}.")

if __name__ == "__main__":
    main()
