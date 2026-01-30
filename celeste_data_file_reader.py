import json

from data.CelesteLevelData import CelesteLevelData


def readCelesteLevelData() -> CelesteLevelData:
    """
    Reads Celeste Level Data from the relevant JSON file and coverts it into Python objects with the same structure as the JSON file.
    """

    try:
        with open("./data/CelesteLevelData.json", "r") as file:
            rawJson = json.load(file)
            return CelesteLevelData.fromJsonDict(rawJson)
    except FileNotFoundError:
        print("Error: The JSON file was not found.")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from the file: {e}")
        raise
