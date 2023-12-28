import sys
import math

from collections import namedtuple

lat_lon_dist = namedtuple('lat_lon_dist', ['y', 'x'])

# one mile in latitude, longitude degrees
one_mile_lat = 0.01446
def one_mile_lon(lat):
    return 0.0144927536231884 * math.cos(lat * math.pi / 180)

# one km in latitude, longitude degrees
one_km = lat_lon_dist(0.008983, 0.0113636)

# Define a common CRS for both GeoDataFrames (replace with your desired CRS)
common_crs = 'EPSG:4326'

def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'

# Define a number of colors
bg_color = "white"
hood_color = "white"
street_color = "#dddddd"
cemetery_gray = "#666666"
grid_color = "#cccccc"

# wandrer
park_green = "#e0eed2"  # before transparency: "#c1e1a7"
water_blue = "#c6e2f3"  # before transparency: "#8bccec"

## v3
# water_blue = rgb_to_hex(4, 53, 108)
# park_green = "#1a5b07"  # mine
#park_green = "#b9e5a1"  # google
bike_orange = "orange"

ghost_color = bike_orange  # "black"  # "#721613"

# water_blue = "blue"
# park_green = "green"
# bike_orange = "orange"

## old veriants
# what is (43, 101, 50) in hex?
#   # rgb_to_hex(11, 82, 136)  # "#2c5c98"

## much lighter version (could turn off alpha)
## This looks good when you have starker neighborhood boundaries
# water_blue = "#b0cae3"
# park_green = "#c2dd9a"

# VISIT BALTIMORE
# water_blue = "#14275b"
# park_green = "#2d6a76"
# bike_orange = "#e44b25"

# Baltimore City connect color scheme
baltimore_city_colors = {
    "red": "#f23b33",
    "orange": "#f7693d",
    "yellow": "#FCEA65",  # "#fefc78",
    "pink": "#f37196",
    "purple": "#8d649e",
    "blue": "#a0cce8",
}

neighborhood_offsets = {
    "Holabird Industrial Park": (0, +0.003),
    "Locust Point Industrial Area": (0.001, -0.0035),
    "Penrose/Fayette Street Outreach": (0, +0.0005),
    "Keswick": (-0.001, 0),
    "Loyola/Notre Dame": (+0.002, 0),
    "Irvington": (0, +0.002),
    "West Forest Park": (0, +0.001),
    "Purnell": (0, +0.0005),
    "Patterson Park Neighborhood": (0, +0.0005),
    "Stadium/Entertainment Area": (+0.001, 0),
}

neighborhood_names = {
    "Belair-Edison": "Belair-Edison",
    "Broening Manor": "Broening Manor",
    "Carroll - Camden Industrial Area": "Carroll-Camden\nIndustrial Area",
    "Carroll-Camden Industrial Area": "Carroll-Camden\nIndustrial Area",
    "Canton Industrial Area": "Canton Industrial Area",
    "Cherry Hill": "Cherry Hill",
    "Clifton Park": "Clifton Park",
    "Concerned Citizens of Forest Park": "Concerned\nCitizens\nof Forest\nPark",
    "Coppin Heights/Ash-Co-East": "Coppin Heights/\nAsh-Co-East",
    "Curtis Bay Industrial Area": "Curtis Bay\nIndustrial\nArea",
    "Easterwood": "Easter-\nwood",
    "Fairfield Area": "Fairfield Area",
    "Forest Park Golf Course": "Forest Park\nGolf Course",
    "Franklintown Road": "Franklin-\ntown\nRoad",
    "Greenmount West": "Green-\nmount\nWest",
    "Grove Park": "Grove Park",
    "Gwynn Falls / Leakin Park": "Gwynn Falls / Leakin Park",
    "Hamilton Hills": "Hamilton Hills",
    "Hanlon-Longwood": "Hanlon-Longwood",
    "Harlem Park": "Harlem Park",
    "Howard Park": "Howard Park",
    "Loch Raven": "Loch Raven",
    "Locust Point": "Locust Point",
    "Locust Point Industrial Area": "Locust Point\nIndustrial Area",
    "Morrell Park": "Morrell Park",
    "North Roland Park/Poplar Hill": "North Roland Park/\nPoplar Hill",
    "North Harford Road": "North Harford Road",
    "Patterson Park Neighborhood": "Patterson Park\nNeighborhood",
    "Penrose/Fayette Street Outreach": "Penrose/Fayette Street Outreach",
    "South Clifton Park": "South Clifton Park",
    "South Clifton Park": "South Clifton Park",
    "West Hills": "West Hills",
    "Wilhelm Park": "Wilhelm Park",
    "Yale Heights": "Yale Heights",
}

def munge(name: str):
    munged_name = neighborhood_names.get(name, name.replace(" ", "\n").replace("/","/\n").replace("-","-\n"))
    return munged_name

def add_title(ax, gdf_neighborhoods, place="Baltimore"):
    ax.text(
        s=place.upper(),
        x=gdf_neighborhoods.total_bounds[0],
        y=gdf_neighborhoods.total_bounds[1] - one_km.y,
        fontsize=220,
        color="black",
        weight=400,
        verticalalignment="bottom",
        horizontalalignment="left",
        name="Avenir Next",
    )

    if place.lower().startswith("baltimore"):
        # NEIGHBORHOODS 2023
        ax.text(
            s="NEIGHBORHOODS 2023",
            x=-76.6625,
            y=39.2040,
            fontsize=80,
            color="black",
            weight=50,
            verticalalignment="bottom",
            horizontalalignment="left",
            name="Avenir Next Condensed",
        )

# for the north/south adjustments, we need to take into account the
# curvature of the earth. Here we find how much we need to add to the Y
# access, using the mid-latitude point as an approximation.
# return the distance between two longitude coordinates at a given latitude
def lon_distance(lon1, lon2, lat):
    return abs(lon2 - lon1) * math.cos(lat * math.pi / 180)


def scale(north, south, east, west, target_ratio=1.5):
    """
    Scales the map to the target ratio, while keeping the center of the map.
    """

    # Find which dimension is larger
    height = abs(north - south)
    width = lon_distance(west, east, (north + south) / 2)

    if height / width < target_ratio:
        # Scale the height
        compensation = target_ratio * width - height
        north += compensation / 2
        south -= compensation / 2

    else:
        # Scale the width
        compensation = (height - target_ratio * width) / target_ratio
        east += compensation / 2
        west -= compensation / 2

    print("Adjusted boundaries:", *map(lambda x: f"{x:.5f}", [west, south, east, north]), file=sys.stderr)

    return north, south, east, west
        

