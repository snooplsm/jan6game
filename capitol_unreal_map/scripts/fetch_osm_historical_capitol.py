#!/usr/bin/env python3
"""Fetch a public historical OSM extract for the Capitol map package."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_DATE_UTC = "2021-01-06T17:00:00Z"
DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
BBOX_LONLAT = [-77.01770688017783, 38.882303355012574, -76.99693276775105, 38.89802380057492]


def default_output_for_date(target_date_utc: str) -> Path:
    date_label = target_date_utc.split("T", 1)[0]
    return ROOT / "source_data" / f"capitol_osm_overpass_{date_label}.json"


def build_query(target_date_utc: str) -> str:
    west, south, east, north = BBOX_LONLAT
    bbox = f"{south},{west},{north},{east}"
    return f"""
[out:json][timeout:180][date:"{target_date_utc}"];
(
  node({bbox});
  way({bbox});
  relation({bbox});
);
out body;
>;
out skel qt;
""".strip()


def fetch_overpass(endpoint: str, query: str) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=query.encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "jan6game-public-capitol-map-builder/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a public historical OpenStreetMap extract for the Capitol area. "
            "The default target is noon Eastern on Jan 6, 2021."
        )
    )
    parser.add_argument(
        "--date",
        default=DEFAULT_TARGET_DATE_UTC,
        help="Historical OSM snapshot time in UTC, e.g. 2021-01-06T17:00:00Z or 2020-12-31T23:59:59Z.",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Overpass API interpreter endpoint.")
    parser.add_argument("--output", type=Path, help="Output JSON path. Defaults to source_data/capitol_osm_overpass_<date>.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or default_output_for_date(args.date)
    if not output.is_absolute():
        output = ROOT / output
    query = build_query(args.date)
    payload = fetch_overpass(args.endpoint, query)
    payload["source_request"] = {
        "target_map_era": "Jan 6, 2021 / late-2020 public map state",
        "target_osm_date_utc": args.date,
        "endpoint": args.endpoint,
        "bbox_lonlat": BBOX_LONLAT,
        "bbox_order_for_overpass": "south,west,north,east",
        "retrieved_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "overpass_ql": query,
        "license_note": "OpenStreetMap data is available under the Open Database License (ODbL).",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"elements: {len(payload.get('elements', []))}")
    print(f"target_osm_date_utc: {args.date}")
    print(f"timestamp_osm_base: {payload.get('osm3s', {}).get('timestamp_osm_base')}")


if __name__ == "__main__":
    main()
