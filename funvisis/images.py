from __future__ import annotations

import io
import os
import re

from .http import get_bytes, head_ok, log

IMG_BASE = ("http://www.funvisis.gob.ve/old/images/reportes/"
            "{y}/{m:02d}/reporte_{n}.gif")
FLOOR = 23857
MAX_CONSEC_MISS = 30
FANOUT = 4


_RE_DATE = re.compile(r'Fecha\s*\(UTC\)[^:]*:\s*(\d{2}/\d{2}/\d{4})', re.I)
_RE_TIME = re.compile(r'Origen\s*\(UTC\)[^:]*:\s*(\d{1,2}:\d{2}:\d{2}(?:[.,]\d)?)', re.I)
_RE_TIME_MIN = re.compile(r'Origen\s*\(UTC\)[^:]*:\s*(\d{1,2}:\d{2})', re.I)
_RE_LAT = re.compile(r'Latitud[^:]*:\s*(\d{1,2}[.,]\d+)', re.I)
_RE_LON = re.compile(r'Longitud[^:]*:\s*(\d{1,3}[.,]\d+)', re.I)
_RE_DEP = re.compile(r'Profundidad[^:]*:\s*(\d+(?:[.,]\d+)?)', re.I)
_RE_MAG = re.compile(r'Magnitud[^:]*:\s*(\d+(?:[.,]\d+)?)', re.I)
_RE_PLACE = re.compile(r'(\d+\s*km\s+al\s+[^()\n]+?)\s*\(Azm', re.I)


def _num(s):
    if s is None:
        return None
    s = s.strip().replace(" ", "")
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _shift(y, m, d):
    idx = (y * 12 + (m - 1)) + d
    return idx // 12, idx % 12 + 1


def _resolve_folder(n, guess, radius=None):
    order = [0, 1, -1, 2, 3][:1 + FANOUT] if radius is None \
        else [0] + [s for r in range(1, radius + 1) for s in (r, -r)]
    for d in order:
        y, m = _shift(*guess, d)
        if 2005 <= y <= 2027 and head_ok(IMG_BASE.format(y=y, m=m, n=n)):
            return (y, m)
    return None


def available():
    try:
        import pytesseract
        from PIL import Image
        return True
    except Exception:
        return False


def _configure():
    import pytesseract
    # Some report GIFs are served partially truncated. Tolerate them so a
    # missing trailing byte range doesn't drop an otherwise-readable image
    # (the parameter text sits mid-image); only images truncated up into
    # the text region are unrecoverable.
    from PIL import ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    cmd = os.environ.get("TESSERACT_CMD") or os.environ.get("STRATUM_TESSERACT")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def walk(start=FLOOR, on_record=None):
    if not available():
        raise RuntimeError(
            "OCR deps missing: pip install pillow pytesseract + the tesseract "
            "binary (spa traineddata).")
    _configure()
    guess = _resolve_folder(start, (2025, 3), radius=48)
    if guess is None:
        log(f"[images] start #{start} not found")
        return []
    n = start
    misses = 0
    out = []
    while True:
        loc = _resolve_folder(n, guess)
        if loc is None:
            misses += 1
            if misses >= MAX_CONSEC_MISS:
                break
            n += 1
            continue
        misses = 0
        guess = loc
        rec = _ocr(n, *loc)
        if rec is not None:
            out.append(rec)
            if on_record:
                on_record(rec)
        if len(out) % 50 == 0 and out:
            log(f"[images] #{n} ({loc[0]}/{loc[1]:02d}), {len(out)} records")
        n += 1
    log(f"[images] done: {len(out)} records, stopped near #{n}")
    return out


def _ocr(n, y, m):
    from PIL import Image, ImageOps
    import pytesseract
    try:
        im = Image.open(io.BytesIO(get_bytes(IMG_BASE.format(y=y, m=m, n=n)))).convert("L")
    except Exception:
        return None
    w, h = im.size
    crop = ImageOps.autocontrast(im.crop((0, int(h * 0.62), w, h)))
    crop = crop.resize((crop.width * 3, crop.height * 3))
    try:
        t = re.sub(r'[ \t]+', ' ', pytesseract.image_to_string(
            crop, lang="spa", config="--psm 6"))
    except Exception:
        return None
    md = _RE_DATE.search(t)
    if not md:
        return None
    lonm = _RE_LON.search(t)
    tm = _RE_TIME.search(t) or _RE_TIME_MIN.search(t)
    placem = _RE_PLACE.search(t)
    rec = {
        "id":         f"FUNVISIS_R{n}",
        "time":       _iso(md.group(1), tm.group(1) if tm else None),
        "latitude":   _num(_RE_LAT.search(t).group(1)) if _RE_LAT.search(t) else None,
        "longitude":  (-_num(lonm.group(1))) if lonm else None,
        "depth_km":   _num(_RE_DEP.search(t).group(1)) if _RE_DEP.search(t) else None,
        "magnitude":  _num(_RE_MAG.search(t).group(1)) if _RE_MAG.search(t) else None,
        "mag_type":   "Mw",
        "place":      placem.group(1).strip() if placem else "",
        "author":     "FUNVISIS",
        "event_type": "",
    }
    return rec if _sane(rec) else None


def _iso(date_dmy, time_hms):
    d, mo, y = date_dmy.split("/")
    if time_hms:
        time_hms = time_hms.replace(",", ".")
        if len(time_hms.split(":")) == 2:
            time_hms += ":00"
    else:
        time_hms = "00:00:00"
    return f"{y}-{mo}-{d}T{time_hms}Z"


def _sane(r):
    from datetime import datetime
    try:
        lat, lon = r["latitude"], r["longitude"]
        if lat is None or lon is None:
            return False
        if not (0.0 <= lat <= 16.5) or not (-74.0 <= lon <= -58.0):
            return False
        if r["depth_km"] is not None and not (0.0 <= r["depth_km"] <= 400.0):
            return False
        if r["magnitude"] is not None and not (-1.0 <= r["magnitude"] <= 9.0):
            return False
        datetime.fromisoformat(r["time"].replace("Z", ""))
        return True
    except Exception:
        return False
