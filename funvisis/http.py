from __future__ import annotations

import sys
import time

import requests

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "funvisis-catalog/1.0"})
    return _session


def get_text(url, params=None, timeout=60, retries=3, backoff=5):
    last = None
    for attempt in range(retries):
        try:
            r = session().get(url, params=params, timeout=timeout)
            if r.status_code == 404:
                r.raise_for_status()
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            last = e
            if r_is_404(e) or attempt == retries - 1:
                raise
            time.sleep(backoff * (attempt + 1))
    raise last


def get_bytes(url, timeout=(10, 30)):
    r = session().get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def head_ok(url, timeout=(10, 30)):
    try:
        r = session().head(url, timeout=timeout, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False


def r_is_404(e):
    resp = getattr(e, "response", None)
    return resp is not None and resp.status_code == 404


def log(msg):
    print(msg, file=sys.stderr, flush=True)
