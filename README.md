# funvisis-catalog

Assembles a CSV catalog of earthquake hypocenters located 
by **FUNVISIS** (Fundación Venezolana de Investigaciones Sismológicas). 

The catalog: **[`funvisis_catalog.csv`](funvisis_catalog.csv)**
(~22k events, 2003 → present). Scrape date/time and row count:
**[`funvisis_catalog.meta.json`](funvisis_catalog.meta.json)** (`generated_utc`).

| Source | Period | Notes |
|---|---|---|
| **ISC Bulletin**, agency `FUNV` | ~2003 → 2025-03 | FDSN event service |
| **Report images** (`reporte_<N>.gif`) | 2025-03 → present | OCR of the per-event "Reporte Sismológico Preliminar"; also the incremental **leading edge** (`update` walks new serials) |

> The live HTML bulletin (`sis_mes.php`) is **not used**. It is
> strictly lower-fidelity than the report images it indexes (local-time
> minute precision vs OCR's UTC-to-the-second, forced `Mw`) and is
> month-scoped, so it drops the tail at every month rollover. The report
> images are serial-numbered and never roll over, so `update` walks them
> instead. (`bulletin.py` remains only as an emergency `build --html`
> fallback.)

## CSV schema

```
id, time, latitude, longitude, depth_km, magnitude, mag_type, place, author, event_type
```

- `id` — `ISC<eventid>` (ISC) or `FUNVISIS_R<N>` (report serial number)
- `time` — ISO-8601 UTC
- `author` — `FUNV` (ISC-served) or `FUNVISIS` (report/bulletin)

## Usage

```bash
pip install -r requirements.txt          # requests + pillow + pytesseract

# Incremental update — OCR-walk new report images from the newest serial
# already in the CSV (the leading edge):
python -m funvisis update --csv funvisis_catalog.csv
#   --start N     force the OCR walk to begin at serial N

# Full rebuild from scratch:
python -m funvisis build --out funvisis_catalog.csv
#   --no-images   skip the OCR step (no pillow/tesseract needed)
#   --no-isc
#   --html        legacy: also merge the live bulletin (avoid — see above)
```

Both `update` and `build` (with images) need the `tesseract` binary with
the `spa` traineddata (`brew install tesseract tesseract-lang` /
`apt-get install tesseract-ocr tesseract-ocr-spa`); point at a non-PATH
binary with `TESSERACT_CMD`.

CI (`.github/workflows/update.yml`) installs tesseract and runs `update`
on a schedule, committing the refreshed CSV.

## Attribution

Earthquake parameters © FUNVISIS (Fundación Venezolana de
Investigaciones Sismológicas), Venezuela. Historical origins served by
the International Seismological Centre (ISC) Bulletin, agency `FUNV`.
This tool only reformats public data; cite FUNVISIS and the ISC.

## License

MIT — see [LICENSE](LICENSE). (Applies to the code. The earthquake data
is FUNVISIS/ISC's; attribute accordingly.)
