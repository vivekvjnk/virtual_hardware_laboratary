"""
CLI interface for tsci-component-resolver.
Provides subcommands: search, import, scaffold, verify.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .searcher import search_components
from .importer import import_component, _validate_tsx_syntax
from .scaffolder import scaffold_component


def cmd_search(args) -> int:
    result = search_components(
        query=args.query,
        package_filter=args.package,
        min_stock=args.min_stock,
        timeout_sec=args.timeout,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.status == "success":
            print(f"Found {result.total_found} component(s) matching '{args.query}':")
            for idx, item in enumerate(result.results[:10], start=1):
                pref = " [PREFERRED]" if item.is_preferred else ""
                print(
                    f"{idx}. {item.mfr} (C{item.lcsc}){pref} - {item.package} "
                    f"(Stock: {item.stock:,}, Price: ${item.price or 0:.3f})"
                )
                if item.description:
                    print(f"   {item.description[:90]}...")
        elif result.status == "not_found":
            print(f"No components found for '{args.query}' in JLCPCB.")
        elif result.status == "network_error":
            print(f"Network Error: {result.error}", file=sys.stderr)
            return 2
        else:
            print(f"Search Error: {result.error}", file=sys.stderr)
            return 1

    return 0 if result.status == "success" else 1


def cmd_import(args) -> int:
    result = import_component(
        query=args.query,
        dest_dir=args.dest_dir,
        timeout_sec=args.timeout,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.status == "success":
            c_info = f" (from {result.imported_c_code})" if result.imported_c_code else ""
            print(f"✔ Successfully imported {result.component_name}{c_info} -> {result.file_path}")
        elif result.status == "network_error":
            print(f"✖ Network Error: {result.error}", file=sys.stderr)
            return 2
        elif result.status == "not_found":
            print(f"✖ Component '{args.query}' not found.", file=sys.stderr)
            return 1
        else:
            print(f"✖ Import failed: {result.error}", file=sys.stderr)
            return 1

    return result.exit_code


def cmd_scaffold(args) -> int:
    pins = [p.strip() for p in args.pins.split(",")] if args.pins else None
    result = scaffold_component(
        name=args.name,
        footprint=args.footprint or "soic8",
        pins=pins,
        output_dir=args.dest_dir,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"✔ Scaffolded custom component {result.name} ({result.footprint}, {result.pin_count} pins)")
        print(f"  Saved to: {result.file_path}")

    return 0


def cmd_verify(args) -> int:
    target = Path(args.file).resolve()
    if not target.is_file():
        err = f"File not found: {target}"
        if args.json:
            print(json.dumps({"file": str(target), "valid": False, "error": err}, indent=2))
        else:
            print(f"✖ {err}", file=sys.stderr)
        return 1

    is_valid, err = _validate_tsx_syntax(target)
    if args.json:
        print(json.dumps({"file": str(target), "valid": is_valid, "error": err}, indent=2))
    else:
        if is_valid:
            print(f"✔ Valid tscircuit component: {target.name}")
        else:
            print(f"✖ Syntax validation failed: {err}", file=sys.stderr)

    return 0 if is_valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="component_resolver",
        description="Resilient CLI for tscircuit/JLCPCB component resolution, verification, and scaffolding.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Search for components with package and stock filtering")
    p_search.add_argument("query", help="Component name or part number (e.g. NE555, C2040)")
    p_search.add_argument("--package", "-p", default=None, help="Filter by package type (e.g. SOIC-8, TSSOP, 0805)")
    p_search.add_argument("--min-stock", "-s", type=int, default=0, help="Minimum inventory stock required")
    p_search.add_argument("--timeout", "-t", type=float, default=10.0, help="Search timeout in seconds (default: 10s)")
    p_search.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_search.set_defaults(func=cmd_search)

    # --- import ---
    p_import = subparsers.add_parser("import", help="Import component, relocate to ./components, and verify syntax")
    p_import.add_argument("query", help="Component C-code (e.g. C2040) or exact part number")
    p_import.add_argument("--dest-dir", "-d", default="./components", help="Destination folder (default: ./components)")
    p_import.add_argument("--timeout", "-t", type=float, default=30.0, help="Import timeout in seconds (default: 30s)")
    p_import.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_import.set_defaults(func=cmd_import)

    # --- scaffold ---
    p_scaffold = subparsers.add_parser("scaffold", help="Generate a custom tscircuit React component template")
    p_scaffold.add_argument("name", help="Component name (e.g. CustomSensor)")
    p_scaffold.add_argument("--footprint", "-f", default="soic8", help="Footprint type (e.g. soic8, sot23, lqfp32)")
    p_scaffold.add_argument("--pins", default=None, help="Comma-separated pin labels (e.g. VCC,GND,IN,OUT)")
    p_scaffold.add_argument("--dest-dir", "-d", default="./components", help="Destination folder (default: ./components)")
    p_scaffold.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_scaffold.set_defaults(func=cmd_scaffold)

    # --- verify ---
    p_verify = subparsers.add_parser("verify", help="Verify TSX syntax and tscircuit chip structure")
    p_verify.add_argument("file", help="Path to the component TSX file")
    p_verify.add_argument("--json", action="store_true", default=False, help="Output structured JSON")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
