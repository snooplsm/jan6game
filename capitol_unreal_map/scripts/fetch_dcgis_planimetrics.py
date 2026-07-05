#!/usr/bin/env python3
"""Fetch public DCGIS planimetrics used by the Capitol map generator."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ELEVATION_OUTPUT = ROOT / "source_data" / "dc_planimetrics_1999_capitol_elevation_points.json"
TRAFFIC_SIGN_OUTPUT = ROOT / "source_data" / "dc_planimetrics_1999_capitol_traffic_signs.json"
SERVICE_URL = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Planimetrics_1999/MapServer"
BBOX_LONLAT = [-77.01770688017783, 38.882303355012574, -76.99693276775105, 38.89802380057492]
ELEVATION_LAYERS = {
    "rooftop_elevations_1999": 4,
    "ground_elevation_points_1999": 6,
}
TRAFFIC_SIGN_LAYERS = {
    "other_traffic_signs_1999": {
        "id": 3,
        "out_fields": "OBJECTID,TRF,TRF_ID,TRF_CODE,DXF_LAYER,DESC_",
    },
    "overhead_traffic_signs_1999": {
        "id": 12,
        "out_fields": "OBJECTID,OTS,OTS_ID,OTS_CODE,DXF_LAYER,DESC_",
    },
}


def fetch_layer(layer_id: int, out_fields: str) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "f": "json",
            "where": "1=1",
            "outFields": out_fields,
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


def base_payload() -> dict[str, Any]:
    return {
        "service_url": SERVICE_URL,
        "bbox_lonlat": BBOX_LONLAT,
        "retrieved_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "license_note": "Public DC GIS planimetrics data accessed through the DCGIS ArcGIS REST service.",
    }


def main() -> None:
    ELEVATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    elevation_payload = {
        **base_payload(),
        "layers": {
            name: fetch_layer(layer_id, "OBJECTID,ELEVATION,DESC_,SUBTYPE")
            for name, layer_id in ELEVATION_LAYERS.items()
        },
    }
    traffic_sign_payload = {
        **base_payload(),
        "layers": {
            name: fetch_layer(int(spec["id"]), str(spec["out_fields"]))
            for name, spec in TRAFFIC_SIGN_LAYERS.items()
        },
    }

    ELEVATION_OUTPUT.write_text(json.dumps(elevation_payload, indent=2, sort_keys=True), encoding="utf-8")
    TRAFFIC_SIGN_OUTPUT.write_text(json.dumps(traffic_sign_payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote {ELEVATION_OUTPUT}")
    for name, layer in elevation_payload["layers"].items():
        print(f"{name}: {layer['feature_count']} features")
    print(f"Wrote {TRAFFIC_SIGN_OUTPUT}")
    for name, layer in traffic_sign_payload["layers"].items():
        print(f"{name}: {layer['feature_count']} features")


if __name__ == "__main__":
    main()
