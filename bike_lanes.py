#!/usr/bin/env python3

"""
This creates a PDF plot of the city of Baltimore, including its unlabeled
streets and neighborhoods.
It was used as the base of my Baltimore City Neighborhoods poster, which
I manually post-edited with a title, legend, and other information.

© 2023 Matt Post
"""

import math
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt

from common import *


# Turn on the local cache and console logging
ox.settings.log_console = True
ox.settings.use_cache = True


def main(args):
    place = "Baltimore, MD"
    placename = place.split(',')[0].replace(" ", "").lower()

    # for the north/south adjustments, we need to take into account the
    # curvature of the earth. Here we find how much we need to add to the Y
    # access, using the mid-latitude point as an approximation.
    # return the distance between two longitude coordinates at a given latitude
    def lon_distance(lon1, lon2, lat):
        return (lon2 - lon1) * math.cos(lat * math.pi / 180)

    print(ox.settings.default_crs)

    city = ox.geocode_to_gdf(place)
    # city = ox.project_gdf(city)
    print("IS PROJECTED city?", city.crs)
    # city_proj = ox.project_gdf(city)

    # Using a network type of "all_private" will get all the alleys etc
    # It also makes the boundaries with water a lot fuzzier since they
    # are overlaid.
    G = ox.graph_from_place(place, network_type="drive", retain_all=True)

    # Convert to a GeoDataFrame and project to a common CRS
    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)
    print("IS PROJECTED streets?", gdf_streets.crs.is_projected)


    # get the bounds of the city
    west, south, east, north = gdf_streets.total_bounds

    tags = {"highway": "cycleway", "route": "bicycle"}
    # tags = {"network": "lcn", "route": "bicycle"}
    gdf_bikepaths = ox.features.features_from_bbox(north, south, east, west, tags=tags)
    gdf_bikepaths.crs = common_crs

    # Baltimore is also somewhat distinct in having good annotations for ghost bikes...
    tags = {"memorial": "ghost_bike"}
    gdf_ghost = ox.features_from_bbox(north, south, east, west, tags=tags)
    gdf_ghost.crs = common_crs

    # Setup the figure and plot
    fig, ax = plt.subplots(figsize=(5, 6), dpi=300)
    fig.tight_layout(pad=0)

    # ax.set_xlim(west, east)
    # ax.set_ylim(south, north)

    # print the x and y axis as a faint grid
    # ax.grid(color=grid_color, linestyle="--", linewidth=0.5)

    # turn off axis labels
    ax.set_xticklabels([])
    ax.set_yticklabels([])

    # turn off the ticks on both axes
    ax.xaxis.set_ticks_position("none")
    ax.yaxis.set_ticks_position("none")
    
    # draw gridlines every one mile
    ax.xaxis.set_major_locator(plt.MultipleLocator(one_mile.x))
    ax.yaxis.set_major_locator(plt.MultipleLocator(one_mile.y))

    # turn off the axis perimeter line
    for spine in ax.spines.values():
        spine.set_visible(False)

    # plot the streets, neighborhoods, water, parks, and cemeteries
    city.plot(ax=ax, fc="white", ec="black", linewidth=1, alpha=1)
    gdf_streets.plot(ax=ax, fc="none", ec="#666666", linewidth=1, alpha=0.5)
    gdf_bikepaths.plot(ax=ax, fc="none", ec="orange", linewidth=3, alpha=0.3)
    gdf_bikepaths.plot(ax=ax, fc="none", ec="orange", linewidth=0.5, alpha=1)
    # gdf_ghost.plot(ax=ax, marker="X", markersize=50, color=ghost_color, alpha=1)

    fig.savefig(f"{placename}.pdf", dpi=300, pad_inches=1.0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    main(args)
