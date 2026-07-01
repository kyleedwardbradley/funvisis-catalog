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
    b.add_argument("--html", action="store_true",
                   help="legacy: also merge the live HTML bulletin "
                        "(lower-fidelity; overwrites OCR rows — avoid)")
    b.add_argument("--cutover", type=_cutover, default=_cutover("2025-03-18"),
                   help="ISC owns < this date; report images own >=")
    b.add_argument("--start-year", type=int, default=2003)
    b.add_argument("--image-floor", type=int, default=23857)

    u = sub.add_parser(
        "update", help="OCR-walk new report images into a CSV (leading edge)")
    u.add_argument("--csv", default=DEFAULT_CSV)
    u.add_argument("--start", type=int, default=None,
                   help="serial to start the OCR walk from "
                        "(default: newest FUNVISIS_R<N> already in the CSV)")

    a = p.parse_args(argv)
    if a.cmd == "build":
        catalog.build(a.out, do_isc=not a.no_isc, do_images=not a.no_images,
                      do_html=a.html, cutover=a.cutover,
                      start_year=a.start_year, image_floor=a.image_floor)
    elif a.cmd == "update":
        catalog.update(a.csv, start=a.start)


if __name__ == "__main__":
    main()
