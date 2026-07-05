#!/usr/bin/env python3
"""Fetch public DCGIS elevation points used for surrounding-building heights."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "source_data" / "dc_planimetrics_1999_capitol_elevation_points.json"
SERVICE_URL = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Planimetrics_1999/MapServer"
BBOX_LONLAT = [-77.01770688017783, 38.882303355012574, -76.99693276775105, 38.89802380057492]
LAYERS = {
    "rooftop_elevations_1999": 4,
    "ground_elevation_points_1999": 6,
}


def fetch_layer(layer_id: int) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "f": "json",
            "where": "1=1",
            "outFields": "OBJECTID,ELEVATION,DESC_,SUBTYPE",
            "returnGeometry": "true",
            "outSR": "4326",
            "geometry": ",".join(str(value) for value in BBOX_LONLAT),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "resultOffset": offset,
            "resultRecordCount": 1000,
        }
        url = f"{SERVICE_URL}/{layer_id}/query?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
        batch = payload.get("features", [])
        features.extend(batch)
        if len(batch) < 1000:
            return {
                "layer_id": layer_id,
                "query_url": f"{SERVICE_URL}/{layer_id}/query",
                "feature_count": len(features),
                "features": features,
            }
        offset += len(batch)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "service_url": SERVICE_URL,
        "bbox_lonlat": BBOX_LONLAT,
        "retrieved_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "license_note": "Public DC GIS planimetrics data accessed through the DCGIS ArcGIS REST service.",
        "layers": {
            name: fetch_layer(layer_id)
            for name, layer_id in LAYERS.items()
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    for name, layer in payload["layers"].items():
        print(f"{name}: {layer['feature_count']} features")


if __name__ == "__main__":
    main()
