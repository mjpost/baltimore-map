# Baltimore Neighborhoods — Interactive Map

An interactive web map of Baltimore showing neighborhood boundaries, City Council
districts, and parks. Built as a single static HTML page using
[Leaflet](https://leafletjs.com/) — no build step or backend required.

## Files

| File | Purpose |
|---|---|
| `index.html` | The entire app: HTML, CSS, JS in one file |
| `optimize_geojson.py` | Builds the optimized GeoJSON files from sources in `../data/` |
| `baltimore_neighborhoods.geojson` | 279 neighborhood polygons + Census demographics |
| `baltimore_districts.geojson` | 14 City Council district polygons |
| `baltimore_parks.geojson` | Park polygons |

The optimizer strips unused properties, simplifies geometry (Douglas–Peucker via
Shapely), and truncates coordinates to ~1.1 m precision, reducing total payload
from ~8.5 MB to ~440 KB.

## Running locally

Serve the directory over HTTP (relative `fetch()` calls won't work from
`file://`):

```sh
cd /Users/post/code/baltimore-map
python3 -m http.server 8081
# then open http://localhost:8081/web/
```

## Functionality

### Layers (always visible)
- **Basemap** — light Carto tiles at low opacity for street context
- **Parks** — green polygons, named on hover
- **Neighborhoods** — outlined polygons with text labels (labels appear at
  zoom ≥ 13)
- **Districts** — colored, dashed-outline polygons with large numeric labels
  (labels appear at zoom ≥ 11)

### Selection mode (legend toggle)
A "Clicking selects: [Neighborhoods] [Districts]" toggle controls what map
clicks select. The non-active layer remains visible underneath. The mode
swaps the SVG z-order so the active layer receives clicks/hovers natively.

### Interactions
- **Hover a neighborhood polygon** (in Neighborhoods mode): orange highlight
- **Hover a district polygon** (in Districts mode): orange border highlight
- **Click a neighborhood**: selects it, shows info panel with population,
  housing units, racial-distribution bar (emoji skin-tone palette), and
  occupied/vacant housing bar
- **Click a district** (in Districts mode, or via legend swatch): highlights
  the district and shows the council representative's name, phone, and email
- **Search box**: type to filter the alphabetical neighborhood list; hovering
  a result highlights it on the map; clicking selects it
- **Zoom slider**: custom horizontal slider in the legend (desktop) or fixed
  to the bottom of the screen (mobile)

### Mobile layout (≤ 600 px)
- Legend collapses to a top sheet, toggled with the ☰ button
- District legend becomes a single horizontal row of numbered swatches
- Zoom bar is fixed to the bottom of the screen
- Title sits just above the zoom bar

### URL state
The current map view, mode, and selection are reflected in the URL query
string (`?lat=…&lng=…&z=…&mode=…&n=…&d=…`) via `history.replaceState`. Loading
a URL with these params restores the exact state, which makes the map
shareable and bookmarkable.

## Code organization

`index.html` is a single file, structured top-to-bottom roughly as:

1. **CSS** — desktop styles, then a `@media (max-width: 600px)` block for
   mobile overrides
2. **Constants** — neighborhood name overrides and label offsets (mirrored
   from `../common.py`), color palette, district fill colors, council rep
   info, and Leaflet style presets
3. **Map setup** — Leaflet map with custom zoom range, no default zoom control
4. **State** — `neighborhoodIndex`, `districtIndex`, `selectedNeighborhood`,
   `selectedDistrict`, `selectionMode`
5. **URL helpers** — `updateURL()`, `getURLParams()`
6. **Hover helpers** — `highlightNeighborhood`, `resetNeighborhood`,
   `highlightDistrictLayer`, `resetDistrictLayer`, `handleHover`, `clearHover`
7. **Data load** — `Promise.all([...fetch...])` then build all layers, the
   `ToggleControl` (legend), and zoom-dependent label visibility
8. **Title kerning** — adjusts subtitle letter-spacing to match the title
   width once fonts are loaded
