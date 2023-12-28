#!/usr/bin/env python3

import random
import osmnx as ox
import matplotlib.pyplot as plt

from common import *


# Turn on the local cache and console logging
ox.settings.log_console = False
ox.settings.use_cache = True
print(ox.__version__)


def get_bounds(place):
    gdf = ox.geocode_to_gdf(place)
    bounds = gdf.total_bounds
    return bounds


def main(args):
    place = args.place
    placename = place.split(',')[0].replace(" ", "").lower()

    # get the bounding box of a city from ox
    west, south, east, north = get_bounds(args.place)

    one_mile = lat_lon_dist(one_mile_lat, one_mile_lon(abs(north - south) / 2))

    north += one_mile.y
    south -= one_mile.y
    east += one_mile.x
    west -= one_mile.x

    north, south, east, west = scale(north, south, east, west, target_ratio=1.5)

    G = ox.graph_from_bbox(north, south, east, west, network_type="drive", retain_all=True)
    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)
    gdf_streets["color"] = street_color

    # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
    tags = {"natural": ["water", "bay", "strait"]}
    gdf_water = ox.features.features_from_bbox(north, south, east, west, tags=tags)
    gdf_water.crs = common_crs
    # Remove all points from the water data
    gdf_water = gdf_water[gdf_water.geometry.type.isin(['Polygon', 'MultiPolygon'])]    

    # schools, but just the buildings
    # tags = {"building": "school", "landuse": "cemetery"}
    # gdf_buildings = ox.features.features_from_place(place, tags=tags)
    # gdf_buildings.crs = common_crs

    try:
        tags = {"leisure": ["park", "garden"]}
        gdf_park = ox.features.features_from_bbox(north, south, east, west, tags=tags)
        # remove all elements of type node
        gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
        gdf_park.crs = common_crs
    except ox._errors.InsufficientResponseError:
        gdf_park = None

    try:
        tags = {'boundaries': "administrative", "admin_level": "10"}
        gdf_neighborhoods = ox.features.features_from_bbox(north, south, east, west, tags=tags)
        gdf_neighborhoods.crs = common_crs

        # remove all points 
        gdf_neighborhoods = gdf_neighborhoods[gdf_neighborhoods["geometry"].apply(lambda x: x.geom_type == "Polygon")]

    except ox._errors.InsufficientResponseError:
        gdf_neighborhoods = None

    # randomly assign one these colors to each neighborhood
    random.seed(args.seed)

    fig, ax = plt.subplots(figsize=(24, 36), dpi=300)
    ax.set_facecolor(bg_color)
    fig.tight_layout(pad=0)

    ax.set_xlim(west, east)
    ax.set_ylim(south, north)

    # print the x and y axis as a faint grid
    ax.grid(color=grid_color, linestyle="--", linewidth=0.5)

    # turn off axis labels
    ax.set_xticklabels([])
    ax.set_yticklabels([])

    # turn off the ticks on both axes
    ax.xaxis.set_ticks_position("none")
    ax.yaxis.set_ticks_position("none")

    ax.xaxis.set_major_locator(plt.MultipleLocator(one_mile.x))
    ax.yaxis.set_major_locator(plt.MultipleLocator(one_mile.y))

    # turn off the axis perimeter line
    for spine in ax.spines.values():
        spine.set_visible(False)

    # use a dashed line for the axis grid
    # gdf_neighborhoods.plot(ax=ax, facecolor=gdf_neighborhoods["color"], linestyle="-", ec="black", linewidth=2, alpha=1)
    gdf_streets.plot(ax=ax, ec=street_color, linewidth=1.5, alpha=0.5)

    gdf_water.plot(ax=ax, facecolor=water_blue, linewidth=1.5, alpha=1)

    if gdf_park is not None:
        gdf_park.plot(ax=ax, facecolor=park_green, alpha=0.6)

    if gdf_neighborhoods is not None:
        gdf_neighborhoods.plot(ax=ax, facecolor="none", linestyle="-", ec="#AAAAAA", linewidth=2, alpha=0.9, zorder=10)

        for idx, row in gdf_neighborhoods.iterrows():
            x = row["geometry"].centroid.x + neighborhood_offsets.get(row["name"], (0, 0))[0]
            y = row["geometry"].centroid.y + neighborhood_offsets.get(row["name"], (0, 0))[1]

            ax.annotate(
                text=munge(row["name"]),
                xy=(x, y),
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=6,
                color="#666666",
                weight="bold",
                name="Helvetica",
                # name="Phosphate",
                zorder=20,
            )

    plt.savefig(f"maps/{placename}_plain.pdf", dpi=300, pad_inches=0.0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("place")
    parser.add_argument("--seed", default=14, type=int, help="Random seed")
    args = parser.parse_args()

    main(args)
