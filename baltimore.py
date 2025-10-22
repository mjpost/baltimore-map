#!/usr/bin/env python3

"""
This creates a PDF plot of the city of Baltimore, including its unlabeled
streets and neighborhoods.
It was used as the base of my Baltimore City Neighborhoods poster, which
I manually post-edited with a title, legend, and other information.

© 2023–2025 Matt Post
"""

import hashlib
from pathlib import Path
import random
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import logging
import yaml
import numpy as np

from matplotlib import patheffects as pe
from matplotlib.collections import LineCollection

from common import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("baltimore-map")
logger.setLevel(logging.INFO)

# Turn on the local cache and console logging
ox.settings.log_console = False
ox.settings.use_cache = True

def init_baltimore(color_list=["gray"], color_method="random", cfg={}):
    # The neighborhoods data can be retrieved from Open Street Map.
    # However, for Baltimore at least, this data is incomplete. Instead, we
    # load the data from a geojson file provided by the City of Baltimore.
    # For other cities, you'd want to query OSM. However, note that many
    # cities do not have neighborhood boundaries (admin level 10) in OSM.
    # tags = {'boundaries': "administrative", "admin_level": "10"}
    # gdf_neighborhoods = ox.features.features_from_place(place, tags=tags)
    gdf_neighborhoods = gpd.read_file("data/Baltimore.geojson")
    gdf_neighborhoods.crs = common_crs

    if color_method == "random":
        logger.info("Using random coloring for neighborhoods")

        random.seed(14)
        gdf_neighborhoods["color"] = gdf_neighborhoods.apply(lambda x: random.choice(color_list), axis=1)

    elif color_method == "constrained":
        adj_map = {i: set() for i in gdf_neighborhoods.index}
        for i, geom_i in gdf_neighborhoods.geometry.items():
            for j, geom_j in gdf_neighborhoods.geometry.items():
                if i != j and geom_i.intersects(geom_j):
                    adj_map[i].add(j)

        assigned_colors = {}
        for idx in gdf_neighborhoods.index:
            neighbor_colors = {assigned_colors[j] for j in adj_map[idx] if j in assigned_colors}
            available_colors = [c for c in color_list if c not in neighbor_colors]
            if not available_colors:
                # fallback if palette too small
                available_colors = color_list
            assigned_colors[idx] = random.choice(available_colors)

        gdf_neighborhoods["color"] = gdf_neighborhoods.index.map(assigned_colors.get)

    elif color_method == "greedy":
        logger.info("Using greedy coloring for neighborhoods")

        from networkx.algorithms.coloring import greedy_color

        G = build_adjacency_graph(gdf_neighborhoods)

        # Step 2: Apply graph coloring
        color_map = greedy_color(G, strategy='largest_first')  # or 'random_sequential', etc.

        # Step 3: Assign to GeoDataFrame
        gdf_neighborhoods['color'] = gdf_neighborhoods.index.map(lambda idx: color_list[color_map[idx] % len(color_list)])

    else:
        # just assign white to all neighborhoods
        logger.info("Using default coloring for neighborhoods")
        gdf_neighborhoods["color"] = cfg["neighborhoods"]["bgcolor"]

    # adjust the lat/long boundaries to get to a 1.5 height:width ratio
    west, south, east, north = gdf_neighborhoods.total_bounds
    # print the number of rows in gdf_neighborhoods
    logger.info(f"Number of neighborhoods: {len(gdf_neighborhoods)}")
    logger.info(f"City boundaries: {gdf_neighborhoods.total_bounds}")

    one_mile = lat_lon_dist(one_mile_lat, one_mile_lon(abs(north - south) / 2))

    west -= one_mile.x * cfg["general"]["margin"].get("west", 0)
    east += one_mile.x * cfg["general"]["margin"].get("east", 0)

    # scale() distributes the compensation evenly. For Baltimore, we want more on the bottom.
    # west, south, east, north = scale(west, south, east, north, target_ratio=1.5)

    # The print ratio is 1.5, so we need to make sure to select the right amount of vertical content. This requires finding the longitude distance at Baltimore's latitude.
    required_height = 1.5 * lon_distance(west, east, (north + south) / 2)
    current_height = north - south
    extra_height = required_height - current_height

    # Keep a bit more space at the bottom, an aesthetic choice
    pct_north = cfg["general"]["margin"].get("north", 0.3)
    north += extra_height * pct_north
    south -= extra_height * (1 - pct_north)

    logger.info(f"Adjusted boundaries: {[west, south, east, north]}")

    # Using a network type of "all_private" will get all the alleys etc
    # It also makes the boundaries with water a lot fuzzier since they
    # are overlaid.
    # network_type=drive is more limited
    G = cache_graph(
        west,
        south,
        east,
        north,
        cfg["general"]["network"],
        retain_all=True,
    )

    # Convert to a GeoDataFrame and project to a common CRS
    # TODO: Is it possible to collapse these into a single layer?
    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)

    return gdf_neighborhoods, gdf_streets, west, south, east, north


