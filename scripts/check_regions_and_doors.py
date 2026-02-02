"""
Run through Celeste's level data to check that all doors have corresponding regions.
"""

from typing import Optional
from classes.DebugLogger import DebugLogger
from data.celeste_data_file_reader import readCelesteLevelData
from data.CelesteLevelData import Region

PRINT_ONLY_MISSING = True

rawLevelData = readCelesteLevelData()

DebugLogger.logDebug(
    f"Checking level data to ensure that all doors have related regions. PRINT_ONLY_MISSING = {PRINT_ONLY_MISSING}"
)
for level in rawLevelData.levels:
    for room in level.rooms:
        for door in room.doors:
            relatedRegion: Optional[Region] = next(
                (region for region in room.regions if region.name == door.name), None
            )
            if relatedRegion is None:
                DebugLogger.logDebugVerbose(
                    f"[Level {level.display_name} - Room {room.name}] Door {door.name} is missing a region."
                )
            elif not PRINT_ONLY_MISSING:
                DebugLogger.logDebugVerbose(
                    f"[Level {level.display_name} - Room {room.name}] Door {door.name} is located in Region {relatedRegion.name}."
                )

DebugLogger.logDebug("Script complete.")
