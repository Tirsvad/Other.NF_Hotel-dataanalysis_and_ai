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
    public_holidays.py  # PublicHolidayCalendar - Cambodian holidays from the `holidays` package
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

| Field | Content |
|---|---|
| `hotel`, `address`, `currency` | NF Hotel, Street 172, Phnom Penh, Cambodia; prices in USD |
| `room_types` | per `assigned_room_type`: size, standard price per night, number of rooms |
| `nearby_events` | events in Phnom Penh 2022-2025 (name, dates, venue, `source_url`) |

| `assigned_room_type` | `room_size` | Standard price | Rooms in hotel |
|---|---|---|---|
| `A` | Small | $20 | 10 |
| `B` | Large | $25 | 10 |

- **`prize_per_nigth` in the CSV is the price the customer actually paid** and
  is never overwritten. Only a missing or negative value is replaced with the
  room type's standard price.
- Room types that are not in the metadata get `room_size = "Unknown"` and no
  invented price.
- `revenue` = (`stays_in_weekend_nights` + `stays_in_week_nights`) x
  `prize_per_nigth` for non-cancelled bookings, `0` for cancelled ones.
- `room_size`, `prize_per_nigth` and `revenue` are part of the descriptive
  statistics sent to the LLM. The prompt also includes the metadata (address,
  room types with prices and room counts, nearby events) and the public
  holidays for the years in the data.

To change a price, a room count, a holiday or an event, edit
`data/hotel_metadata.json` and restart the service (it is read once at
startup). `scripts/build_metadata.py` is the helper that produced the file.

### Public holidays

Public holidays are **not stored in the hotel metadata**. They are looked up at
run time in the Python [`holidays`](https://pypi.org/project/holidays/) package
(country `KH`, Cambodia) by `PublicHolidayCalendar`
([services/public_holidays.py](src/nf_hotel_api/services/public_holidays.py)).
The LLM prompt lists the holidays for the years the bookings' arrival dates
span, and the dataset generator uses them to shape demand.

[data/holidays.json](data/holidays.json) is a generated **export** of that
calendar (holiday name, start and end date, with the package version it came
from) for anyone who wants to read the holidays without running Python. The
application does not read it; the package stays the source of truth. Refresh it
after upgrading the package or when a new year starts:

```bash
.venv/Scripts/python scripts/update_holidays.py
```

By default it covers 2022 up to next year; use `--first-year` / `--last-year`
to change that. `tests/test_public_holidays.py` fails when the file no longer
matches the package, which is the signal to re-run the script.

### Nearby events

Looked up on the web; each entry carries its `source_url`. All venues are in
Phnom Penh, but the distance to Street 172 was **not measured**, so the
20 km radius is an assumption based on the venues being in the city.

| Event | Date | Venue |
|---|---|---|
| 40th and 41st ASEAN Summits | 10-13 Nov 2022 | Phnom Penh |
| 2023 SEA Games | 5-17 May 2023 | Morodok Techo Sports Complex, Olympic Sports Complex, Chroy Changvar Convention Centre |
| 12th ASEAN Para Games | 3-9 Jun 2023 | Morodok Techo National Stadium |
| Phnom Penh International Half Marathon | 11 Jun 2023, 16 Jun 2024, 15 Jun 2025 | Phnom Penh |
| Miss Grand Cambodia 2024 final | 12 Jul 2024 | Koh Pich Theater |
| CAMFOOD & CAMHOTEL 2024 | 6-8 Nov 2024 | Diamond Island Convention & Exhibition Center |
| Cambodia ASEAN Business Summit 2025 | 6 Mar 2025 | Sofitel Phnom Penh Phokeetra |
| 2025 AFC Challenge League final | 10 May 2025 | Phnom Penh |
| Mekong Forum 2025 | 30-31 Jul 2025 | Shangri-La Hotel Phnom Penh |
| CamboP&ELight 2025 | 6-9 Aug 2025 | Diamond Island Convention & Exhibition Center |
| Phnom Penh Design Festival 2025 | 31 Oct - 2 Nov 2025 | Factory Phnom Penh |

The list is not exhaustive (2022 and 2024 in particular have few entries).

## The dataset (`data/nf_hotel_bookings.csv`)

**The bookings are synthetic, not real reservations.** They are generated by
[scripts/generate_bookings.py](scripts/generate_bookings.py) (fixed seed, so the
file is reproducible) to fit this hotel:

- Arrivals 1 Jan 2022 - 31 Dec 2025, about 8,500 rows.
- The hotel has only 10 small and 10 large rooms. The simulation never sells
  more rooms of a type than exist on any night; requests for a sold-out night
  are turned away and do not appear in the file. `tests/test_dataset.py`
  checks this.
- Demand follows the calendar in the metadata: it is higher on Fridays and
  Saturdays and in the cool season, much higher during big events (SEA Games,
  ASEAN Summit) and the Water Festival, and lower during Khmer New Year and
  Pchum Ben, when people leave the capital. Average occupancy comes out around
  55-60 %, close to full during the biggest events.
- `prize_per_nigth` is the price paid: the standard price with a discount for
  Corporate/Groups/Offline TA bookings and a surcharge on peak days.
- About 2 % deliberately dirty rows (duplicates, impossible guest counts, blank
  meals) are added so `DataCleaningService` has real work to do.

All multipliers (holiday and event effects, price rules, guest mix) are
**modelling assumptions**, not measurements. They are constants at the top of
the script; change them and regenerate:

```bash
.venv/Scripts/python scripts/generate_bookings.py
```

(Close the CSV in Excel first, otherwise Windows blocks the write.) Replace the
file with real bookings when they are available; nothing else needs to change.

## Tests

```bash
.venv/Scripts/python -m pytest
```
