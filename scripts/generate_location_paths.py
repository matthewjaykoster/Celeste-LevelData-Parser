"""
Generates logical pathways through a Celeste level for every location contained within /data/CelesteLogicData.json.
"""

from collections import defaultdict
from classes.DebugLogger import DebugLogger
from classes.MissingDataException import MissingDataException
from data.CelesteLocationData import CelesteLocationCheckPathRegion
from data.celeste_data_file_reader import readCelesteLevelData, readCelesteLocationData
from data.CelesteLevelData import CelesteLevelData, Level, Region, Room, RoomConnection
from typing import Any, Dict, Iterator, List, Optional, TypeVar

from data.celeste_data_file_writer import writeLocationsToJsonDataFile

CELESTE_LEVEL_INITIAL_SOURCE_MAP = {
    "0a": {"source_room": "0", "source_region": "main"},
    "1a": {"source_room": "1", "source_region": "main"},
    "1b": {"source_room": "00", "source_region": "west"},
    "1c": {"source_room": "00", "source_region": "west"},
    "2a": {"source_room": "start", "source_region": "main"},
    "2b": {"source_room": "start", "source_region": "west"},
    "2c": {"source_room": "00", "source_region": "west"},
    "3a": {"source_room": "s0", "source_region": "main"},
    "3b": {"source_room": "00", "source_region": "west"},
    "3c": {"source_room": "00", "source_region": "west"},
    "4a": {"source_room": "a-00", "source_region": "west"},
    "4b": {"source_room": "a-00", "source_region": "west"},
    "4c": {"source_room": "00", "source_region": "west"},
    "5a": {"source_room": "a-00b", "source_region": "west"},
    "5b": {"source_room": "start", "source_region": "west"},
    "5c": {"source_room": "00", "source_region": "west"},
    "6a": {"source_room": "00", "source_region": "west"},
    "6b": {"source_room": "a-00", "source_region": "bottom"},
    "6c": {"source_room": "00", "source_region": "west"},
    "7a": {"source_room": "a-00", "source_region": "west"},
    "7b": {"source_room": "a-00", "source_region": "west"},
    "7c": {"source_room": "01", "source_region": "west"},
    "8a": {"source_room": "outside", "source_region": "east"},
    "9a": {"source_room": "00", "source_region": "west"},
    "9b": {"source_room": "00", "source_region": "east"},
    "9c": {"source_room": "intro", "source_region": "west"},
    "10a": {"source_room": "intro-00-past", "source_region": "west"},
    "10b": {"source_room": "f-door", "source_region": "west"},
    "10c": {"source_room": "end-golden", "source_region": "bottom"},
}

LEVEL_CACHE = {}
ROOM_CACHE = {}
ROOM_CONN_PATH_CACHE = {}

T = TypeVar("T")


