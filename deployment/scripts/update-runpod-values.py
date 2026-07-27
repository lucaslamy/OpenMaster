#!/usr/bin/env python3
"""Update only OpenMaster image references in an existing Helm values file."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _set_nested(lines: list[str], section: str, key: str, value: str) -> None:
    section_pattern = re.compile(rf"^{re.escape(section)}:\s*(?:#.*)?$")
    section_index = next(
        (index for index, line in enumerate(lines) if section_pattern.match(line.rstrip())),
        None,
    )
    rendered = f"  {key}: {json.dumps(value)}\n"
    if section_index is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend([f"{section}:\n", rendered])
        return
    end = section_index + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
        end += 1
    key_pattern = re.compile(rf"^\s{{2}}{re.escape(key)}:")
    for index in range(section_index + 1, end):
        if key_pattern.match(lines[index]):
            lines[index] = rendered
            return
    lines.insert(end, rendered)


def update_values(path: Path, version: str, registry: str) -> None:
    """Atomically pin API, web, and worker images to one release."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    registry_host = registry.split("/", 1)[0]
    repository_root = registry.split("/", 1)[1] if "/" in registry else ""
    if not repository_root:
        raise ValueError("Registry must include a repository path")
    _set_nested(lines, "image", "registry", registry_host)
    _set_nested(lines, "image", "repository", f"{repository_root}/api")
    _set_nested(lines, "image", "tag", version)
    _set_nested(lines, "api", "image", f"{registry}/api:{version}")
    _set_nested(lines, "web", "image", f"{registry}/web:{version}")
    _set_nested(lines, "workers", "image", f"{registry}/api:{version}")
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text("".join(lines), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    """Validate CLI arguments and update one values file."""
    if len(sys.argv) != 4:
        print("Usage: update-runpod-values.py VALUES VERSION REGISTRY", file=sys.stderr)
        return 2
    try:
        update_values(Path(sys.argv[1]), sys.argv[2], sys.argv[3].rstrip("/"))
    except (OSError, ValueError) as error:
        print(f"Cannot update values: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
