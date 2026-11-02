import csv
import math
from collections import defaultdict
from statistics import mean

METRICS = ("avg_fps", "p95_frame_ms", "p95_ping_ms", "crashes")
REQUIRED = {"match_id", "region", "build", *METRICS}

def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing required CSV columns")
        for line, row in enumerate(reader, start=2):
            try:
                if not row["match_id"] or not row["region"] or not row["build"]:
                    raise ValueError("missing identifying fields")
                values = {key: float(row[key]) for key in METRICS}
                if not all(math.isfinite(value) and value >= 0 for value in values.values()):
                    raise ValueError("metrics must be finite and nonnegative")
                if values["crashes"] != int(values["crashes"]):
                    raise ValueError("crashes must be an integer")
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"{path}:{line}: invalid row: {exc}") from exc
            rows.append({"region": row["region"], **values})
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return rows

def analyze(before, after, threshold=10.0, min_samples=3):
    if threshold < 0 or min_samples < 1:
        raise ValueError("invalid analysis parameters")
    cohorts = []
    for region in sorted({r["region"] for r in before} | {r["region"] for r in after}):
        old = [r for r in before if r["region"] == region]
        new = [r for r in after if r["region"] == region]
        metrics = {}
        sufficient = min(len(old), len(new)) >= min_samples
        for metric in METRICS:
            old_avg = mean(r[metric] for r in old) if old else None
            new_avg = mean(r[metric] for r in new) if new else None
            pct = ((new_avg - old_avg) / old_avg * 100) if old_avg else None
            # Lower FPS is worse; higher latency/crashes are worse.
            worse = -pct if metric == "avg_fps" and pct is not None else pct
            metrics[metric] = {
                "before": old_avg, "after": new_avg, "change_pct": pct,
                "regression": bool(sufficient and worse is not None and worse >= threshold),
            }
        cohorts.append({"region": region, "before_count": len(old),
                        "after_count": len(new), "sufficient_samples": sufficient,
                        "metrics": metrics})
    return {"threshold_pct": threshold, "minimum_samples_per_cohort": min_samples,
            "regions": cohorts, "limitations": "Observational differences do not establish patch causality."}