def findAllPaths(
    level: Level,
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str,
) -> List[List[Region]]:
    """Finds all the paths through a Celeste Level between two rooms as a series of regions.

    Args:
        level (Level): Search within this level.
        sourceRoomName (str): Start at this room.
        sourceRegionName (str): Start at this region in the source room.
        destinationRoomName (str): End at this room.
        destinationRegionName (str): End at this region in the destination room.

    Raises:
        MissingDataException: Raised if any of the input variables have missing backing data.
        ValueError: Raised if path through a room without a valid path is found.

    Returns:
        List[Any]: A list containing all paths (as lists of rooms and regions) between source and destination.
    """

    if level.rooms is None or len(level.rooms) == 0:
        raise MissingDataException("Level has no defined rooms.")

    sourceRoom = getRoom(level, sourceRoomName)

    sourceRegion = next(
        (region for region in sourceRoom.regions if region.name == sourceRegionName),
        None,
    )
    if sourceRegion is None:
        raise MissingDataException(
            f"Unable to find source region named {sourceRoomName}"
        )

    destinationRoom = getRoom(level, destinationRoomName)

    destinationRegion = next(
        (
            region
            for region in destinationRoom.regions
            if region.name == destinationRegionName
        ),
        None,
    )
    if destinationRegion is None:
        raise MissingDataException(
            f"Unable to find destination region named {destinationRegionName}"
        )

    DebugLogger.logDebugVerbose(
        f"Finding paths from Room {sourceRoomName} -> {sourceRegionName} to Room {destinationRoomName} -> {destinationRegionName}."
    )
    roomConnectionPaths = findRoomPathsBetweenRooms(
        level,
        sourceRoomName,
        sourceRegionName,
        destinationRoomName,
        destinationRegionName,
    )

    allRegionPaths: List[List[Region]] = []

    for roomConnPath in roomConnectionPaths:
        fullRegionPaths: List[List[Region]] = []

        # Find paths within all rooms between source and destination
        for index, roomConn in enumerate(roomConnPath):
            # Figure out where we are and where we are going
            previousRoomConnection = _safeListGet(roomConnPath, index - 1)
            currSourceRegionName = (
                previousRoomConnection.dest_door
                if previousRoomConnection
                else sourceRegionName
            )
            currTargetRegionName = roomConn.source_door

            regionPathsThroughRoom = getRegionPathsThroughRoom(
                level, roomConn.source_room, currSourceRegionName, currTargetRegionName
            )

            if len(regionPathsThroughRoom) == 0:
                # These SHOULD get thrown out during the room pathfinding.
                raise ValueError(
                    f"Failed to find path through room: {getRegionPathsCacheKey(level, roomConn.source_room, currSourceRegionName, currTargetRegionName)}"
                )

            # Nasty combinatorial
            fullRegionPaths = _combineRegionPaths(
                fullRegionPaths, regionPathsThroughRoom
            )

        # Find paths from destination room entry door to final region
        finalRoomConnection = _safeListGet(roomConnPath, len(roomConnPath) - 1)
        finalSourceRegionName = (
            finalRoomConnection.dest_door if finalRoomConnection else sourceRegionName
        )
        destinationRegionPaths = findRegionPathsThroughRoom(
            destinationRoom,
            finalSourceRegionName,
            destinationRegionName,
        )
        fullRegionPaths = _combineRegionPaths(fullRegionPaths, destinationRegionPaths)

        allRegionPaths.extend(fullRegionPaths)

    return allRegionPaths


def findRegionPathsThroughRoom(
    room: Room,
    sourceRegion: str,
    destinationRegion: str,
) -> List[List[Region]]:
    """Iteratively find all paths from `sourceRegion` to `destinationRegion` in a DAG of Regions within a room.
    Avoids revisiting the same room in a path to prevent loops.

    Args:
        room (Room): Search within this room.
        sourceRegion (str): Start at this region.
        destinationRegion (str): End at this region.

    Returns:
        List[List[Region]]: A set of lists, each list representing one possible path from Source to Destination.
    """

    if sourceRegion == destinationRegion:
        return []

    # Fast lookup: region name -> Region object
    regionByName: Dict[str, Region] = {region.name: region for region in room.regions}

    # Graph: region name -> list of destination region names
    regionGraph: Dict[str, List[str]] = defaultdict(list)
    for region in room.regions:
        for connection in region.connections:
            regionGraph[region.name].append(connection.dest)

    paths: List[List[Region]] = []

    # Stack entries: (currentRegionName, pathSoFar, visitedRegions)
    stack: List[tuple[str, List[str], set[str]]] = [
        (sourceRegion, [sourceRegion], {sourceRegion})
    ]

    while stack:
        currentRegion, pathSoFar, visitedRegions = stack.pop()

        if currentRegion == destinationRegion:
            paths.append([regionByName[name] for name in pathSoFar])
            continue

        for nextRegion in regionGraph.get(currentRegion, []):
            if nextRegion not in visitedRegions:
                stack.append(
                    (
                        nextRegion,
                        pathSoFar + [nextRegion],
                        visitedRegions | {nextRegion},
                    )
                )

    return paths


def findRoomPathsFromRoomConnections(
    graph: Dict[str, List[RoomConnection]],
    sourceRoomName: str,
    destinationRoomName: str,
) -> Iterator[List[RoomConnection]]:
    """Iteratively find all paths from `sourceRoomName` to `destinationRoomName` in a DAG of RoomConnections.
    Avoids revisiting the same room in a path to prevent loops.

    Args:
        graph (Dict[str, List[RoomConnection]]): A dictionary of source room names keyed to its related connections.
        sourceRoomName (str): Start at this room.
        destinationRoomName (str): End at this room.

    Yields:
        Iterator[List[RoomConnection]]: Each room connection as it is found to meet the criteria.
    """
    # Stack stores tuples: (current_room, path_so_far, rooms_seen_so_far)
    stack: List[tuple[str, List[RoomConnection], set[str]]] = [
        (sourceRoomName, [], {sourceRoomName})
    ]

    while stack:
        current, path, seen = stack.pop()

        if current == destinationRoomName:
            yield path
            continue

        for conn in graph.get(current, []):
            next_room = conn.dest_room
            if next_room not in seen:  # Prevent revisiting rooms in this path
                stack.append((next_room, path + [conn], seen | {next_room}))


