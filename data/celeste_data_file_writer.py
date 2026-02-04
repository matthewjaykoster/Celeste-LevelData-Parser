import json
from pathlib import Path
from typing import List
from classes.DebugLogger import DebugLogger
from data.CelesteLogicData import CelesteLogicData, LocationCheckLogic
from data.CelesteLocationData import CelesteLocationCheck, CelesteLocationData


def writeLocationsToJsonDataFile(locations: List[CelesteLocationCheck]):
    celesteLocationData = CelesteLocationData(locations)
    jsonData = celesteLocationData.toJsonDict()

    baseDirectory = Path(__file__).resolve().parent.parent
    outputPath: Path = (
        baseDirectory / "data" / "CelesteLocationData.json"
    )  # TODO Improve this resolution path
    DebugLogger.logDebug(f"Writing location data to {outputPath}")

    with outputPath.open("w", encoding="utf-8") as f:
        json.dump(jsonData, f, indent=2)

    DebugLogger.logDebug("Location data written successfully.")


def writeLogicToJsonDataFile(logic: List[LocationCheckLogic]):
    celesteLogicData = CelesteLogicData(logic)
    jsonData = celesteLogicData.toJsonDict()

    baseDirectory = Path(__file__).resolve().parent.parent
    outputPath: Path = (
        baseDirectory / "data" / "CelesteLogicData.json"
    )  # TODO Improve this resolution path
    DebugLogger.logDebug(f"Writing location data to {outputPath}")

    with outputPath.open("w", encoding="utf-8") as f:
        json.dump(jsonData, f, indent=2)

    DebugLogger.logDebug("Logic data written successfully.")
