import json
from types import SimpleNamespace

def readCelesteLevelData():
    """
    Reads Celeste Level Data from the relevant JSON file and coverts it into Python objects with the same structure as the JSON file.
    """

    try:
        with open('./data/CelesteLevelData.json', 'r') as file:
            return json.load(file, object_hook=lambda d: SimpleNamespace(**d))
    except FileNotFoundError:
        print('Error: The JSON file was not found.')
    except json.JSONDecodeError as e:
        print(f'Error: Failed to decode JSON from the file: {e}')