#!/usr/bin/env python3

import random
import osmnx as ox
import matplotlib.pyplot as plt

from common import *


# Turn on the local cache and console logging
ox.settings.log_console = True
ox.settings.use_cache = True
print(ox.__version__)


def main(args):
    place = args.place
    placename = place.split(',')[0].replace(" ", "").lower()

    G = ox.graph_from_place(place, network_type="drive", retain_all=True)

    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)
    gdf_streets["color"] = street_color

    # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
    tags = {"natural": "water"}
    gdf_water = ox.features.features_from_place(place, tags=tags)
    gdf_water.loc[gdf_water["natural"] == "water", "color"] = water_blue
    gdf_water.crs = common_crs

    # schools, but just the buildings
    # tags = {"building": "school", "landuse": "cemetery"}
    # gdf_buildings = ox.features.features_from_place(place, tags=tags)
    # gdf_buildings.crs = common_crs

    try:
        tags = {"leisure": ["park", "garden"]}
        gdf_park = ox.features.features_from_place(place, tags=tags)
        # remove all elements of type node
        gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
        gdf_park.crs = common_crs
    except ox._errors.InsufficientResponseError:
        gdf_park = None

    try:
        tags = {'boundaries': "administrative", "admin_level": "10"}
        gdf_neighborhoods = ox.features.features_from_place(place, tags=tags)
        gdf_neighborhoods.crs = common_crs

        # remove all points 
        gdf_neighborhoods = gdf_neighborhoods[gdf_neighborhoods["geometry"].apply(lambda x: x.geom_type == "Polygon")]
    except ox._errors.InsufficientResponseError:
        gdf_neighborhoods = None

    # randomly assign one these colors to each neighborhood
    random.seed(args.seed)

    # the plot. You'll have to adjust these for the city you're doing
    fig, ax = plt.subplots(figsize=(24,36), dpi=300)

    ax.set_xlim(gdf_streets.total_bounds[0] - one_km.x,
                gdf_streets.total_bounds[2] + one_km.x)
    ax.set_ylim(gdf_streets.total_bounds[1] - one_km.y,
                gdf_streets.total_bounds[3] + one_km.y)

    # print the x and y axis as a faint grid
    ax.grid(color=grid_color, linestyle="--", linewidth=0.5)

    # put the axis labels to the top and to the right
    ax.xaxis.tick_top()
    ax.yaxis.tick_right()
    ax.tick_params(axis="both", direction="in", length=6, width=0.5, colors=grid_color)

    # use three decimal places for the axis tick labels
    ax.xaxis.set_major_formatter(plt.FormatStrFormatter("%.3f"))

    # draw gridlines every one mile
    ax.xaxis.set_major_locator(plt.MultipleLocator(one_mile.x))
    ax.yaxis.set_major_locator(plt.MultipleLocator(one_mile.y))

    # turn off the axis perimeter line
    for spine in ax.spines.values():
        spine.set_visible(False)

    # use a dashed line for the axis grid
    # gdf_neighborhoods.plot(ax=ax, facecolor=gdf_neighborhoods["color"], linestyle="-", ec="black", linewidth=2, alpha=1)
    gdf_streets.plot(ax=ax, ec=gdf_streets["color"], linewidth=1, alpha=0.5)

    if gdf_neighborhoods is not None:
        gdf_neighborhoods.plot(ax=ax, facecolor="white", linestyle="-", ec="black", linewidth=2, alpha=1)

    # gdf_water.plot(ax=ax, facecolor=water_blue, ec=water_blue, linewidth=1, alpha=1)
    gdf_water.plot(ax=ax, facecolor=water_blue, ec=water_blue, linewidth=1.5, alpha=0.5)

    if gdf_park is not None:
        gdf_park.plot(ax=ax, facecolor=park_green, ec="black", linewidth=0, alpha=0.5)

    # add_title(ax, gdf_streets, place=placename.upper())

    # Print the name of each neighborhood on the map
    if gdf_neighborhoods is not None:
        for idx, row in gdf_neighborhoods.iterrows():
            x = row["geometry"].centroid.x + baltimore_offsets.get(row["name"], (0, 0))[0]
            y = row["geometry"].centroid.y + baltimore_offsets.get(row["name"], (0, 0))[1]

            ax.annotate(
                text=munge(row["name"]),
                xy=(x, y),
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=7,
                color="black",
                weight="bold",
                name="Avenir Next Condensed",
                # name="Phosphate",
            )

    plt.savefig(f"maps/{placename}_plain.pdf", dpi=300)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("place")
    parser.add_argument("--seed", default=14, type=int, help="Random seed")
    args = parser.parse_args()

    main(args)
