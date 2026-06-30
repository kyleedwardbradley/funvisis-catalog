from __future__ import annotations

import csv
from datetime import datetime

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


def build(out_path, do_isc=True, do_images=True, do_html=True,
          cutover=datetime(2025, 3, 18), start_year=isc.START_YEAR,
          image_floor=images.FLOOR):
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
    log(f"[build] wrote {n} records → {out_path}")
    return n


def update(csv_path):
    catalog = read_csv(csv_path)
    before = len(catalog)
    merge(catalog, bulletin.fetch())
    n = write_csv(catalog, csv_path)
    log(f"[update] {csv_path}: {before} → {n} (+{n - before})")
    return n
