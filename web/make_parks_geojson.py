#!/usr/bin/env python3
"""Convert baltimore_parks.csv (WKT geometry) to GeoJSON."""

import csv
import json
import re
import sys
from pathlib import Path


def parse_wkt_polygon(wkt: str):
    """Parse a WKT POLYGON string into GeoJSON coordinates."""
    # Match POLYGON ((...)) or MULTIPOLYGON (((...)))
    multi = wkt.strip().startswith("MULTIPOLYGON")
    if multi:
        # MULTIPOLYGON (((x y, ...)), ((x y, ...)))
        rings_str = wkt.replace("MULTIPOLYGON", "").strip()
        # Split on ")),((" to get individual polygons
        polygons = []
        # Remove outer parens
        rings_str = rings_str.strip("()")
        parts = re.split(r"\)\s*,\s*\(", rings_str)
        for part in parts:
            part = part.strip("()")
            ring = [
                [float(c) for c in coord.strip().split()]
                for coord in part.split(",")
            ]
            polygons.append([ring])
        return {"type": "MultiPolygon", "coordinates": polygons}
    else:
        # POLYGON ((x y, x y, ...))
        # Strip "POLYGON" and outer parens, then handle inner ring parens
        body = wkt.replace("POLYGON", "").strip()
        # Remove outermost parens: "(( ... ))" -> "( ... )"
        body = body.strip("()")
        # Split by inner rings (separated by "),(")
        ring_strs = re.split(r"\)\s*,\s*\(", body)
        rings = []
        for rs in ring_strs:
            rs = rs.strip("()")
            ring = [
                [float(c) for c in coord.strip().split()]
                for coord in rs.split(",")
            ]
            rings.append(ring)
        return {"type": "Polygon", "coordinates": rings}


def main():
    csv_path = Path(__file__).resolve().parent.parent / "baltimore_parks.csv"
    out_path = Path(__file__).resolve().parent.parent / "data" / "baltimore_parks.geojson"

    features = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wkt = row.get("geometry", "")
            if not wkt or "POLYGON" not in wkt.upper():
                continue
            geometry = parse_wkt_polygon(wkt)
            props = {
                "name": row.get("name", ""),
                "osmid": row.get("osmid", ""),
                "leisure": row.get("leisure", ""),
            }
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": geometry,
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    print(f"Wrote {len(features)} park features to {out_path}")


if __name__ == "__main__":
    main()
