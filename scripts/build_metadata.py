"""One-off helper that writes data/hotel_metadata.json.

Events were looked up on the web (source_url per event). Public holidays are
not stored here: they come from the `holidays` package at run time. Edit the
lists and re-run to change the file - or edit the JSON directly.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def e(name, start, end, venue, url):
    return {"name": name, "start_date": start, "end_date": end, "venue": venue, "source_url": url}


EVENTS = [
    e("40th and 41st ASEAN Summits and Related Summits", "2022-11-10", "2022-11-13",
      "Phnom Penh",
      "https://www.pmo.gov.sg/Newsroom/PM-Lee-Hsien-Loong-to-attend-the-40th-and-41st-ASEAN-Summits-and-Related-Summits-in-Cambodia-2022"),
    e("2023 SEA Games (Southeast Asian Games)", "2023-05-05", "2023-05-17",
      "Morodok Techo Sports Complex (Chroy Changvar), Olympic Sports Complex, Chroy Changvar Convention Centre",
      "https://en.wikipedia.org/wiki/2023_SEA_Games"),
    e("12th ASEAN Para Games", "2023-06-03", "2023-06-09",
      "Morodok Techo National Stadium",
      "https://en.wikipedia.org/wiki/2023_ASEAN_Para_Games"),
    e("Phnom Penh International Half Marathon", "2023-06-11", "2023-06-11",
      "Phnom Penh", "https://aims-worldrunning.org/races/10059.html"),
    e("Phnom Penh International Half Marathon", "2024-06-16", "2024-06-16",
      "Phnom Penh", "https://aims-worldrunning.org/races/10059.html"),
    e("Miss Grand Cambodia 2024 final", "2024-07-12", "2024-07-12",
      "Koh Pich Theater", "https://en.wikipedia.org/wiki/Miss_Grand_Cambodia_2024"),
    e("CAMFOOD & CAMHOTEL 2024 trade fair", "2024-11-06", "2024-11-08",
      "Diamond Island Convention & Exhibition Center",
      "https://www.tradeindia.com/tradeshows/venue/diamond-island-convention-exhibition-center-diecc/1173/"),
    e("Cambodia ASEAN Business Summit 2025", "2025-03-06", "2025-03-06",
      "Sofitel Phnom Penh Phokeetra",
      "https://cambodiainvestmentreview.com/2025/01/30/cambodia-asean-business-summit-2025-set-for-march-6-at-sofitel-phnom-penh/"),
    e("2025 AFC Challenge League final", "2025-05-10", "2025-05-10",
      "Phnom Penh", "https://en.wikipedia.org/wiki/2025_AFC_Challenge_League_final"),
    e("Phnom Penh International Half Marathon", "2025-06-15", "2025-06-15",
      "Phnom Penh", "https://aims-worldrunning.org/races/10059.html"),
    e("Mekong Forum 2025", "2025-07-30", "2025-07-31",
      "Shangri-La Hotel Phnom Penh", "https://mekonginstitute.org/mekong-forum-2025/"),
    e("CamboP&ELight 2025 trade fair", "2025-08-06", "2025-08-09",
      "Diamond Island Convention & Exhibition Center",
      "https://www.tradeindia.com/tradeshows/venue/diamond-island-convention-exhibition-center-diecc/1173/"),
    e("Phnom Penh Design Festival 2025", "2025-10-31", "2025-11-02",
      "Factory Phnom Penh", "https://ppua.edu.kh/events/ppdf/"),
]

METADATA = {
    "hotel": "NF Hotel",
    "address": {"street": "Street 172", "city": "Phnom Penh", "country": "Cambodia"},
    "currency": "USD",
    "room_types": {
        "A": {"size": "Small", "standard_price_per_night": 20, "room_count": 10},
        "B": {"size": "Large", "standard_price_per_night": 25, "room_count": 10},
    },
    "nearby_events": EVENTS,
}

if __name__ == "__main__":
    path = ROOT / "data" / "hotel_metadata.json"
    path.write_text(json.dumps(METADATA, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(EVENTS)} events)")
