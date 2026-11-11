import argparse
import json
from .core import analyze, load_rows

def main():
    parser = argparse.ArgumentParser(description="Compare pre/post patch performance telemetry")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", default="report.json")
    parser.add_argument("--threshold", type=float, default=10.0, help="Percent change threshold")
    args = parser.parse_args()
    if args.threshold < 0:
        parser.error("--threshold must be nonnegative")
    try:
        report = analyze(load_rows(args.before), load_rows(args.after), args.threshold)
        with open(args.output, "w", encoding="utf-8") as out:
            json.dump(report, out, indent=2, sort_keys=True)
            out.write("\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Saved {args.output}")

if __name__ == "__main__":
    main()
