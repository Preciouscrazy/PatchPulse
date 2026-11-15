"""Command-line entry point for PatchPulse's offline cohort comparison."""

import argparse
import json
import os
from pathlib import Path
import tempfile

from .core import analyze, load_rows


def _aliases_source(destination, sources):
    for source in sources:
        if source.resolve() == destination.resolve():
            return True
        if source.exists() and destination.exists() and source.samefile(destination):
            return True
    return False


def _write_json(destination, report):
    """Build a complete JSON document before replacing the destination file."""
    content = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Compare pre/post patch performance telemetry")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", default="report.json")
    parser.add_argument("--threshold", type=float, default=10.0, help="Percent change threshold")
    args = parser.parse_args()
    before, after, destination = Path(args.before), Path(args.after), Path(args.output)
    try:
        if _aliases_source(destination, (before, after)):
            raise ValueError("output must not overwrite either input CSV")
        report = analyze(load_rows(before), load_rows(after), args.threshold)
        _write_json(destination, report)
    except (OSError, ValueError, OverflowError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Saved {destination}")


if __name__ == "__main__":
    main()
