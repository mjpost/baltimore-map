#!/usr/bin/env python3

"""
This creates a PDF plot of the city of Baltimore, including its unlabeled
streets and neighborhoods.
It was used as the base of my Baltimore City Neighborhoods poster, which
I manually post-edited with a title, legend, and other information.

© 2023 Matt Post
"""

import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt

from common import *


# Turn on the local cache and console logging
ox.settings.log_console = True
ox.settings.use_cache = True
print(ox.__version__)


def main(args):
    place = "Baltimore, MD"
    placename = place.split(',')[0].replace(" ", "").lower()

    # Using a network type of "all_private" will get all the alleys etc
    # It also makes the boundaries with water a lot fuzzier since they
    # are overlaid.
    G = ox.graph_from_place(place, network_type="drive", retain_all=True)

    # Convert to a GeoDataFrame and project to a common CRS
    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)

    # Define a number of colors
    street_color = "#cccccc"
    cemetery_gray = "#666666"
    grid_color = "#cccccc"
    ghost_color = "#721613"
    water_blue = "#2c5c98"
    park_green = "#1a5b07"

    # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
    tags = {"natural": "water"}
    gdf_water = ox.features.features_from_place(place, tags=tags)
    # anything with a "natural" column value of "water" should be a nice sea blue
    gdf_water.loc[gdf_water["natural"] == "water", "color"] = water_blue
    gdf_water.crs = common_crs

    # cemeteries!
    tags = {"landuse": "cemetery"}
    gdf_cemetery = ox.features.features_from_place(place, tags=tags)
    gdf_cemetery.crs = common_crs

    tags = {"leisure": ["park", "garden"]}
    gdf_park = ox.features.features_from_place(place, tags=tags)
    # remove all elements of type node
    gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
    gdf_park.crs = common_crs

    # The neighborhoods data can be retrieved from Open Street Map.
    # However, for Baltimore at least, this data is incomplete. Instead, we
    # load the data from a geojson file provided by the City of Baltimore.
    # For other cities, you'd want to query OSM. However, note that many
    # cities do not have neighborhood boundaries (admin level 10) in OSM.
    # tags = {'boundaries': "administrative", "admin_level": "10"}
    # gdf_neighborhoods = ox.features.features_from_place(place, tags=tags)
    gdf_neighborhoods = gpd.read_file("data/Baltimore.geojson")
    gdf_neighborhoods.crs = common_crs

    # Baltimore is also somewhat distinct in having good annotations for ghost bikes...
    tags = {"memorial": "ghost_bike"}
    gdf_ghost = ox.features.features_from_place(place, tags=tags)
    gdf_ghost.crs = common_crs

    # ...and drinking fountains
    tags = {"amenity": "drinking_water"}
    gdf_drinking_fountains = ox.features.features_from_place(place, tags=tags)
    gdf_drinking_fountains.crs = common_crs

    # Setup the figure and plot
    fig, ax = plt.subplots(figsize=(24, 36), dpi=300)
    fig.tight_layout(pad=10)

    ax.set_xlim(gdf_neighborhoods.total_bounds[0] - one_km.x * 0.5, 
                gdf_neighborhoods.total_bounds[2] + one_km.x * 0.5)
    ax.set_ylim(gdf_neighborhoods.total_bounds[1] - one_km.y * 0.5, 
                gdf_neighborhoods.total_bounds[3] + one_km.y * 0.5)

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

    # plot the streets, neighborhoods, water, parks, and cemeteries
    gdf_streets.plot(ax=ax, ec=street_color, linewidth=1, alpha=0.5)
    gdf_neighborhoods.plot(ax=ax, facecolor="white", linestyle="-", ec="black", linewidth=2, alpha=1)
    gdf_water.plot(ax=ax, facecolor=water_blue, ec="black", linewidth=0, alpha=0.5)
    gdf_park.plot(ax=ax, facecolor=park_green, ec="black", linewidth=0, alpha=0.5)
    gdf_cemetery.plot(ax=ax, facecolor=cemetery_gray, linewidth=0, alpha=0.3)
    gdf_ghost.plot(ax=ax, marker="X", markersize=50, color=ghost_color, alpha=1)

    # Print the name of each neighborhood on the map.
    # These print at the center of the neighborhood polygon, which isn't always
    # correct. So we use a dictionary of offsets to shift them around a bit.
    for idx, row in gdf_neighborhoods.iterrows():
        x = row["geometry"].centroid.x + baltimore_offsets.get(row["Name"], (0, 0))[0]
        y = row["geometry"].centroid.y + baltimore_offsets.get(row["Name"], (0, 0))[1]

        ax.annotate(
            text=munge(row["Name"]),
            xy=(x, y),
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=6,
            color="black",
            weight=200,
            # name="Damascus",
            name="Avenir Next Condensed",
            # name="Phosphate",
        )

    fig.savefig(f"{placename}.pdf", dpi=300)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    main(args)
