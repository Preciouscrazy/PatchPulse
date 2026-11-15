"""Offline pre/post-patch cohort comparison with explicit validation boundaries."""

import csv
import math
from collections import defaultdict

METRICS = ("avg_fps", "p95_frame_ms", "p95_ping_ms", "crashes")
FIELDS = ("match_id", "region", "build", *METRICS)


def _metrics_from_values(raw, context, *, allow_text):
    values = {}
    for metric in METRICS:
        try:
            value = raw[metric]
            if not allow_text and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"{metric} must be numeric")
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"{metric} must be finite and nonnegative")
            if metric == "crashes" and (not number.is_integer() or number > 2**53):
                raise ValueError("crashes must be a nonnegative, exactly representable integer")
            values[metric] = number
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{context}: {exc}") from exc
    return values


def load_rows(path):
    """Parse an exact seven-column UTF-8 CSV with precise source-line errors."""
    rows, seen = [], set()
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            if tuple(next(reader, [])) != FIELDS:
                raise ValueError(f"{path}: expected CSV header: {','.join(FIELDS)}")
            for raw in reader:
                if not raw:
                    continue
                line = reader.line_num
                if len(raw) != len(FIELDS):
                    raise ValueError(f"{path}:{line}: expected exactly seven columns")
                match_id, region, build, *metrics = (value.strip() for value in raw)
                if not match_id or not region or not build:
                    raise ValueError(f"{path}:{line}: match ID, region and build are required")
                if match_id in seen:
                    raise ValueError(f"{path}:{line}: duplicate match ID")
                mapped = dict(zip(METRICS, metrics))
                values = _metrics_from_values(mapped, f"{path}:{line}", allow_text=True)
                seen.add(match_id)
                rows.append({"region": region, **values})
        except csv.Error as exc:
            raise ValueError(f"{path}:{reader.line_num}: malformed CSV: {exc}") from exc
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return rows


def _validate_cohort(rows, label):
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError(f"{label} cohort must contain samples")
    validated = defaultdict(list)
    for index, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"{label} row {index}: expected an object")
        region = raw.get("region")
        if not isinstance(region, str) or not region.strip():
            raise ValueError(f"{label} row {index}: nonempty region required")
        values = _metrics_from_values(raw, f"{label} row {index}", allow_text=False)
        validated[region.strip()].append(values)
    return validated


def _average(samples, metric):
    if not samples:
        return None
    try:
        result = math.fsum(row[metric] for row in samples) / len(samples)
    except OverflowError as exc:
        raise ValueError(f"{metric}: cohort sum exceeds finite numeric range") from exc
    if not math.isfinite(result):
        raise ValueError(f"{metric}: cohort mean exceeds finite numeric range")
    return result


def analyze(before, after, threshold=10.0, min_samples=3):
    """Report region-scoped descriptive changes; no causal interpretation."""
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be numeric")
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be finite and nonnegative")
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 1:
        raise ValueError("min_samples must be a positive integer")

    old_by_region = _validate_cohort(before, "before")
    new_by_region = _validate_cohort(after, "after")
    cohorts = []
    for region in sorted(old_by_region.keys() | new_by_region.keys()):
        old, new = old_by_region.get(region, []), new_by_region.get(region, [])
        sufficient = min(len(old), len(new)) >= min_samples
        metrics = {}
        for metric in METRICS:
            old_avg, new_avg = _average(old, metric), _average(new, metric)
            pct = None
            if old_avg is not None and new_avg is not None and old_avg > 0:
                pct = (new_avg - old_avg) / old_avg * 100
                if not math.isfinite(pct):
                    raise ValueError(f"{metric}: relative change exceeds finite numeric range")
            # With a zero baseline, percentage change is undefined. A new
            # positive undesirable metric (latency/crashes) is flagged explicitly.
            zero_baseline_worsened = (
                old_avg == 0 and new_avg is not None and new_avg > 0
                and metric != "avg_fps"
            )
            worse = (-pct if metric == "avg_fps" else pct) if pct is not None else None
            metrics[metric] = {
                "before": old_avg, "after": new_avg, "change_pct": pct,
                "regression": bool(
                    sufficient and (
                        (worse is not None and worse >= threshold) or zero_baseline_worsened
                    )
                ),
            }
        cohorts.append({
            "region": region,
            "before_count": len(old),
            "after_count": len(new),
            "sufficient_samples": sufficient,
            "metrics": metrics,
        })
    return {
        "threshold_pct": threshold,
        "minimum_samples_per_cohort": min_samples,
        "regions": cohorts,
        "limitations": "Observational differences do not establish patch causality.",
    }
