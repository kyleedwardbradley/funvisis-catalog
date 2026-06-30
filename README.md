# funvisis-catalog

A small, standalone scraper that assembles a CSV catalog of Venezuelan
earthquake hypocenters located by **FUNVISIS** (Fundación Venezolana de
Investigaciones Sismológicas). 

The catalog: **[`funvisis_catalog.csv`](funvisis_catalog.csv)**
(~22k events, 2003 → present). Scrape date/time and row count:
**[`funvisis_catalog.meta.json`](funvisis_catalog.meta.json)** (`generated_utc`).

| Source | Period | Notes |
|---|---|---|
| **ISC Bulletin**, agency `FUNV` | ~2003 → 2025-03 | FDSN event service |
| **Report images** (`reporte_<N>.gif`) | 2025-03 → present | OCR of the per-event "Reporte Sismológico Preliminar" |
| **Live bulletin** (`sis_mes.php`) | current month | HTML table |

## CSV schema

```
id, time, latitude, longitude, depth_km, magnitude, mag_type, place, author, event_type
```

- `id` — `ISC<eventid>` (ISC) or `FUNVISIS_R<N>` (report serial number)
- `time` — ISO-8601 UTC
- `author` — `FUNV` (ISC-served) or `FUNVISIS` (report/bulletin)

## Usage

```bash
pip install -r requirements.txt          # requests; pillow+pytesseract only for OCR

# Dependency-free incremental update (merge the current bulletin):
python -m funvisis update --csv funvisis_catalog.csv

# Full rebuild from scratch:
python -m funvisis build --out funvisis_catalog.csv
#   --no-images   skip the OCR step (no pillow/tesseract needed)
#   --no-isc / --no-html
```

The OCR step (`build` with images) needs the `tesseract` binary with the
`spa` traineddata (`brew install tesseract tesseract-lang` /
`apt-get install tesseract-ocr tesseract-ocr-spa`); point at a non-PATH
binary with `TESSERACT_CMD`. `update` needs only `requests`.

CI (`.github/workflows/update.yml`) runs `update` on a schedule and
commits the refreshed CSV.

## Attribution

Earthquake parameters © FUNVISIS (Fundación Venezolana de
Investigaciones Sismológicas), Venezuela. Historical origins served by
the International Seismological Centre (ISC) Bulletin, agency `FUNV`.
This tool only reformats public data; cite FUNVISIS and the ISC.

## License

MIT — see [LICENSE](LICENSE). (Applies to the code. The earthquake data
is FUNVISIS/ISC's; attribute accordingly.)
