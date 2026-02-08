"""
Generates logic for each pathway contained within /data/CelesteLogicData.json.
"""

from typing import List
from classes.DebugLogger import DebugLogger
from data.CelesteLocationData import CelesteLocationCheck, CelesteLocationData
from data.CelesteLogicData import LocationCheckLogic
from data.celeste_data_file_reader import readCelesteLocationData
from data.celeste_data_file_writer import writeLogicToJsonDataFile
from scripts.generate_location_paths import generateLocationChecks

KEYSANITY_DISABLED_RULE = "$KEYSANITY_IS_DISABLED"
KEY_TO_LUA_KEYCODE_MAP = {
    "Front Door Key": "celestialresorta-frontdoorkey",
    "Hallway Key 1": "celestialresorta-hallwaykey1",
    "Hallway Key 2": "celestialresorta-hallwaykey2",
    "Huge Mess Key": "celestialresorta-hugemesskey",
    "Entrance Key": "mirrortemplea-entrancekey",
    "Depths Key": "mirrortemplea-depthskey",
    "Search Key 1": "mirrortemplea-searchkey1",
    "Search Key 2": "mirrortemplea-searchkey2",
    "Central Chamber Key 1": "mirrortempleb-centralchamberkey1",
    "Central Chamber Key 2": "mirrortempleb-centralchamberkey2",
    "2500 M Key": "thesummita-2500mkey",
    "Power Source Key 1": "farewell-powersourcekey1",
    "Power Source Key 2": "farewell-powersourcekey2",
    "Power Source Key 3": "farewell-powersourcekey3",
    "Power Source Key 4": "farewell-powersourcekey4",
    "Power Source Key 5": "farewell-powersourcekey5",
}


def collapseLocationCheckPathLogic(rules: List[List[List[str]]]) -> List[List[str]]:
    """
    Collapses logical path rules by expanding AND/OR logic into
    a minimal list of AND-only rule sets.

    Args:
        rules (List[List[List[str]]]): Logical path rules.

    Returns:
        List[List[str]]: Simplified logical rule sets.
    """

    # Start with one empty path (neutral element for AND)
    collapsedPaths: List[set[str]] = [set()]

    for step in rules:
        nextPaths: List[set[str]] = []

        for existing in collapsedPaths:
            for option in step:
                merged = existing | set(option)
                nextPaths.append(merged)

        collapsedPaths = nextPaths

    # Convert back to sorted lists
    return [sorted(path) for path in collapsedPaths]


def cullRules(rules: List[List[str]]) -> List[List[str]]:
    """Culls a set of rules, removing logically invalid, duplicate, and proper subset rules.

    Args:
        rules (List[List[str]]): A list of rules. Outer list represents logical OR, inner represents logical AND.

    Returns:
        List[List[str]]: The list of rules, culled to the same logical truth in a minimal format.
    """

    # ---- Rule 1: remove invalid KEYSANITY rules ----
    filtered = [rule for rule in rules if not violatesKeysanityRule(rule)]

    # ---- Rule 2: deduplicate ----
    unique_sets = {frozenset(rule) for rule in filtered}

    # ---- Rule 3: remove proper supersets ----
    culled_sets = set(unique_sets)

    for a in unique_sets:
        for b in unique_sets:
            if a is not b and a > b:  # proper superset
                culled_sets.discard(a)
                break

    # Convert back to list-of-lists (sorted for stability/debugging)
    result = [sorted(list(s)) for s in culled_sets]
    if len(result) == 1 and len(result[0]) == 0:
        return []  # If we have an inner list with no rules, throw it out.

    return result


def handleLogicDataMapping(locations: List[CelesteLocationCheck]):
    """Remaps any logic keys which don't match the Lua codes and adds in settings
       logic where needed. Directly edits the passed object.

    Args:
        rawCelesteLocationData (CelesteLocationData): Celeste location data loaded from the file.
    """
    for location in locations:
        for regionPath in location.region_paths_to_location:
            regionPath.rules = remapLogicRules(regionPath.rules)


