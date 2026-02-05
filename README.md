# Celeste-LevelData-Parser

Small toolset which enables parsing of the [Celeste Open World Archipelago level data file](https://github.com/PoryGoneDev/Pory_Archipelago/blob/main/worlds/celeste_open_world/data/CelesteLevelData.json) located in [PoryGone's](https://github.com/PoryGoneDev) custom [AP World](https://github.com/PoryGoneDev/Pory_Archipelago) built to handle a variety of Archipelago worlds, including Celeste Open World.

Primarily used to build logic chains from the base room of a level to all of the possible checks in that level for export into my [Celeste Open World PopTracker Pack](https://github.com/matthewjaykoster/Celeste-OW-Archipelago-Tracker).

## Use

Requires Python 3.14.2.

Run any of the scripts using Python and you should be good to go. However, these tools were purpose-built and not really intended for use or consumption outside those purposes, so that's all the documentation I'll be providing.

### Typical Use

Run the scripts in the following order:

1. `./scripts/generate_locations.py`
2. `./scripts/generate_location_paths.py`
3. `./scripts/generate_logic.py`
4. `./scripts/save_logic_to_lua_json.py`

At the end of this sequence, you should have generated a datafile with the necessary logic located at `./data/CelesteLogicData.json` and loaded the relevant logic to each of the locations within the PopTracker Locations JSON.