def findRoomPathsBetweenRooms(
    level: Level,
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str,
) -> List[List[RoomConnection]]:
    """Find a list of all room paths through a Celeste Level between two rooms.
    Validates the room paths along the way to ensure each room has a valid internal path to the next in the list.

    Args:
        level (Level): Search within this level.
        sourceRoomName (str): Start at this room.
        sourceRegionName (str): Start at this region in the source room.
        destinationRoomName (str): End at this room.
        destinationRegionName (str): End at this region in the destination room.

    Returns:
        List[List[RoomConnection]]: A set of lists, each list representing one possible path from Source to Destination.
    """

    if sourceRoomName == destinationRoomName:
        return []

    # Convert room connections to a graph for rapid access
    roomConnectionsGraph = defaultdict(list)
    for conn in level.room_connections:
        roomConnectionsGraph[conn.source_room].append(conn)

    potentialRoomPaths = list(
        findRoomPathsFromRoomConnections(
            roomConnectionsGraph, sourceRoomName, destinationRoomName
        )
    )

    # Validate that each pair of connections represents a room that can actually be traversed.
    # Throw out any invalid paths.
    validRoomPaths = []
    for roomPath in potentialRoomPaths:
        pathIsValid = True

        # All rooms from start to n - 1
        for index, connection in enumerate(roomPath):
            if index == 0:
                pathSourceRegionName = sourceRegionName
            else:
                pathSourceRegionName = roomPath[index - 1].dest_door

            regionPaths = getRegionPathsThroughRoom(
                level,
                connection.source_room,
                pathSourceRegionName,
                connection.source_door,
            )

            pathIsValid = len(regionPaths) > 0
            if not pathIsValid:
                DebugLogger.logDebugVerbose(
                    f"Found invalid path from Room {sourceRoomName} -> {sourceRegionName} to Room {destinationRoomName} -> {destinationRegionName}. No route through Room {connection.source_room} from {pathSourceRegionName} to {connection.source_door}."
                )
                break

        if not pathIsValid:
            continue

        # Destination room
        finalConnection = roomPath[-1]
        regionPaths = getRegionPathsThroughRoom(
            level,
            finalConnection.dest_room,
            finalConnection.dest_door,
            destinationRegionName,
        )
        if not pathIsValid:
            DebugLogger.logDebugVerbose(
                f"Found invalid path from Room {sourceRoomName} -> {sourceRegionName} to Room {destinationRoomName} -> {destinationRegionName}. No route through Room ${finalConnection.dest_room} from {finalConnection.dest_door} to {destinationRegionName}."
            )
            continue

        validRoomPaths.append(roomPath)

    return validRoomPaths


def getLevel(levelData: CelesteLevelData, levelName: str):
    level = LEVEL_CACHE.get(levelName)
    if level is None:
        level = next(level for level in levelData.levels if level.name == levelName)
        LEVEL_CACHE[levelName] = level

    return level


def getRegionPathsCacheKey(
    level: Level, roomName: str, sourceRegionName, targetRegionName
) -> str:
    return f"{level.name}_{roomName}-{sourceRegionName}-{targetRegionName}"


def getRegionPathsThroughRoom(
    level: Level, roomName: str, sourceRegionName, targetRegionName
) -> List[List[Region]]:
    """Gets all region paths through a room, using a cache if possible.

    Args:
        level (Level): The level which contains the room.
        roomName (str): The room to path through.
        sourceRegionName (_type_): _description_
        targetRegionName (_type_): _description_

    Returns:
        _type_: _description_
    """
    roomPathCacheKey = getRegionPathsCacheKey(
        level, roomName, sourceRegionName, targetRegionName
    )
    regionPathsThroughRoom: Optional[List[List[Region]]] = ROOM_CONN_PATH_CACHE.get(
        roomPathCacheKey
    )
    if regionPathsThroughRoom is None:
        currRoom = next(room for room in level.rooms if room.name == roomName)

        regionPathsThroughRoom = findRegionPathsThroughRoom(
            currRoom, sourceRegionName, targetRegionName
        )

        ROOM_CONN_PATH_CACHE[roomPathCacheKey] = regionPathsThroughRoom

    return regionPathsThroughRoom


