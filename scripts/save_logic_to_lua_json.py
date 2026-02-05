"""
Saves logic in generated JSON file /data/CelesteLogicData.json into PopTracker
pack JSON location config files.
"""

from pathlib import Path
import json
from typing import Dict, Any, List

from classes.DebugLogger import DebugLogger
from data.CelesteLocationData import CelesteLocationType
from data.CelesteLogicData import LocationCheckLogic
from data.celeste_data_file_reader import readCelesteLogicData

DRY_RUN: bool = True

IGNORE_LOCATION_TYPES: List[str] = []  # Don't load logic for these location types

JSON_FILE_CACHE: Dict[str, List[Dict[str, Any]]] = {}

LEVEL_TO_FILE_MAP = {
    "Celestial Resort": "celestial_resort.json",
    "Core": "core.json",
    "Epilogue": "epilogue.json",
    "Farewell": "farewell.json",
    "Forsaken City": "forsaken_city.json",
    "Golden Ridge": "golden_ridge.json",
    "Mirror Temple": "mirror_temple.json",
    "Old Site": "old_site.json",
    "Prologue": "prologue.json",
    "Reflection": "reflection.json",
    "The Summit": "summit.json",
}

POPTRACKER_LOCATION_JSON_DIRECTORY: Path = Path(
    ""  # Absolute path to the directory containing the target JSON files
)


def buildSectionName(locationLogic: LocationCheckLogic) -> str:
    """
    Builds the expected section name in the target JSON based on location logic.
    """
    if locationLogic.location_type == "strawberry":
        return f"Room {locationLogic.room_name} {locationLogic.location_display_name}"

    return locationLogic.location_display_name


def convertLogicRules(logicRules: List[List[str]]) -> List[str]:
    """
    Converts logic rules into a format understood by PopTracker's LUA-read JSON files.
    """
    result = []
    for ruleGroup in logicRules:
        mappedRuleGroup = []
        for rule in ruleGroup:
            # Strip underscores from all non-function rules. Functions are denoted with a leading $.
            if rule.startswith("$"):
                mappedRuleGroup.append(rule)
            else:
                mappedRuleGroup.append(rule.replace("_", ""))

        # Join inner lists into comma-separated strings
        result.append(",".join(mappedRuleGroup))

    return result


def ensureAccessRules(affectedFiles: set):
    """
    Ensure 'access_rules' exists in all relevant JSON structures. There's an easily misunderstood
    feature of PopTracker where child access_rules do not get run if no parent is defined.
    """
    DebugLogger.logDebug("Ensuring that access_rules fields exist in all JSON files.")
    for fileName in POPTRACKER_LOCATION_JSON_DIRECTORY.glob("*.json"):
        jsonData = JSON_FILE_CACHE.get(fileName.name) or _loadFileIntoCache(
            fileName.name
        )
        updated = False

        # The top-level JSON file is a list of level data objects
        for levelData in jsonData:
            # Ensure access_rules exists at top level
            if "access_rules" not in levelData:
                levelData["access_rules"] = []
                updated = True

            # Sections at top level (some levels may have sections directly)
            for section in levelData.get("sections", []):
                if "access_rules" not in section and "ref" not in section:
                    section["access_rules"] = []
                    updated = True

            # Children
            for child in levelData.get("children", []):
                if "access_rules" not in child:
                    child["access_rules"] = []
                    updated = True

                # Sections within children
                for section in child.get("sections", []):
                    if "access_rules" not in section and "ref" not in section:
                        section["access_rules"] = []
                        updated = True

        if updated and not DRY_RUN:
            DebugLogger.logDebug(f"Added access_rules field to {fileName.name}.")
            affectedFiles.add(fileName.name)
            JSON_FILE_CACHE[fileName.name] = jsonData


def findLevelData(
    jsonData: List[Dict[str, Any]],
    levelDisplayName: str,
) -> Dict[str, Any] | None:
    """
    Finds the top-level level data object matching the given display name.
    """
    for levelData in jsonData:
        if levelData.get("name") == levelDisplayName:
            return levelData

    return None


def findTargetSectionForLocationLogic(
    locationLogic: LocationCheckLogic,
) -> Dict[str, Any] | None:
    """
    Locates the section object in the target JSON file that corresponds
    to the given location logic.

    Returns the section dict if found, otherwise None.
    """

    jsonData = getTargetJsonForLocationLogic(locationLogic)

    levelData = findLevelData(jsonData, locationLogic.level_display_name)
    if levelData is None:
        DebugLogger.logDebug(
            f"[WARN] No level data found for '{locationLogic.level_display_name}'"
        )
        return None

    expectedSectionName = buildSectionName(locationLogic)

    children = levelData.get("children")
    if children:
        # Main: Check through all child sections
        for child in children:
            for section in child.get("sections", []):
                if section.get("name") == expectedSectionName:
                    return section
    else:
        # Fallback: check top-level "sections"
        for section in levelData.get("sections", []):
            if section.get("name") == expectedSectionName:
                return section

    DebugLogger.logDebug(
        f"[WARN] Section not found: '{expectedSectionName}' "
        f"in level '{locationLogic.level_display_name}'"
    )
    return None


