# NF Hotel Analytics API

Secure FastAPI service that cleans NF Hotel booking data, computes descriptive
statistics, and asks a local LLM to turn those statistics into a marketing /
operations report in markdown.

## Architecture

Clean-architecture layering, each concern isolated behind classes/interfaces:

```
src/nf_hotel_api/
  domain/          # Pydantic models (Booking, ReportResponse, HotelMetadata) - no framework/IO deps
  repositories/     # Where data comes from: CsvBookingRepository, JsonBookingRepository, JsonHotelMetadataRepository
  services/         # Business logic
    cleaning.py       # DataCleaningService - wrong format / empty cells / wrong data / duplicates / pricing
    statistics.py      # DescriptiveStatsService - df.describe() (booking_id dropped)
    llm_report.py       # LLMReportService - calls the local LLM, strips <think> blocks
    report.py             # ReportService - orchestrates the above use case
  api/               # FastAPI routers, DI wiring, HTTP-only concerns
  core/              # Settings (env config) and API-key security
```

Dependencies point inward: `api` -> `services` -> `domain`, and `repositories`
implement an abstract interface consumed by `services`, so the analysis logic
never depends on FastAPI or pandas I/O directly.

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
cp .env.example .env
# edit .env: set API_KEY, and point LLM_BASE_URL at your local
# OpenAI-compatible inference server serving qwen3.8-whittle-moe-27b-a17.8b
```

## Run

```bash
.venv/Scripts/python -m uvicorn nf_hotel_api.main:app --app-dir src --reload
```

Docs: http://localhost:8000/docs

## Security

Every `/api/v1/*` route requires an `X-API-Key` header matching `API_KEY`
from the environment, checked with a constant-time comparison
(`secrets.compare_digest`). CORS is locked to `ALLOWED_ORIGINS`. Never commit
the real `.env`.

## Endpoints

- `GET /health` - unauthenticated liveness check.
- `POST /api/v1/report/from-file` - runs the report over the bundled
  `data/nf_hotel_bookings.csv`.
- `POST /api/v1/report/from-json` - runs the report over booking records
  supplied in the request body, same shape as the CSV columns.

### JSON format for `POST /api/v1/report/from-json`

Request body is `{"records": [<Booking>, ...]}`, at least one record. Each
`Booking` has these fields (mirrors [domain/schemas.py](src/nf_hotel_api/domain/schemas.py)):

| Field | Type | Example |
|---|---|---|
| `booking_id` | int | `1` |
| `hotel` | string | `"NF Hotel"` |
| `is_canceled` | int (0/1) | `0` |
| `lead_time` | int | `342` |
| `arrival_date_week_number` | int | `27` |
| `booking_date` | string (`YYYY-MM-DD` or `DD-MM-YYYY`) | `"2017-07-24"` |
| `arrival_date` | string (`YYYY-MM-DD` or `DD-MM-YYYY`) | `"2018-07-01"` |
| `arrival_date_day_of_month` | int | `1` |
| `stays_in_weekend_nights` | int | `0` |
| `stays_in_week_nights` | int | `0` |
| `adults` | int | `2` |
| `children` | int | `0` |
| `babies` | int | `0` |
| `meal` | string | `"BB"` |
| `country` | string | `"Portugal"` |
| `market_segment` | string | `"Direct"` |
| `is_repeated_guest` | int (0/1) | `0` |
| `previous_cancellations` | int | `0` |
| `assigned_room_type` | string (`"A"` small, `"B"` large) | `"A"` |
| `booking_changes` | int | `3` |
| `deposit_type` | string | `"No Deposit"` |
| `agent` | int | `0` |
| `customer_type` | string | `"No Contract (Single)"` |
| `required_car_parking_spaces` | int | `0` |
| `total_of_special_requests` | int | `0` |
| `prize_per_nigth` | number, optional (price paid per night; standard price if omitted) | `20` |

Fields are intentionally accepted as raw/untrusted input - values with the
wrong format, blanks, or implausible numbers are fine; `DataCleaningService`
fixes them before statistics are computed.

A ready-to-use example payload lives in
[examples/sample_booking_request.json](examples/sample_booking_request.json):

```bash
curl -X POST http://localhost:8000/api/v1/report/from-json \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  --data @examples/sample_booking_request.json
```

Both report endpoints return:

```json
{
  "descriptive_stats": { "<column>": { "mean": ..., "top": ..., "...": ... } },
  "llm_report": "## Markdown report from the LLM, <think> blocks stripped"
}
```

## Data cleaning pipeline (`DataCleaningService`)

Applied in order, before any statistics are computed:

1. **Wrong format** - dates parsed to `datetime`, numeric columns coerced to
   numeric, categorical columns trimmed of whitespace.
2. **Empty cells** - blank/placeholder values normalized to `"Unknown"` for
   categoricals and `0` for numerics; rows with unparseable dates are dropped.
3. **Wrong data** - implausible guest counts (e.g. 55 adults) are clipped to
   a sane maximum; bookings with zero total occupants are corrected to one
   adult instead of being discarded.
4. **Duplicates** - exact duplicate bookings (ignoring `booking_id`, which is
   just a row identifier) are removed, keeping the first occurrence.
5. **Pricing** - room size and revenue are derived, and missing prices are
   filled from the hotel metadata (see below).

Dates are accepted as `YYYY-MM-DD` (JSON) and `DD-MM-YYYY` (the CSV export).
Each value is tried against both layouts, so a mixed column does not lose rows.

## Hotel metadata and pricing

Reference data that is not part of the bookings lives in
[data/hotel_metadata.json](data/hotel_metadata.json) (path set by
`METADATA_PATH`, loaded by `JsonHotelMetadataRepository`):

```json
{
  "hotel": "NF Hotel",
  "currency": "USD",
  "room_types": {
    "A": { "size": "Small", "standard_price_per_night": 20, "room_count": null },
    "B": { "size": "Large", "standard_price_per_night": 25, "room_count": null }
  }
}
```

| `assigned_room_type` | `room_size` | Standard price | Rooms in hotel |
|---|---|---|---|
| `A` | Small | $20 | *to be filled in* |
| `B` | Large | $25 | *to be filled in* |

- **`prize_per_nigth` in the CSV is the price the customer actually paid** and
  is never overwritten. Only a missing or negative value is replaced with the
  room type's standard price.
- Room types that are not in the metadata get `room_size = "Unknown"` and no
  invented price.
- `revenue` = (`stays_in_weekend_nights` + `stays_in_week_nights`) x
  `prize_per_nigth` for non-cancelled bookings, `0` for cancelled ones.
- `room_size`, `prize_per_nigth` and `revenue` are part of the descriptive
  statistics sent to the LLM, and the prompt includes the room catalogue
  (standard prices and room counts) from the metadata file.
- `room_count` is `null` until the real number of rooms is known. Occupancy
  rate needs it, so it is not calculated yet. Events are also still missing.

To change a standard price or set a room count, edit `data/hotel_metadata.json`
and restart the service (it is read once at startup).

## Tests

```bash
.venv/Scripts/python -m pytest
```
