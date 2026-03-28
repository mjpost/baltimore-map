"""Optimize GeoJSON files for web: strip properties, simplify geometry, truncate coords."""

import json
from pathlib import Path
from shapely.geometry import shape, mapping

DATA = Path(__file__).parent.parent / "data"
WEB = Path(__file__).parent

PRECISION = 5  # ~1.1 meter accuracy

def truncate_coords(coords, precision):
    """Recursively truncate coordinate precision."""
    if isinstance(coords[0], (int, float)):
        return [round(c, precision) for c in coords[:2]]  # also drops Z
    return [truncate_coords(c, precision) for c in coords]

def simplify_feature(feature, tolerance, keep_props):
    """Simplify geometry and strip properties."""
    geom = shape(feature["geometry"])
    if tolerance > 0:
        geom = geom.simplify(tolerance, preserve_topology=True)
    simplified = mapping(geom)
    simplified["coordinates"] = truncate_coords(simplified["coordinates"], PRECISION)
    props = {k: feature["properties"][k] for k in keep_props if k in feature["properties"]}
    return {"type": "Feature", "properties": props, "geometry": simplified}

def process(input_name, output_name, keep_props, tolerance):
    with open(DATA / input_name) as f:
        data = json.load(f)
    features = [simplify_feature(feat, tolerance, keep_props) for feat in data["features"]]
    out = {"type": "FeatureCollection", "features": features}
    outpath = WEB / output_name
    with open(outpath, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    orig_size = (DATA / input_name).stat().st_size
    new_size = outpath.stat().st_size
    print(f"{input_name} ({orig_size/1024:.0f}K) -> {output_name} ({new_size/1024:.0f}K)  [{100*(1-new_size/orig_size):.0f}% smaller]")

# Baltimore neighborhoods: keep Name + demographics, simplify aggressively (tolerance ~0.0001 ≈ 11m)
process("Baltimore.geojson", "baltimore_neighborhoods.geojson",
        ["Name", "Population", "White", "Blk_AfAm", "AmInd_AkNa", "Asian",
         "NatHaw_Pac", "Other_Race", "TwoOrMore", "Hisp_Lat",
         "Housing", "Occupied", "Vacant"], 0.0001)

# Districts: keep AREA_NAME, moderate simplification
process("Baltimore_City_Council_Districts.geojson", "baltimore_districts.geojson", ["AREA_NAME"], 0.0001)

# Parks: keep name, light simplification
process("baltimore_parks.geojson", "baltimore_parks.geojson", ["name"], 0.00005)
