import json
from types import SimpleNamespace

def parseCelesteLevelData():
    try:
        with open('./data/CelesteLevelData.json', 'r') as file:
            return json.load(file, object_hook=lambda d: SimpleNamespace(**d))
    except FileNotFoundError:
        print('Error: The JSON file was not found.')
    except json.JSONDecodeError as e:
        print(f'Error: Failed to decode JSON from the file: {e}')

parseCelesteLevelData()