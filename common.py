from collections import namedtuple

lat_lon_dist = namedtuple('lat_lon_dist', ['y', 'x'])

# one mile in latitude, longitude degrees
one_mile = lat_lon_dist(0.0144927536231884, 0.0181818181818182)

# one km in latitude, longitude degrees
one_km = lat_lon_dist(0.008983, 0.0113636)

# Define a common CRS for both GeoDataFrames (replace with your desired CRS)
common_crs = 'EPSG:4326'

def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'

# Define a number of colors
street_color = "#cccccc"
cemetery_gray = "#666666"
grid_color = "#cccccc"
ghost_color = "#721613"
# what is (43, 101, 50) in hex?
water_blue = rgb_to_hex(4, 53, 108)  # rgb_to_hex(11, 82, 136)  # "#2c5c98"
park_green = "#1a5b07"

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
    "Carroll - Camden Industrial Area": "Carroll-Camden\nIndustrial Area",
    "Penrose/Fayette Street Outreach": "Penrose/Fayette\nStreet Outreach",
    "Coppin Heights/Ash-Co-East": "Coppin Heights/\nAsh-Co-East",
    "Concerned Citizens of Forest Park": "Concerned\nCitizens\nof Forest\nPark",
    "Greenmount West": "Green-\nmount\nWest",
    "South Clifton Park": "South Clifton Park",
    "North Roland Park / Poplar Hill": "North Roland Park\n/ Poplar Hill",
    "South Clifton Park": "South Clifton Park",
    "Canton Industrial Area": "Canton Industrial Area",
    "Local Point Industrial Area": "Local Point\nIndustrial Area",
    "Carroll-Camden Industrial Area": "Carroll-Camden\nIndustrial Area",
    "Cherry Hill": "Cherry Hill",
    "Wilhelm Park": "Wilhelm Park",
    "Morrell Park": "Morrell Park",
    "Forest Park Golf Course": "Forest Park\nGolf Course",
    "Howard Park": "Howard Park",
    "Grove Park": "Grove Park",
    "West Hills": "West Hills",
}

def munge(name: str):
    munged_name = neighborhood_names.get(name, name.replace(" ", "\n").replace("/","/\n").replace("-","-\n"))
    return munged_name.upper()

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
