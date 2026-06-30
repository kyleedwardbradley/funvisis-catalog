from __future__ import annotations

from datetime import datetime

from .http import get_text, log

ISC_URL = "https://www.isc.ac.uk/fdsnws/event/1/query"
START_YEAR = 2003

_SPLIT = ("413", "429", "500", "502", "503", "504",
          "timed out", "timeout", "Read timed out")


def _overload(err: str) -> bool:
    return any(s in err for s in _SPLIT)


def _fmt(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def _f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def fetch(start_year=START_YEAR, cutover=datetime(2025, 3, 18)):
    out = []
    for y in range(start_year, cutover.year + 1):
        s = datetime(y, 1, 1)
        e = datetime(y + 1, 1, 1)
        if s >= cutover:
            break
        if e > cutover:
            e = cutover
        text = _fetch_range(s, e)
        recs = parse(text)
        out.extend(recs)
        log(f"[isc] {y}: +{len(recs)} ({len(out)} total)")
    return out


def _fetch_range(start, end, depth=0):
    params = {
        "contributor": "FUNV",
        "starttime": _fmt(start), "endtime": _fmt(end),
        "orderby": "time-asc", "format": "text",
    }
    try:
        return get_text(ISC_URL, params=params, timeout=240)
    except Exception as e:
        span = end - start
        mid = start + span / 2
        if _overload(str(e)) and depth < 12 and span.days > 1 \
                and start < mid < end:
            return ((_fetch_range(start, mid, depth + 1) or "")
                    + "\n" + (_fetch_range(mid, end, depth + 1) or ""))
        log(f"[isc] window {start:%Y-%m-%d}..{end:%Y-%m-%d} failed: {e}")
        return ""


def parse(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split("|")
        if len(p) < 13:
            continue
        eid = p[0].strip()
        if not eid:
            continue
        t = p[1].strip()
        out.append({
            "id":         f"ISC{eid}",
            "time":       (t + "Z") if t and not t.endswith("Z") else t,
            "latitude":   _f(p[2]),
            "longitude":  _f(p[3]),
            "depth_km":   _f(p[4]),
            "magnitude":  _f(p[10]),
            "mag_type":   p[9].strip(),
            "place":      p[12].strip(),
            "author":     p[5].strip() or "FUNV",
            "event_type": p[13].strip() if len(p) > 13 else "",
        })
    return out
