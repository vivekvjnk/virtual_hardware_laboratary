#!/usr/bin/env python3
"""Scaffold an empty Engineering Capability Package (ECP) directory skeleton.

Usage:
    python scaffold_ecp.py --name <package-name> --dest <target-dir> [--description "..."]

Creates:
    <dest>/<package-name>/SKILL.md   (frontmatter stub, ready to fill in)
    <dest>/<package-name>/tools/
    <dest>/<package-name>/references/
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

## Overview
TODO: what this capability does and the core concept behind it.

## When to use this skill
- TODO

## Inputs / Prerequisites
- TODO

## Workflow
1. TODO

## Verification
- TODO
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="lowercase-hyphenated package name")
    parser.add_argument("--dest", required=True, help="destination directory to create the package in")
    parser.add_argument(
        "--description",
        default="TODO: what this does and when to use it.",
        help="frontmatter description text",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not NAME_PATTERN.match(args.name):
        print(f"error: --name '{args.name}' must be lowercase, hyphenated (e.g. 'my-package')", file=sys.stderr)
        return 1

    package_dir = Path(args.dest) / args.name
    tools_dir = package_dir / "tools"
    references_dir = package_dir / "references"
    skill_file = package_dir / "SKILL.md"

    if skill_file.exists():
        print(f"error: {skill_file} already exists, refusing to overwrite", file=sys.stderr)
        return 1

    tools_dir.mkdir(parents=True, exist_ok=True)
    references_dir.mkdir(parents=True, exist_ok=True)

    title = args.name.replace("-", " ").title()
    skill_file.write_text(
        SKILL_TEMPLATE.format(name=args.name, description=args.description, title=title),
        encoding="utf-8",
    )

    print(f"Created ECP skeleton at {package_dir}")
    print(f"  {skill_file}")
    print(f"  {tools_dir}/")
    print(f"  {references_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
