import json

from classes.DebugLogger import DebugLogger
from data.CelesteLevelData import CelesteLevelData
from data.CelesteLocationData import CelesteLocationData
from data.CelesteLogicData import CelesteLogicData


def readCelesteLevelData() -> CelesteLevelData:
    """
    Reads Celeste Level Data from the relevant JSON file and coverts it into Python objects with the same structure as the JSON file.
    """

    try:
        with open("./data/CelesteLevelData.json", "r") as file:
            rawJson = json.load(file)
            return CelesteLevelData.fromJsonDict(rawJson)
    except FileNotFoundError:
        DebugLogger.logDebug("Error: The JSON file was not found.")
        raise
    except json.JSONDecodeError as e:
        DebugLogger.logDebug(f"Error: Failed to decode JSON from the file: {e}")
        raise


def readCelesteLocationData() -> CelesteLocationData:
    """
    Reads Celeste Location Data from the relevant JSON file and coverts it into Python objects with the same structure as the JSON file.
    """

    try:
        with open("./data/CelesteLocationData.json", "r") as file:
            rawJson = json.load(file)
            return CelesteLocationData.fromJsonDict(rawJson)
    except FileNotFoundError:
        DebugLogger.logDebug("Error: The JSON file was not found.")
        raise
    except json.JSONDecodeError as e:
        DebugLogger.logDebug(f"Error: Failed to decode JSON from the file: {e}")
        raise


def readCelesteLogicData() -> CelesteLogicData:
    """
    Reads Celeste Location Data from the relevant JSON file and coverts it into Python objects with the same structure as the JSON file.
    """

    try:
        with open("./data/CelesteLogicData.json", "r") as file:
            rawJson = json.load(file)
            return CelesteLogicData.fromJsonDict(rawJson)
    except FileNotFoundError:
        DebugLogger.logDebug("Error: The JSON file was not found.")
        raise
    except json.JSONDecodeError as e:
        DebugLogger.logDebug(f"Error: Failed to decode JSON from the file: {e}")
        raise
