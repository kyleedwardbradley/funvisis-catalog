from __future__ import annotations

import re
from datetime import datetime, timedelta

from .http import get_text

LIVE_URL = "http://www.funvisis.gob.ve/old/sis_mes.php"
VET_OFFSET_HOURS = 4

_DATE = re.compile(r'^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$')
_REPORTE = re.compile(r'reporte_(\d+)\.gif', re.I)


def _f(s):
    s = (s or "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _clean(cell):
    s = re.sub(r'<[^>]+>', '', cell).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def _hlv_to_utc(date_s, time_s):
    dm = _DATE.match(date_s)
    tm = re.match(r'^\s*(\d{1,2}):(\d{2})', time_s)
    if not dm or not tm:
        return ""
    try:
        local = datetime(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)),
                         int(tm.group(1)), int(tm.group(2)))
    except ValueError:
        return ""
    return (local + timedelta(hours=VET_OFFSET_HOURS)).strftime(
        "%Y-%m-%dT%H:%M:00Z")


def fetch():
    return parse(get_text(LIVE_URL, timeout=60))


def parse(html):
    out = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE):
        cells = [_clean(c) for c in re.findall(
            r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)]
        if len(cells) < 6 or not _DATE.match(cells[0]):
            continue
        iso = _hlv_to_utc(cells[0], cells[1])
        lat, lon = _f(cells[2]), _f(cells[3])
        if not iso or lat is None or lon is None:
            continue
        m = _REPORTE.search(row)
        if m:
            eid = f"FUNVISIS_R{int(m.group(1))}"
        else:
            compact = iso[:16].replace("-", "").replace(":", "").replace("T", "")
            eid = f"FUNVISIS{compact}_{lat:.2f}_{lon:.2f}"
        out.append({
            "id":         eid,
            "time":       iso,
            "latitude":   lat,
            "longitude":  lon,
            "depth_km":   _f(cells[4]),
            "magnitude":  _f(cells[5]),
            "mag_type":   "Mw",
            "place":      cells[6] if len(cells) > 6 else "",
            "author":     "FUNVISIS",
            "event_type": "",
        })
    return out
