#!/usr/bin/env python3

"""
This creates a PDF plot of the city of Baltimore, including its unlabeled
streets and neighborhoods.
It was used as the base of my Baltimore City Neighborhoods poster, which
I manually post-edited with a title, legend, and other information.

© 2023 Matt Post
"""

import random
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import logging

from common import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Turn on the local cache and console logging
ox.settings.log_console = False
ox.settings.use_cache = True

def init_baltimore(tight=False, color_list=["gray"], color_method="random"):
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

    # adjust the lat/long boundaries to get to a 1.5 height:width ratio
    west, south, east, north = gdf_neighborhoods.total_bounds
    # print the number of rows in gdf_neighborhoods
    print(f"Number of neighborhoods: {len(gdf_neighborhoods)}")
    print("City boundaries:", gdf_neighborhoods.total_bounds)

    one_mile = lat_lon_dist(one_mile_lat, one_mile_lon(abs(north - south) / 2))

    if not tight:
        west -= one_mile.x
        east += one_mile.x

        # scale() distributes the compensation evenly. For Baltimore, we want more on the bottom.
        # west, south, east, north = scale(west, south, east, north, target_ratio=1.5)

        compensation = 1.5 * lon_distance(west, east, (north + south) / 2) - (north - south)
        # Keep a bit more space at the bottom, an aesthetic choice
        north += one_mile.y * 1.5
        south -= compensation - one_mile.y * 1.5

        print("Adjusted boundaries:", *map(lambda x: f"{x:.5f}", [west, south, east, north]))

    # Using a network type of "all_private" will get all the alleys etc
    # It also makes the boundaries with water a lot fuzzier since they
    # are overlaid.
    G = ox.graph_from_bbox((west, south, east, north), network_type="drive", retain_all=True)

    # Convert to a GeoDataFrame and project to a common CRS
    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)

    return gdf_neighborhoods, gdf_streets, west, south, east, north


import networkx as nx

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


import numpy as np
from matplotlib.collections import LineCollection

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


import yaml