def remapLogicRules(
    logic: List[List[List[str]]],
) -> List[List[List[str]]]:
    """
    Remaps logic rules as needed.
        Uses KEY_TO_LUA_KEYCODE_MAP to modify key names to their related lua-mapped item names.
        Adds an OR branch for KEYSANITY being disabled when a key remap occurs.
    """

    remappedLogic: List[List[List[str]]] = []

    for step in logic:
        newStep: List[List[str]] = []
        needsKeysanityBypass = False

        for option in step:
            newOption: List[str] = []

            for rule in option:
                if rule in KEY_TO_LUA_KEYCODE_MAP:
                    newOption.append(KEY_TO_LUA_KEYCODE_MAP[rule])
                    needsKeysanityBypass = True
                else:
                    newOption.append(rule)

            newStep.append(newOption)

        if needsKeysanityBypass:
            newStep.append([KEYSANITY_DISABLED_RULE])

        remappedLogic.append(newStep)

    return remappedLogic


def violatesKeysanityRule(rule: list[str]) -> bool:
    """Determines whether an individual rule has both a key and KEYSANITY_DISABLED required.

    Args:
        rule (list[str]): The logic rule in question.

    Returns:
        bool: True, if a violation. False otherwise.
    """
    if KEYSANITY_DISABLED_RULE not in rule:
        return False

    return any("key" in r.lower() and r != KEYSANITY_DISABLED_RULE for r in rule)


################
# Script Logic #
################

# 1. Convert logic data as needed - handleLogicDataMapping
# 2. Collapse location logic down to List[List[str]]. Outer = OR, Inner = AND, then
#    combine region paths using OR logic - collapseLocationCheckPathLogic
# 3. Deduplicate logic between ORs, removing duplicates and subsets and invalid logic
#    (e.g. $KEYSANITY_IS_DISABLED + Key ANDed together) - TODO
# 4. Convert to data structure which can be saved
# 5. Save to new JSON file - celeste_data_file_writer.writeLogicToJsonDataFile

PULL_FROM_FILE = False

# 0 - Get locations
DebugLogger.logDebug("Generating logic file.")
locations: List[CelesteLocationCheck]
if PULL_FROM_FILE:
    DebugLogger.logDebug("Pulling locations from file.")
    rawCelesteLocationData = readCelesteLocationData()
    locations = rawCelesteLocationData.locations
else:
    DebugLogger.logDebug("Generating locations on the fly.")
    locations = generateLocationChecks(False)

# 1 - Map rule values as needed to prep for Lua import
DebugLogger.logDebug("Mapping logic data (needed for lua import).")
handleLogicDataMapping(locations)

locationLogic: List[LocationCheckLogic] = []
for index, location in enumerate(locations):
    allRules: List[List[str]] = []

    # 2 - Collapse "rule paths" into logical ANDs and ORs, appending multiple "rule paths" using ORs
    if len(location.region_paths_to_location) > 0:
        for regionPath in location.region_paths_to_location:
            if len(location.location_rule) > 0:
                regionPath.rules.append(location.location_rule)
            allRules = allRules + collapseLocationCheckPathLogic(regionPath.rules)
    elif len(location.location_rule) > 0:
        allRules = allRules + collapseLocationCheckPathLogic([location.location_rule])

    # 3 - Remove duplicate, proper subset, and invalid rules
    allRules = cullRules(allRules)

    # 4 - Convert to writable format
    locationLogic.append(
        LocationCheckLogic(
            location.level_display_name,
            location.room_name,
            location.location_display_name,
            location.location_type,
            allRules,
        )
    )

    if index % 10 == 0:
        DebugLogger.logDebug(f"Converted {index + 1} locations into logic format.")

# 5 - Write to file
writeLogicToJsonDataFile(locationLogic)
