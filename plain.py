#!/usr/bin/env python3

import random
import osmnx as ox
import gpxpy
import geopandas as gpd
import gpxpy.gpx
import pandas as pd

from common import *

import matplotlib.pyplot as plt


# Turn on the local cache and console logging
ox.settings.log_console = True
ox.settings.use_cache = True
print(ox.__version__)


def main(args):
    place = "Baltimore, MD"
    placename = place.split(',')[0].replace(" ", "").lower()

    bg_color = "white"  # "#e0e0e0"
    street_color = "#cccccc"
    cemetery_gray = "#666666"
    park_green = "#b2df8a"

    G = ox.graph_from_place(place, network_type="all_private")

    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=True, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)
    # assign every street a random color from city_colors
    # gdf_streets["color"] = gdf_streets.apply(lambda x: random.choice(list(city_colors.values())), axis=1)
    gdf_streets["color"] = street_color

    # get all parks from the OSM database
    # tags = {'natural': 'water', 'boundaries': "administrative", "admin_level": "9", 'leisure': ["garden"]}
    # tags = {'boundaries': "administrative", "admin_level": "10", "natural": "water"}  # , "leisure": ["park", "garden"]}

    # define a good RGB blue for water
    # water_blue = "#a6cee3"

    # grab a random color from city_colors and then remove it
    water_blue = city_colors["blue"]
    # city_colors.remove(water_blue)

    # park_green = random.choice(list(city_colors.values()))
    # city_colors.remove(park_green)

    # get all water, including lakes, rivers, and oceans, reservoirs, fountains, pools, and man-made lakes and ponds
    tags = {"natural": "water"}
    gdf_water = ox.features.features_from_place(place, tags=tags)
    # anything with a "natural" column value of "water" should be a nice sea blue
    gdf_water.loc[gdf_water["natural"] == "water", "color"] = water_blue
    gdf_water.crs = common_crs

    # schools, but just the buildings
    # tags = {"building": "school"}
    # cemeteries!
    tags = {"landuse": "cemetery"}
    gdf_buildings = ox.features.features_from_place(place, tags=tags)
    gdf_buildings.crs = common_crs
    # use a spooky gray for those

    tags = {"leisure": ["park", "garden"]}
    gdf_park = ox.features.features_from_place(place, tags=tags)
    # remove all elements of type node
    gdf_park = gdf_park[gdf_park["geometry"].apply(lambda x: x.geom_type != "Point")]
    gdf_park.crs = common_crs

    # write to disk
    gdf_park.to_csv("baltimore_parks.csv")

    # tags = {'boundaries': "administrative", "admin_level": "10"}
    # gdf_neighborhoods = ox.features.features_from_place(place, tags=tags)
    # load geojson file
    gdf_neighborhoods = gpd.read_file("data/Baltimore.geojson")
    # gdf_neighborhoods["color"] = bg_color
    gdf_neighborhoods.crs = common_crs

    # randomly assign one these colors to each neighborhood
    random.seed(args.seed)
    gdf_neighborhoods["color"] = gdf_neighborhoods.apply(lambda x: random.choice(list(city_colors.values())), axis=1)

    # choose a random color for each city neightborhood
    # gdf_neighborhoods["color"] = gdf_neighborhoods.apply(lambda x: "#%06x" % random.randint(0, 0xFFFFFF), axis=1)

    # load points from a csv file, create a GDF
    # df = pd.read_csv("data/ghost.csv")
    # gdf_ghost = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat))
    tags = {"memorial": "ghost_bike"}
    gdf_ghost = ox.features.features_from_place(place, tags=tags)
    gdf_ghost.crs = common_crs

    tags = {"amenity": "drinking_water"}
    gdf_drinking_fountains = ox.features.features_from_place(place, tags=tags)
    gdf_drinking_fountains.crs = common_crs

    ## Baltimore map
    fig, ax = plt.subplots(figsize=(36,48), dpi=300)
    fig.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)

    ax.set_xlim(gdf_neighborhoods.total_bounds[0] - one_km.x * 0.5, 
                gdf_neighborhoods.total_bounds[2] + one_km.x * 0.5)
    ax.set_ylim(gdf_neighborhoods.total_bounds[1] - one_km.y * 0.5, 
                gdf_neighborhoods.total_bounds[3] + one_km.y * 0.5)

    grid_color = "#cccccc"

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

    gdf_neighborhoods.plot(ax=ax, facecolor="white", linestyle="-", ec="black", linewidth=2, alpha=1)

    # gdf_water.plot(ax=ax, facecolor=water_blue, ec=water_blue, linewidth=1, alpha=1)
    gdf_water.plot(ax=ax, facecolor=water_blue, ec=water_blue, linewidth=1.5, alpha=1)
    gdf_park.plot(ax=ax, facecolor=park_green, ec="black", linewidth=0, alpha=1)

    # plot each point in gdf_ghost with bike-14.png as an icon
    gdf_ghost.plot(ax=ax, marker="X", markersize=50, color="black", alpha=1)

    # BALTIMORE city name
    add_title(ax, gdf_neighborhoods)

    # Print the name of each neighborhood on the map
    for idx, row in gdf_neighborhoods.iterrows():
        x = row["geometry"].centroid.x + offsets.get(row["Name"], (0, 0))[0]
        y = row["geometry"].centroid.y + offsets.get(row["Name"], (0, 0))[1]

        ax.annotate(
            text=munge(row["Name"]),
            xy=(x, y),
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=7,
            color="black",
            weight="bold",
            name="Avenir Next Condensed",
            # name="Phosphate",
        )

    # for every relation in parks, print the name in the middle of it
    if False:
        park_count = 0
        for idx, row in gdf_park.iterrows():
            name = row["name"]

            if name == "" or name is float:
                continue

            park_count += 1

            x = row["geometry"].centroid.x
            y = row["geometry"].centroid.y

            print(park_count, "PARK", name, x, y)

            ax.annotate(
                text=row["name"],
                xy=(x, y),
                horizontalalignment="center",
                verticalalignment="center",
                fontsize=6.5,
                color="#999999",
                style="italic",
                name="Avenir Next Condensed",
            )

    plt.savefig(f"{placename}-plain.pdf", dpi=300)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=14, type=int, help="Random seed")
    args = parser.parse_args()

    main(args)