def main(args):
    place = "Baltimore, MD"
    placename = "baltimore"

    # load colors from the yaml file
    with open(args.data_file, "r") as f:
        data = yaml.safe_load(f)

    colors = data["colors"]
    alphas = data["alphas"]
    zs = data["zorders"]
    sizes = data["sizes"]
    color_method = data.get("color_method", "random")

    color_list = list(colors["neighborhood"].values())

    gdf_neighborhoods, gdf_streets, west, south, east, north = init_baltimore(color_list=color_list, color_method=color_method)

    # tags = {"highway": "cycleway", "route": "bicycle"}
    tags = {
        'highway': 'cycleway',
        # "route": "bicycle",
        # 'cycleway:right': True,
        # 'cycleway:left': True,
        # 'cycleway:both': True,
        # 'bicycle': ['yes', 'designated']
        'bicycle': 'designated',
    }
    # tags = {"network": "lcn", "route": "bicycle"}
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
        'bicycle': ['yes', 'designated'],
    }
    gdf_bikeable = ox.features.features_from_bbox(bbox=(west, south, east, north), tags=tags)
    # remove points
    gdf_bikeable = gdf_bikeable[gdf_bikeable.geometry.type.isin(['LineString', 'MultiLineString'])]
    gdf_bikeable.crs = common_crs    

    # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
    tags = {"natural": "water"}
    gdf_water = ox.features.features_from_bbox(bbox=(west, south, east, north), tags=tags)
    gdf_water.crs = common_crs
    # Remove all points from the water data
    gdf_water = gdf_water[gdf_water.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    # cemeteries!
    tags = {"landuse": "cemetery"}
    gdf_cemetery = ox.features.features_from_place(place, tags=tags)
    gdf_cemetery.crs = common_crs

    tags = {"leisure": ["park", "garden"]}
    gdf_park = ox.features.features_from_place(place, tags=tags)
    # remove all elements of type node
    gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
    gdf_park.crs = common_crs

    # Baltimore is also somewhat distinct in having good annotations for ghost bikes...
    tags = {"memorial": "ghost_bike"}
    gdf_ghost = ox.features_from_bbox(bbox=(west, south, east, north), tags=tags)
    gdf_ghost.crs = common_crs

    # ...and drinking fountains
    tags = {"amenity": "drinking_water"}
    gdf_drinking_fountains = ox.features.features_from_place(place, tags=tags)
    gdf_drinking_fountains.crs = common_crs

    # Setup the figure and plot
    fig, ax = plt.subplots(figsize=(24, 36), dpi=300)
    ax.set_facecolor(colors["bg"])
    fig.tight_layout(pad=0)

    ax.set_xlim(west, east)
    ax.set_ylim(south, north)

    # print the x and y axis as a faint grid
    ax.grid(color=colors["grid"], linestyle="--", linewidth=0.5)

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
    gdf_streets.plot(ax=ax, ec=colors["street"], linewidth=sizes["street_line_width"], alpha=alphas["street"], zorder=zs["streets"])

    # cycleways get plotted quite thick and blurry, with the darker lane on top of them
    gdf_cycleways.plot(ax=ax, ec=colors["bike_lane"], linewidth=sizes["cycleway_line_width"], alpha=alphas["cycleway"])
    gdf_bikeable.plot(ax=ax, ec=colors["bike_lane"], linewidth=sizes["bike_lane_line_width"], alpha=alphas["bike_lane"], linestyle="--")

    # draw_nautical_lines(ax, ax.get_xlim() + ax.get_ylim(), spacing=0.01, angle=45)
    gdf_water.plot(ax=ax, facecolor=colors["water"], alpha=alphas["water"], zorder=zs["water"])

    gdf_park.plot(ax=ax, facecolor=colors["park"], alpha=alphas["park"], zorder=zs["park"])
    gdf_cemetery.plot(ax=ax, facecolor=colors["cemetery"], ec="#444444", linewidth=1, alpha=alphas["cemetery"])
    gdf_ghost.plot(ax=ax, marker="X", markersize=50, color=colors["ghost_bike"], alpha=alphas["ghost_bike"])

    # gdf_neighborhoods.plot(ax=ax, facecolor='none', ec=hood_line_color, linewidth=hood_line_width, alpha=0.9, zorder=10)

    gdf_neighborhoods.plot(ax=ax, facecolor=gdf_neighborhoods["color"], ec=colors["hood_line"], linewidth=sizes["hood_line_width"], alpha=alphas["neighborhood"], zorder=zs["neighborhoods"])

    # Plot just the city boundary
    # city = ox.geocode_to_gdf("Baltimore, MD")
    # city_proj = ox.project_gdf(city, to_crs=common_crs)
    # city_proj.plot(ax=ax, facecolor="none", ec=hood_line_color, linewidth=hood_line_width, alpha=0.9, zorder=10)

    # Print the name of each neighborhood on the map.
    # These print at the center of the neighborhood polygon, which isn't always
    # correct. So we use a dictionary of offsets to shift them around a bit.
    for idx, row in gdf_neighborhoods.iterrows():
        x = row["geometry"].centroid.x + neighborhood_offsets.get(row["Name"], (0, 0))[0]
        y = row["geometry"].centroid.y + neighborhood_offsets.get(row["Name"], (0, 0))[1]

        ax.annotate(
            text=munge(row["Name"]).upper(),
            xy=(x, y),
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=6,
            color=colors["text"],
            # color="#dddddd",
            weight=800,
            # name="Georgia",
            name="Avenir Next",
            # name="Rockwell",
            # name="Copperplate",  # no, too much
            # name="Phosphate",
            zorder=zs["text"],
        )

    fig.savefig(f"{placename}.pdf", dpi=300, pad_inches=0.0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", "-d", type=str, default="visit.yaml",)
    args = parser.parse_args()

    main(args)