def cache_graph(west, south, east, north, network_type, retain_all=True):
    key = f"{west:.5f}_{south:.5f}_{east:.5f}_{north:.5f}_{network_type}_ra{int(retain_all)}"
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    cache_dir = Path("graph_cache")
    cache_dir.mkdir(exist_ok=True)
    path = cache_dir / f"graph_{h}.graphml"
    if path.exists():
        logger.info(f"Loading cached graph from {path}")
        return ox.load_graphml(path)
    logger.info(f"Generating new graph and saving to {path}")
    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type=network_type, retain_all=retain_all)
    ox.save_graphml(G, path)
    return G

# Step 1: Build adjacency graph
def build_adjacency_graph(gdf):
    G = nx.Graph()
    for idx, geom in gdf.geometry.items():
        G.add_node(idx)
        
    for i, geom_i in gdf.geometry.items():
        for j, geom_j in gdf.geometry.items():
            if i >= j:
                continue
            if geom_i.intersects(geom_j):  # or .intersects() if you want more aggressive adjacency
                G.add_edge(i, j)
    return G


def draw_nautical_lines(ax, bounds, spacing=0.01, angle=45, color='white', alpha=0.2, linewidth=0.5):
    """Draws diagonal lines at a given angle over specified bounds (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = bounds

    # Convert angle to radians and get direction vector
    angle_rad = np.deg2rad(angle)
    dx = spacing / np.cos(angle_rad)
    dy = spacing / np.sin(angle_rad)

    lines = []
    x = xmin - (ymax - ymin)
    while x < xmax + (ymax - ymin):
        start = (x, ymin)
        end = (x + (ymax - ymin) / np.tan(angle_rad), ymax)
        lines.append([start, end])
        x += dx

    line_collection = LineCollection(lines, colors=color, linewidths=linewidth, alpha=alpha)
    ax.add_collection(line_collection)


def main(args):
    place = "Baltimore, MD"
    placename = "baltimore"

    # load colors from the yaml file
    with open(args.data_file, "r") as f:
        cfg = yaml.safe_load(f)

    # Build z-order database. This can either be read from
    # a top-level "zorders" section, or pulled from each section.
    zorders = cfg.get("zorders", {})
    # Now go through all the top-level sections, and grab
    # a z-order if present
    for section in cfg.keys():
        if section == "zorders":
            continue
        if isinstance(cfg[section], dict) and (zorder := cfg[section].get("zorder")):
            zorders[section] = zorder
    # Now update the cfg sections with the zorders
    cfg["zorders"] = zorders

    # Adapt to new object-based configuration schema
    color_method = cfg.get("color_method", "none")

    # Neighborhood palette
    color_list = list(cfg.get("neighborhoods", {}).get("palette", {}).values())
    # Ensure required config sections exist
    for section in [
        "streets",
        "grid",
        "neighborhoods",
        "water",
        "park",
        "cemetery",
        "districts",
        "bike",
        "ghost_bike",
        "text",
    ]:
        cfg.setdefault(section, {})

    gdf_neighborhoods, gdf_streets, west, south, east, north = init_baltimore(color_list=color_list, color_method=color_method, cfg=cfg)

    # cemeteries!
    tags = {"landuse": "cemetery"}
    gdf_cemetery = ox.features.features_from_place(place, tags=tags)
    gdf_cemetery.crs = common_crs

    # # ...and drinking fountains
    # tags = {"amenity": "drinking_water"}
    # gdf_drinking_fountains = ox.features.features_from_place(place, tags=tags)
    # gdf_drinking_fountains.crs = common_crs

    width = cfg["general"].get("width", 24)
    height = cfg["general"].get("height", 36)
    dpi = cfg["general"].get("dpi", 300)

    # Setup the figure and plot
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    ax.set_facecolor(cfg["general"].get("bgcolor", "white"))
    fig.tight_layout(pad=0)

    ax.set_xlim(west, east)
    ax.set_ylim(south, north)

    # print the x and y axis as a faint grid
    if cfg["grid"]:
        ax.grid(
            color=cfg["grid"]["color"],
            linestyle=cfg["grid"]["linestyle"],
            linewidth=cfg["grid"]["line_width"],
            alpha=cfg["grid"]["alpha"]
        )

    # turn off axis labels
    ax.set_xticklabels([])
    ax.set_yticklabels([])

    # turn off the ticks on both axes
    ax.xaxis.set_ticks_position("none")
    ax.yaxis.set_ticks_position("none")
    
    # draw gridlines every one mile
    one_mile = lat_lon_dist(one_mile_lat, one_mile_lon(abs(north - south) / 2))
    ax.xaxis.set_major_locator(plt.MultipleLocator(one_mile.x))
    ax.yaxis.set_major_locator(plt.MultipleLocator(one_mile.y))

    # turn off the axis perimeter line
    for spine in ax.spines.values():
        spine.set_visible(False)

    # plot the streets, neighborhoods, water, parks, and cemeteries
    # Clip streets to the combined neighborhoods geometry before plotting
    city_polygon = gdf_neighborhoods.union_all()


    if cfg["streets"]:
        if cfg["streets"].get("clip_to_city", False):
            gdf_streets = gpd.clip(gdf_streets, city_polygon)

        gdf_streets.plot(
            ax=ax,
            ec=cfg["streets"]["color"],
            linewidth=cfg["streets"]["line_width"],
            alpha=cfg["streets"]["alpha"],
            zorder=cfg["zorders"]["streets"]
        )

    if cfg["districts"]:
        district_file = cfg["districts"].get("file", "data/Baltimore_City_Council_Districts.geojson")
        gdf_districts = gpd.read_file(district_file)
        gdf_districts.crs = common_crs

        gdf_districts.plot(
            ax=ax,
            facecolor="none",
            ec=cfg["districts"]["boundary_color"],
            linewidth=cfg["districts"]["boundary_line_width"],
            linestyle=cfg["districts"]["linestyle"],
            alpha=cfg["districts"]["alpha"],
            zorder=cfg["zorders"]["districts"],
        )

    # cycleways get plotted quite thick and blurry, with the darker lane on top of them
    # tags = {"network": "lcn", "route": "bicycle"}
    if cfg["bike"]:
        # tags = {"highway": "cycleway", "route": "bicycle"}
        tags = {
            'highway': 'cycleway',
            # "route": "bicycle",
            # 'cycleway:right': True,
            # 'cycleway:left': True,
            # 'cycleway:both': True,
            'bicycle': ['designated'],  # used to have 'yes' here too, but that's too much
        }
        gdf_cycleways = ox.features.features_from_bbox(bbox=(west, south, east, north), tags=tags)
        # remove points
        gdf_cycleways = gdf_cycleways[gdf_cycleways.geometry.type.isin(['LineString', 'MultiLineString'])]
        gdf_cycleways.crs = common_crs

        tags = {
            'highway': 'cycleway',
            "route": "bicycle",
            'cycleway:right': True,
            'cycleway:left': True,
            'cycleway:both': True,
            'bicycle': ['designated'],  # used to have 'yes' here too, but that's too much
        }
        gdf_bikeable = ox.features.features_from_bbox(bbox=(west, south, east, north), tags=tags)
        # remove points
        gdf_bikeable = gdf_bikeable[gdf_bikeable.geometry.type.isin(['LineString', 'MultiLineString'])]
        gdf_bikeable.crs = common_crs    

        if cfg["bike"]["clip"]:
            gdf_cycleways = gpd.clip(gdf_cycleways, city_polygon)
            gdf_bikeable = gpd.clip(gdf_bikeable, city_polygon)

        gdf_cycleways.plot(
            ax=ax,
            ec=cfg["bike"]["lane_color"],
            linewidth=cfg["bike"]["cycleway_line_width"],
            alpha=cfg["bike"]["cycleway_alpha"],
            zorder=cfg["zorders"]["bike"]
        )
        gdf_bikeable.plot(
            ax=ax,
            ec=cfg["bike"]["lane_color"],
            linewidth=cfg["bike"]["bike_lane_line_width"],
            alpha=cfg["bike"]["bike_lane_alpha"],
            linestyle="--",
            zorder=cfg["zorders"]["bike"] + 1
        )

    # draw_nautical_lines(ax, ax.get_xlim() + ax.get_ylim(), spacing=0.01, angle=45)
    if cfg["water"]:
        # TODO: get all water inside city boundaries, but just major waterways outside the city

        # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
        tags = {"natural": "water"}
        gdf_water = ox.features.features_from_bbox(bbox=(west, south, east, north), tags=tags)
        gdf_water.crs = common_crs
        # Remove all points from the water data
        gdf_water = gdf_water[gdf_water.geometry.type.isin(['Polygon', 'MultiPolygon'])]

        gdf_water.plot(
            ax=ax,
            facecolor=cfg["water"].get("color", "#5891ac"),
            alpha=cfg["water"].get("alpha", 1),
            zorder=cfg["zorders"].get("water", 10),
        )

    if cfg["park"]:
        tags = {"leisure": ["park", "garden"]}
        gdf_park = ox.features.features_from_place(place, tags=tags)
        # remove all elements of type node
        gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
        gdf_park.crs = common_crs

        gdf_park.plot(
            ax=ax,
            facecolor=cfg["park"]["color"],
            alpha=cfg["park"]["alpha"],
            zorder=cfg["zorders"]["park"],
        )

    if cfg["cemetery"]:
        gdf_cemetery.plot(
            ax=ax,
            facecolor=cfg["cemetery"]["color"],
            ec="#444444",
            linewidth=cfg["cemetery"]["line_width"],
            alpha=cfg["cemetery"]["alpha"],
            zorder=cfg["zorders"]["cemetery"],
        )

    # Baltimore is also somewhat distinct in having good annotations for ghost bikes...
    # tags = {"memorial": "ghost_bike"}
    if cfg["ghost_bike"]:
        gdf_ghost = ox.features_from_bbox(bbox=(west, south, east, north), tags=tags)
        gdf_ghost.crs = common_crs
        gdf_ghost.plot(
            ax=ax,
            marker="X",
            markersize=cfg["ghost_bike"]["marker_size"],
            color=cfg["ghost_bike"]["color"],
            alpha=cfg["ghost_bike"]["alpha"],
        )

    # gdf_neighborhoods.plot(ax=ax, facecolor='none', ec=hood_line_color, linewidth=hood_line_width, alpha=0.9, zorder=10)

    # Transparent (no fill) neighborhoods: only draw boundaries
    gdf_neighborhoods.plot(
        ax=ax,
        facecolor="none",  # or facecolor="none"
        ec=cfg["neighborhoods"]["boundary_color"],
        linewidth=cfg["neighborhoods"]["boundary_line_width"],
        alpha=cfg["neighborhoods"]["alpha"],  # now applies to edges only
        zorder=cfg["zorders"]["neighborhoods"],
    )

    # Plot just the city boundary
    # city = ox.geocode_to_gdf("Baltimore, MD")
    # city_proj = ox.project_gdf(city, to_crs=common_crs)
    # city_proj.plot(ax=ax, facecolor="none", ec=hood_line_color, linewidth=hood_line_width, alpha=0.9, zorder=10)

    # assign IDs to neighborhood names in alphabetical order
    def maybe_rename(name):
        rename_map = {
            "Baltimore Peninsula": "Port Covington (Baltimore Peninsula)",
            "Washington Village/Pigtown": "Pigtown (Washington Village)",
            # https://www.reddit.com/r/baltimore/comments/1mnjd08/comment/n87fbwd/
            "Charles North": "Station North (Charles North)",
        }
        return rename_map.get(name, name)

    names = [maybe_rename(name) for name in gdf_neighborhoods["Name"]]
    ids = { name: str(i) for i, name in enumerate(sorted(names), 1) }

    # Print the name of each neighborhood on the map.
    # These print at the center of the neighborhood polygon, which isn't always
    # correct. So we use a dictionary of offsets to shift them around a bit.
    text_display = cfg["text"].get("display", "none")
    if text_display != "none":
        for _, row in gdf_neighborhoods.iterrows():
            dx, dy = (0, 0)  # neighborhood_offsets.get(row["Name"], (0, 0))
            centroid = row.geometry.centroid
            x = centroid.x + dx
            y = centroid.y + dy

            name = maybe_rename(row["Name"])
            idx = ids[name]

            print(f"Neighborhood {idx}: {name}")
            text_color = cfg["text"]["color"]
            text_bg = cfg["text"]["bgcolor"]
            font_size = cfg["text"]["size"]

            text = name if text_display == "text" else idx

            ax.annotate(
                text=text,
                xy=(x, y),
                ha="center",
                va="center",
                fontsize=font_size,
                color=text_color,
                weight=800,
                name="Georgia",
                zorder=cfg["zorders"]["text"],
                path_effects=[
                    pe.withStroke(linewidth=5, foreground=text_bg),
                ],
            )

    pdf_file = f"{placename}-{args.data_file.replace('.yaml', '')}.pdf"
    image_file = pdf_file.replace(".pdf", ".png")
    print(f"Saving figure to {pdf_file} and {image_file}")
    fig.savefig(pdf_file, dpi=300, pad_inches=0.0)
    fig.savefig(image_file, dpi=300, pad_inches=0.0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", "-d", type=str, default="visit.yaml",)
    args = parser.parse_args()

    main(args)
