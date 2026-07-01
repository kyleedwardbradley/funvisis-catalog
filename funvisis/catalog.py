from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from . import bulletin, images, isc
from .http import log

FIELDS = ["id", "time", "latitude", "longitude", "depth_km",
          "magnitude", "mag_type", "place", "author", "event_type"]


def read_csv(path):
    out = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["id"]] = _typed(row)
    except FileNotFoundError:
        pass
    return out


def write_csv(records, path):
    rows = list(records.values()) if isinstance(records, dict) else list(records)
    rows.sort(key=lambda r: (r.get("time") or ""))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def merge(base, new):
    for r in new:
        if r.get("id"):
            base[r["id"]] = r
    return base


def _typed(row):
    for k in ("latitude", "longitude", "depth_km", "magnitude"):
        v = (row.get(k) or "").strip()
        row[k] = float(v) if v else None
    return row


def meta_path(csv_path):
    base = csv_path[:-4] if csv_path.endswith(".csv") else csv_path
    return base + ".meta.json"


def write_meta(records, csv_path, generated=None):
    rows = list(records.values()) if isinstance(records, dict) else list(records)
    times = sorted(r.get("time") for r in rows if r.get("time"))
    by_author = {}
    for r in rows:
        a = r.get("author") or ""
        by_author[a] = by_author.get(a, 0) + 1
    meta = {
        "generated_utc": generated or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "rows": len(rows),
        "time_range": {"min": times[0] if times else None,
                       "max": times[-1] if times else None},
        "by_author": dict(sorted(by_author.items())),
        "source": "https://github.com/kyleedwardbradley/funvisis-catalog",
    }
    with open(meta_path(csv_path), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    return meta


def build(out_path, do_isc=True, do_images=True, do_html=False,
          cutover=datetime(2025, 3, 18), start_year=isc.START_YEAR,
          image_floor=images.FLOOR):
    # `do_html` (the live HTML bulletin) is off by default and is a legacy
    # fallback only. The bulletin is strictly lower-fidelity than the report
    # images it indexes — local-time minute precision vs OCR's UTC-to-the-
    # second, forced Mw, month-scoped — and because it merges after the OCR
    # pass it would OVERWRITE the higher-fidelity image rows for the same
    # FUNVISIS_R<N> id. Prefer OCR (`do_images`) for the recent period.
    catalog = {}
    if do_isc:
        merge(catalog, isc.fetch(start_year=start_year, cutover=cutover))
        log(f"[build] after ISC: {len(catalog)}")
    if do_images:
        merge(catalog, images.walk(start=image_floor))
        log(f"[build] after images: {len(catalog)}")
    if do_html:
        merge(catalog, bulletin.fetch())
        log(f"[build] after bulletin: {len(catalog)}")
    n = write_csv(catalog, out_path)
    write_meta(catalog, out_path)
    log(f"[build] wrote {n} records → {out_path}")
    return n


_SERIAL_PREFIX = "FUNVISIS_R"


def _max_serial(catalog, floor=images.FLOOR):
    """Highest ``FUNVISIS_R<N>`` report serial present in the catalog, or
    the OCR floor when none are on file yet."""
    best = floor
    for eid in catalog:
        if eid.startswith(_SERIAL_PREFIX):
            try:
                best = max(best, int(eid[len(_SERIAL_PREFIX):]))
            except ValueError:
                pass
    return best


def update(csv_path, start=None):
    """Incrementally extend the catalog by OCR-walking the report images
    (``reporte_<N>.gif``) forward from the newest serial already on file.

    The report images are the authoritative per-event source — UTC to the
    second, real depth/magnitude, serial-numbered — and the walk is not
    month-scoped, so unlike the live HTML bulletin it can't lose the tail
    at a month rollover. Needs the OCR deps (pillow + pytesseract + the
    tesseract binary with the ``spa`` traineddata); `images.walk` fails
    loudly if they're missing.
    """
    catalog = read_csv(csv_path)
    before = len(catalog)
    if start is None:
        start = _max_serial(catalog)
    merge(catalog, images.walk(start=start))
    n = write_csv(catalog, csv_path)
    write_meta(catalog, csv_path)
    log(f"[update] {csv_path}: {before} → {n} (+{n - before}) "
        f"[OCR from #{start}]")
    return n
