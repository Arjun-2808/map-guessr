# Map Guessr

Three blank-map guessing games, each a single static HTML page:

- **Kabupaten Guessr** (`/`): Indonesia's 514 kabupaten and kota, by island group or province.
- **Philippines Guessr** (`/philippines`): 82 provinces + Metro Manila, or the 18 regions.
- **Area Code Guessr** (`/area-codes`): every in-service US area code, overlays included.

Each game has a score run (up to 1,000 points per guess, less the further off you are) and a drill mode (clear every name in an area, three tries each).

## Layout

- `public/` is what gets deployed. Each page embeds its own map data; d3 and topojson-client load from CDNs.
- `src/` has the shared game engine, per-game config and the Python data-prep scripts used to build the pages.

## Data

- Indonesia: BPS 2020 boundaries via [geoBoundaries](https://www.geoboundaries.org) (CC BY 3.0 IGO), with the 2022 Papua split and current regency names.
- Philippines: PSA/NAMRIA PSGC (Dec 2023) via [faeldon/philippines-json-maps](https://github.com/faeldon/philippines-json-maps). Includes the 2024 Negros Island Region; Sulu shown outside BARMM after the 2024 Supreme Court ruling.
- US: HIFLD/HSIP 2010 area code polygons (public domain), with later overlays matched through the NANPA database via [benaduggan/area-code-map](https://github.com/benaduggan/area-code-map). Territories aren't shown.