def getRoomCacheKey(level: Level, roomName: str) -> str:
    return f"{level.name}_{roomName}"


def getRoom(level: Level, roomName: str) -> Room:
    roomCacheKey = getRoomCacheKey(level, roomName)
    room: Optional[Room] = ROOM_CACHE.get(roomCacheKey)
    if room is None:
        room = next(room for room in level.rooms if room.name == roomName)
        if room is None:
            raise MissingDataException(f"Unable to find source room named {roomName}")

        ROOM_CACHE[roomCacheKey] = room

    return ROOM_CACHE[roomCacheKey]


def printRoomPaths(paths: List[List[Any]]):
    DebugLogger.logDebug("===========")
    for index, path in enumerate(paths):
        DebugLogger.logDebug(
            f"Path {index + 1}: {
                ' | '.join(
                    f'{step.source_room} {step.source_door}->{step.dest_room} {step.dest_door}'
                    for step in path
                )
            }"
        )
        DebugLogger.logDebug("===========")


def printRegionPathsWithLogic(regionPaths: List[List[Region]]):
    """
    Prints each path of regions to the console.

    Format for each path:
    region1 --[rules]--> region2 --[rules]--> region3 ...

    Avoids repeating region names at boundaries.
    """
    for path in regionPaths:
        if not path:
            continue

        line_parts = []
        for i in range(len(path) - 1):
            current = path[i]
            next_region = path[i + 1]

            # Flatten all rules from current to next_region
            connection_rules = []
            for conn in current.connections:
                if conn.dest == next_region.name:
                    for rule_set in conn.rule:
                        connection_rules.extend(rule_set)

            # Only include current.name at the start
            if i == 0:
                segment = f"{current.name} --[{', '.join(connection_rules)}]--> {next_region.name}"
            else:
                segment = f"--[{', '.join(connection_rules)}]--> {next_region.name}"

            line_parts.append(segment)

        # Handle single-region path
        if len(path) == 1:
            print("[START] " + path[0].name)
        else:
            print("[START] " + " ".join(line_parts))


def _combineRegionPaths(
    fullRegionPaths: List[List[Region]],
    regionPathsThroughRoom: List[List[Region]],
) -> List[List[Region]]:
    if not fullRegionPaths:
        return [path.copy() for path in regionPathsThroughRoom]

    return [
        fullPath + roomPath
        for fullPath in fullRegionPaths
        for roomPath in regionPathsThroughRoom
    ]


def _safeListGet(lst: List[T], idx: int) -> Optional[T]:
    """Gets a value from a list so long as the provided index is within range.
    Note: Does not support negative index values.

    Args:
        lst (List[T]): Get from this list.
        idx (int): Get the item as the specified index.

    Returns:
        Optional[T]: The item at the index, if valid. Otherwise None.
    """

    return lst[idx] if 0 <= idx < len(lst) else None


################
# Script Logic #
################
rawCelesteLevelData = readCelesteLevelData()
rawCelesteLocationData = readCelesteLocationData()
for index, location in enumerate(rawCelesteLocationData.locations):
    level = getLevel(rawCelesteLevelData, location.level_name)
    paths = findAllPaths(
        level,
        CELESTE_LEVEL_INITIAL_SOURCE_MAP[level.name]["source_room"],
        CELESTE_LEVEL_INITIAL_SOURCE_MAP[level.name]["source_region"],
        location.room_name,
        location.region_name,
    )

    regionPathsToLocation: List[List[CelesteLocationCheckPathRegion]] = []
    for path in paths:
        convertedPath: List[CelesteLocationCheckPathRegion] = []
        for i in range(len(path) - 1):
            currentRegion = path[i]
            nextRegion = path[i + 1]
            convertedPath.append(
                CelesteLocationCheckPathRegion.fromCelesteRegionPath(
                    currentRegion, nextRegion
                )
            )

        convertedPath.append(
            CelesteLocationCheckPathRegion.fromCelesteRegionPath(path[-1])
        )

        regionPathsToLocation.append(convertedPath)

    location.region_paths_to_location = regionPathsToLocation

    if index % 50 == 0:
        DebugLogger.logDebug(f"Calculated paths for {index + 1} locations.")

writeLocationsToJsonDataFile(rawCelesteLocationData.locations)
