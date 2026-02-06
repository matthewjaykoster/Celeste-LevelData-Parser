"""
Generates all locations from the Celesete Level Data file into /data/CelesteLogicData.json.
"""

from typing import List

from classes.DebugLogger import DebugLogger
from data.CelesteLocationData import (
    CelesteLocationCheck,
    CelesteLocationType,
)
from data.celeste_data_file_reader import readCelesteLevelData
from data.celeste_data_file_writer import writeLocationsToJsonDataFile


def getAllLocations() -> List[CelesteLocationCheck]:
    DebugLogger.logDebug("Loading level data...")
    rawLevelData = readCelesteLevelData()

    DebugLogger.logDebug("Pulling locations from level data...")
    allLocations: List[CelesteLocationCheck] = []
    for level in rawLevelData.levels:
        for room in level.rooms:
            # Checkpoint locations
            if room.checkpoint != "":
                allLocations.append(
                    CelesteLocationCheck(
                        level.name,
                        level.display_name,
                        room.name,
                        room.checkpoint_region,
                        room.checkpoint,
                        room.checkpoint,
                        CelesteLocationType.CHECKPOINT.value,
                        [],
                        [],
                    )
                )

            for region in room.regions:
                for location in region.locations or []:
                    # All other location types
                    allLocations.append(
                        CelesteLocationCheck(
                            level.name,
                            level.display_name,
                            room.name,
                            region.name,
                            location.name,
                            location.display_name,
                            location.type,
                            location.rule,
                            [],
                        )
                    )

    DebugLogger.logDebugVerbose(allLocations)
    return allLocations


################
# Script Logic #
################
allLocations = getAllLocations()
writeLocationsToJsonDataFile(allLocations)
