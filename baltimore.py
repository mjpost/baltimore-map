#!/usr/bin/env python3

import random
import osmnx as ox
import gpxpy
import geopandas as gpd
import gpxpy.gpx
import pandas as pd

from collections import namedtuple
import matplotlib.pyplot as plt


# Turn on the local cache and console logging
ox.settings.log_console = True
ox.settings.use_cache = True
print(ox.__version__)

lat_lon_dist = namedtuple('lat_lon_dist', ['y', 'x'])

# one mile in latitude, longitude degrees
one_mile = lat_lon_dist(0.0144927536231884, 0.0181818181818182)

# one km in latitude, longitude degrees
one_km = lat_lon_dist(0.008983, 0.0113636)


def main(args):
    place = "Baltimore, MD"
    placename = place.split(',')[0].replace(" ", "").lower()
    # Define a common CRS for both GeoDataFrames (replace with your desired CRS)
    common_crs = 'EPSG:4326'

    G = ox.graph_from_place(place, network_type="drive")
    # fig, ax = ox.plot_graph(G,
    #     # bgcolor="#333333",
    #     edge_color="white",
    #     edge_linewidth=0.1,
    #     node_size=0,
    # )

    gdf_streets = ox.graph_to_gdfs(G, nodes=False, edges=True, node_geometry=True, fill_edge_geometry=True)
    gdf_streets = gdf_streets.to_crs(common_crs)

    # get all parks from the OSM database
    # tags = {'natural': 'water', 'boundaries': "administrative", "admin_level": "9", 'leisure': ["garden"]}
    # tags = {'boundaries': "administrative", "admin_level": "10", "natural": "water"}  # , "leisure": ["park", "garden"]}

    bg_color = "white"  # "#e0e0e0"
    street_color = "#cccccc"
    cemetery_gray = "#666666"
    park_green = "#b2df8a"

    # define a good RGB blue for water
    water_blue = "#a6cee3"

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
    random.seed(14)
    # city_mosaic = ["red", "orange", "teal", "yellow", "pink", "purple"]
    city_mosaic = ["#f23b33", "#f7693d", "#a0cce8", "#e1ed6a", "#f37196", "#8d649e"]
    gdf_neighborhoods["color"] = gdf_neighborhoods.apply(lambda x: random.choice(city_mosaic), axis=1)

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

    # print(gdf_park)

    # remove all rows that are not polygons
    # gdf_neighborhoods = gdf_neighborhoods[gdf_neighborhoods["geometry"].apply(lambda x: x.type == "Polygon")]
    # gdf_neighborhoods.to_csv("baltimore.csv")

    ## Baltimore map
    fig, ax = plt.subplots(figsize=(36,48), dpi=300)

    # ax.set_xlim(gdf_streets.total_bounds[0] - one_km.x, gdf_streets.total_bounds[2] + one_km.x)
    # ax.set_ylim(gdf_streets.total_bounds[1] - one_km.y * 1.5, gdf_streets.total_bounds[3] + one_km.y * 0.75)

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
    gdf_neighborhoods.plot(ax=ax, facecolor=gdf_neighborhoods["color"], linestyle="-", ec="orange", linewidth=2, alpha=0.5)
    gdf_streets.plot(ax=ax, ec=street_color, linewidth=1, alpha=0.5)
    gdf_water.plot(ax=ax, facecolor=water_blue, ec=water_blue, linewidth=1, alpha=1)
    gdf_park.plot(ax=ax, facecolor=park_green, ec="black", linewidth=1.2, alpha=1)
    gdf_buildings.plot(ax=ax, facecolor=cemetery_gray, linewidth=1.2, alpha=0.3)
    # gdf_neighborhoods["color"] = gdf_neighborhoods.apply(lambda x: "#%06x" % random.randint(0, 0xFFFFFF), axis=1)
    # gdf_neighborhoods.plot(ax=ax, facecolor=gdf_neighborhoods["color"], linestyle="--", ec="orange", linewidth=1.5, alpha=1)

    # plot each point in gdf_ghost with bike-14.png as an icon
    gdf_ghost.plot(ax=ax, marker="X", markersize=50, color="black", alpha=1)

    font_color = "#aaaaaa"

    # BALTIMORE city name
    if False:
        ax.text(
            s="Baltimore",
            x=gdf_neighborhoods.total_bounds[0],
            y=gdf_neighborhoods.total_bounds[1] - 0.003,  # + (gdf_streets.total_bounds[3] - gdf_streets.total_bounds[1]) * 0.25,
            fontsize=144,
            color=font_color,
            weight="bold",
            verticalalignment="bottom",
            horizontalalignment="left",
            name="Phosphate",
        )

    # # NEIGHBORHOODS 2023
    # ax.text(
    #     s="Neighborhoods 2023",
    #     x=-76.6500,
    #     y=39.2075,
    #     fontsize=30,
    #     color=font_color,
    #     weight="bold",
    #     verticalalignment="bottom",
    #     horizontalalignment="left",
    #     name="Avenir Next Condensed",
    # )

    # draw_compass(-76.6660, 39.2480)
    # draw_scale_patch(-76.673, 39.2319)
    # draw_legend(-76.709, 39.2319)

    offsets = {
        "Holabird Industrial Park": (0, +0.003),
        "Locust Point Industrial Area": (0.001, -0.0035),
        "Penrose/Fayette Street Outreach": (0, +0.0005),
        "Keswick": (-0.001, 0),
        "Loyola/Notre Dame": (+0.002, 0),
        "Irvington": (0, +0.002),
        "West Forest Park": (0, +0.001),
        "Purnell": (0, +0.0005),
    }

    names = {
        "Carroll - Camden Industrial Area": "Carroll-\nCamden\nIndustrial\nArea",
        "Penrose/Fayette Street Outreach": "Penrose/Fayette\nStreet Outreach",
        "Coppin Heights/Ash-Co-East": "Coppin Heights/\nAsh-Co-East",
        "Concerned Citizens of Forest Park": "Concerned\nCitizens\nof Forest\nPark",
    }

    def munge(name: str):
        munged_name = names.get(name, name.replace(" ", "\n").replace("/","/\n").replace("-","-\n"))
        return munged_name.upper()

    # Print the name of each neighborhood on the map
    for idx, row in gdf_neighborhoods.iterrows():
        x = row["geometry"].centroid.x + offsets.get(row["Name"], (0, 0))[0]
        y = row["geometry"].centroid.y + offsets.get(row["Name"], (0, 0))[1]

        ax.annotate(
            text=munge(row["Name"]),
            xy=(x, y),
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=6.5,
            color="#999999",
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

    plt.savefig(f"{placename}.pdf", dpi=300)


def draw_legend(ax, x, y):
    wx = one_km.x / 3
    wy = one_km.y / 3

    # a square for the parks
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y),
            width=wx,
            height=wy,
            linewidth=1,
            color=park_green,
            fill=True,
            ec="#333333",
            alpha=0.5,
        )
    )
    # and for the water
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y + wy * 1.25),
            width=wx,
            height=wy,
            linewidth=1,
            color=water_blue,
            fill=True,
            ec="#333333",
            alpha=0.5,
        )
    )
    # draw a small gray square just above that
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y + wy * 2.5),
            width=wx,
            height=wy,
            linewidth=1,
            color=cemetery_gray,
            fill=True,
            ec="#333333",
            alpha=0.5,
        )
    )
    # plot a single point
    ax.plot(
        x,
        y + wy * 3.75,
        marker="X",
        markersize=10,
        color="black",
        alpha=1,
    )
    # border
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y + wy * 5),
            width=wx,
            height=wy/5,
            linewidth=1,
            color="orange",
            fill=True,
            # ec="#333333",
            alpha=0.5,
        )
    )
    # street
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y + wy * 6.25),
            width=wx,
            height=wy/5,
            linewidth=1,
            color=street_color,
            fill=True,
            # ec="#333333",
            alpha=0.5,
        )
    )

    ax.text(
        s="Park",
        x=x + wx * 1.5,
        y=y,
        fontsize=12,
        color="black",
        verticalalignment="bottom",
        horizontalalignment="left",
        weight="light",
        name="Avenir Next Condensed",
    )


def draw_scale_patch(ax, x, y):
    ax.add_patch(
        plt.Rectangle(
            xy=(x, y),
            width=one_mile.x,
            height=one_mile.y,
            linewidth=2,
            color="#aaaaaa",
            fill=False,
        )
    )
    ax.text(
        s="one\nsquare\nmile",
        x=x + one_mile.x / 2,
        y=y + one_mile.y / 2,
        fontsize=14,
        color=font_color,
        weight="bold",
        verticalalignment="center",
        horizontalalignment="center",
        name="Avenir Next",
    )


def draw_compass(ax, x, y):
    # Draw an arrow pointing north, with a fancy N above it
    ax.text(
        s="N",
        x=-76.6660,
        y=39.2480,
        fontsize=28,
        color="#666666",
        weight="bold",
        verticalalignment="bottom",
        horizontalalignment="center",
        name="Apple Chancery",
    )
    # next draw a little tiny red triangle above the N
    ax.arrow(
        x=-76.6655,
        y=39.2480,
        dx=0,
        dy=0.005,
        head_width=0.0025,
        head_length=0.0010,
        fc="orange",
        ec="orange",
        alpha=0.5,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=14, type=int, help="Random seed")
    args = parser.parse_args()

    main(args)