def flushJsonFileCacheToDisk() -> None:
    DebugLogger.logDebug("Saving loaded JSON file data to disk.")

    if POPTRACKER_LOCATION_JSON_DIRECTORY is None:
        raise RuntimeError("POPTRACKER_LOCATION_JSON_DIRECTORY is not set")
    for fileName, jsonData in JSON_FILE_CACHE.items():
        if DRY_RUN:
            DebugLogger.logDebug(f"[DRY RUN] Would write {fileName} to disk.")
            continue
        filePath = POPTRACKER_LOCATION_JSON_DIRECTORY / fileName
        with filePath.open("w", encoding="utf-8") as f:
            json.dump(jsonData, f, indent=2, ensure_ascii=False)

    DebugLogger.logDebug("Save complete.")


def getBaseLevelName(levelDisplayName: str) -> str:
    # "Forsaken City A" -> "Forsaken City"
    return levelDisplayName.rsplit(" ", 1)[0]


def getTargetJsonForLocationLogic(
    locationLogic: LocationCheckLogic,
) -> List[Dict[str, Any]]:
    """
    Loads and returns the target JSON file for the given location logic object.
    """

    if POPTRACKER_LOCATION_JSON_DIRECTORY is None:
        raise RuntimeError("POPTRACKER_LOCATION_JSON_DIRECTORY has not been set")

    levelDisplayName = locationLogic.level_display_name
    baseLevelName = getBaseLevelName(levelDisplayName)

    if baseLevelName not in LEVEL_TO_FILE_MAP:
        raise ValueError(f"No target JSON file mapped for level '{baseLevelName}'")

    targetFileName = LEVEL_TO_FILE_MAP[baseLevelName]

    # If we have the file in cache already, use it. Otherwise load.
    if targetFileName in JSON_FILE_CACHE:
        return JSON_FILE_CACHE[targetFileName]

    return _loadFileIntoCache(targetFileName)


def injectLogicRulesIntoSection(
    section: Dict[str, Any],
    logicRules: List[List[str]],
) -> None:
    """
    Replaces the section's 'access_rules' with converted logic rules.
    """

    section["access_rules"] = convertLogicRules(logicRules)


def _loadFileIntoCache(targetFileName: str) -> List[Dict[str, Any]]:
    DebugLogger.logDebug(f"Loading {targetFileName} into memory cache.")
    targetFilePath = POPTRACKER_LOCATION_JSON_DIRECTORY / targetFileName

    if not targetFilePath.exists():
        raise FileNotFoundError(f"Target JSON file not found: {targetFilePath}")

    with targetFilePath.open("r", encoding="utf-8") as file:
        JSON_FILE_CACHE[targetFileName] = json.load(file)

    DebugLogger.logDebug(f"{targetFileName} loaded into cache.")
    return JSON_FILE_CACHE[targetFileName]


#################
# Script Logic  #
#################
def main() -> None:
    if POPTRACKER_LOCATION_JSON_DIRECTORY is None:
        raise RuntimeError("POPTRACKER_LOCATION_JSON_DIRECTORY must be set")

    affectedFiles = set()
    ensureAccessRules(affectedFiles)

    rawLogicData = readCelesteLogicData()

    # Summary counters
    ignoredCount = 0
    missingSectionCount = 0
    updatedCount = 0

    for locationLogic in rawLogicData.locationLogic:
        if locationLogic.location_type in IGNORE_LOCATION_TYPES:
            ignoredCount += 1
            continue

        section = findTargetSectionForLocationLogic(locationLogic)
        if section is None:
            missingSectionCount += 1
            print(
                f"[WARN] Missing section for {locationLogic.level_display_name}, {locationLogic.room_name}, {locationLogic.location_display_name}"
            )
            continue
        injectLogicRulesIntoSection(section, locationLogic.logic_rule)
        updatedCount += 1

        targetFileName = LEVEL_TO_FILE_MAP.get(
            getBaseLevelName(locationLogic.level_display_name)
        )
        affectedFiles.add(targetFileName)

    flushJsonFileCacheToDisk()

    # Print summary
    print("\n=== Summary ===")
    print(f"Locations updated: {updatedCount}")
    print(f"Locations skipped (ignored): {ignoredCount}")
    print(f"Locations skipped (missing section): {missingSectionCount}")
    print(f"JSON files affected: {len(affectedFiles)}")
    if DRY_RUN:
        print("[DRY RUN]: no files were written.")


#################
# Entry Point   #
#################

if __name__ == "__main__":
    DRY_RUN = False  # Set False to actually write files

    POPTRACKER_LOCATION_JSON_DIRECTORY = Path(
        "C:/Coding/Celeste-OW-Archipelago-Tracker/locations"
    )

    IGNORE_LOCATION_TYPES = [
        CelesteLocationType.BINOCULARS,
        CelesteLocationType.CAR,
        CelesteLocationType.CHECKPOINT,
        CelesteLocationType.CLUTTER,
        CelesteLocationType.GEM,
        CelesteLocationType.KEY,
        CelesteLocationType.GOLDEN_STRAWBERRY,
        CelesteLocationType.ROOM_ENTER,
    ]

    main()
