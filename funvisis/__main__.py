from __future__ import annotations

import argparse
from datetime import datetime

from . import catalog

DEFAULT_CSV = "funvisis_catalog.csv"


def _cutover(s):
    return datetime.strptime(s, "%Y-%m-%d")


def main(argv=None):
    p = argparse.ArgumentParser(prog="funvisis")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="full rebuild → CSV")
    b.add_argument("--out", default=DEFAULT_CSV)
    b.add_argument("--no-isc", action="store_true", help="skip ISC backbone")
    b.add_argument("--no-images", action="store_true",
                   help="skip report-image OCR (no pillow/tesseract needed)")
    b.add_argument("--no-html", action="store_true", help="skip live bulletin")
    b.add_argument("--cutover", type=_cutover, default=_cutover("2025-03-18"),
                   help="ISC owns < this date; images/bulletin own >=")
    b.add_argument("--start-year", type=int, default=2003)
    b.add_argument("--image-floor", type=int, default=23857)

    u = sub.add_parser("update", help="merge the live bulletin into a CSV")
    u.add_argument("--csv", default=DEFAULT_CSV)

    a = p.parse_args(argv)
    if a.cmd == "build":
        catalog.build(a.out, do_isc=not a.no_isc, do_images=not a.no_images,
                      do_html=not a.no_html, cutover=a.cutover,
                      start_year=a.start_year, image_floor=a.image_floor)
    elif a.cmd == "update":
        catalog.update(a.csv)


if __name__ == "__main__":
    main()
