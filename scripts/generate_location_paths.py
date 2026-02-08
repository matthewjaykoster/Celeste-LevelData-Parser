"""
Generates logical pathways through a Celeste level for every location contained within /data/CelesteLogicData.json.
"""

from collections import defaultdict, deque
import hashlib
from classes.DebugLogger import DebugLogger
from classes.MissingDataException import MissingDataException
from data.CelesteLocationData import CelesteLocationCheck, CelesteLocationCheckPath
from data.celeste_data_file_reader import readCelesteLevelData, readCelesteLocationData
from data.CelesteLevelData import CelesteLevelData, Level, Region, Room, RoomConnection
from typing import Any, Dict, Iterator, List, Optional, Tuple, TypeVar
from data.celeste_data_file_writer import writeLocationsToJsonDataFile
import time


# Constants
CELESTE_LEVEL_CONSTANTS = {
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
    "6a": {"source_room": "00", "source_region": "east"},
    "6b": {"source_room": "a-00", "source_region": "bottom"},
    "6c": {"source_room": "00", "source_region": "west"},
    "7a": {"source_room": "a-00", "source_region": "west"},
    "7aa": {"source_room": "a-00", "source_region": "west"},
    "7ab": {"source_room": "b-00", "source_region": "bottom"},
    "7ac": {"source_room": "c-00", "source_region": "west"},
    "7ad": {"source_room": "d-00", "source_region": "bottom"},
    "7ae": {"source_room": "e-00b", "source_region": "bottom"},
    "7af": {"source_room": "f-00", "source_region": "south"},
    "7ag": {"source_room": "g-00", "source_region": "bottom"},
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
T = TypeVar("T")

# Globals
SCRIPT_OPTIONS = {"shouldSaveToFile": True}

# Simple in-memory JSON caches
LEVEL_CACHE = {}
ROOM_CACHE = {}

# DFS helpers
MAX_ROOM_VISITS = 2
REACHABLE_ROOMS_CACHE: dict[tuple[str, str], set[str]] = {}
REVERSE_ROOM_GRAPH_CACHE: dict[str, defaultdict[str, list[str]]] = {}
ROOM_CONNECTION_GRAPH_CACHE: dict[str, defaultdict[str, list[RoomConnection]]] = {}
ROOM_REGION_PATH_CACHE = {}
SUBLEVEL_ENTRY_EXIT_7A: Dict[str, Tuple[str, str]] = {
    "a": ("a-00", "b-00"),  # a-06 connects to b-00
    "b": ("b-00", "c-00"),  # b-09 connects to c-00
    "c": ("c-00", "d-00"),  # c-09 connects to d-00
    "d": ("d-00", "e-00b"),  # d-11 connects to e-00b
    "e": ("e-00b", "f-00"),  # e-13 connects to f-00
    "f": ("f-00", "g-00"),  # f-11 connects to g-00
    "g": ("g-00", "g-03"),  # g-03 is the final exit
}
SUBLEVEL_ROOM_PATH_CACHE_7A: Dict[str, List[List[RoomConnection]]] = {}


def buildConnectionGraphForLevel(
    level: Level,
) -> defaultdict[str, List[RoomConnection]]:
    """Convert room connections within a level to a graph for rapid access

    Args:
        level (Level): The Celeste Level
    """
    roomConnectionsGraph = defaultdict(list)
    for conn in level.room_connections:
        roomConnectionsGraph[conn.source_room].append(conn)
    return roomConnectionsGraph


def buildReverseConnectionGraph(
    roomConnectionsGraph: defaultdict[str, List[RoomConnection]],
) -> defaultdict[str, List[str]]:
    """Build a "reverse room" graph for a given level (e.g. dest -> src instead of forward).

    Args:
        roomConnectionsGraph (defaultdict[str, List[RoomConnection]]): The forward-looking graph (see buildConnectionGraphForLevel(...))
    """
    reverseGraph: Dict[str, List[str]] = defaultdict(list)
    for src, conns in roomConnectionsGraph.items():
        for conn in conns:
            reverseGraph[conn.dest_room].append(src)
    return reverseGraph


def calculateReachableRoomsForDestination(
    destinationRoomName: str, reverseGraph: defaultdict[str, List[str]]
) -> set[str]:
    """Determines which rooms can possibly reach a given destination via Breadth First Search.

    Args:
        destinationRoomName (str): The destination to reach.
        reverseGraph (defaultdict[str, List[str]]): A reverse connection graph for a level (see buildReverseConnectionGraph())

    Returns:
        _type_: _description_
    """
    reachableRoomsForDestination: set[str] = set()
    queue = [destinationRoomName]
    while queue:
        room = queue.pop()
        if room in reachableRoomsForDestination:
            continue
        reachableRoomsForDestination.add(room)
        for prevRoom in reverseGraph.get(room, []):
            queue.append(prevRoom)
    return reachableRoomsForDestination


def cullLogicallyEquivalentPaths(
    paths: list[CelesteLocationCheckPath],
) -> list[CelesteLocationCheckPath]:
    """Remove logically equivalent CelesteLocationCheckPaths to reduce combinatorial explosion."""
    seenFingerprints = set()
    uniquePaths = []

    for path in paths:
        fp = getCullFingerPrint(path)
        if fp not in seenFingerprints:
            seenFingerprints.add(fp)
            uniquePaths.append(path)

    return uniquePaths


def findAllPaths(
    level: Level,
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str,
) -> List[CelesteLocationCheckPath]:
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
        List[List[CelestePathRegionNode]]: A list containing all paths (as lists of regions) between source and destination.
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
    roomConnectionPaths = findFullRoomPaths(
        level,
        sourceRoomName,
        sourceRegionName,
        destinationRoomName,
        destinationRegionName,
    )

    return findFullRegionPaths(
        level,
        sourceRegionName,
        destinationRegionName,
        destinationRoom,
        roomConnectionPaths,
    )


def findFullRegionPaths(
    level: Level,
    sourceRegionName: str,
    destinationRegionName: str,
    destinationRoom: Room,
    roomConnectionPaths: List[List[RoomConnection]],
) -> List[CelesteLocationCheckPath]:
    """Finds all the paths through a Celeste Level between two rooms as a series of regions.

    Args:
        level (Level): Search within this level.
        sourceRegionName (str): Start at this region in first Room Connection.
        destinationRoom (str): End at this room.
        roomConnectionPaths (List[List[RoomConnection]]): A list of room connection lists which define room-based paths through the level.

    Raises:
        ValueError: Raised if path through a room without a valid path is found.

    Returns:
        List[List[CelestePathRegionNode]]: A list containing all paths (as lists of regions) between source and destination.
    """

    allLocationPaths: List[CelesteLocationCheckPath] = []

    for roomConnPath in roomConnectionPaths:
        fullLocationPaths: List[CelesteLocationCheckPath] = []

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
            if currSourceRegionName == currTargetRegionName:
                # If we're already at our current destination, don't waste time calculating anything.
                continue

            regionPathsThroughRoom = getRegionPathsThroughRoom(
                level,
                roomConn.source_room,
                currSourceRegionName,
                currTargetRegionName,
            )

            # These SHOULD get thrown out during the room pathfinding. This is just a sanity check.
            if len(regionPathsThroughRoom) == 0:
                raise ValueError(
                    f"Failed to find path through room: {getRegionPathsCacheKey(level, roomConn.source_room, currSourceRegionName, currTargetRegionName)}"
                )

            roomLocationPaths = _convertRegionPathsToLocationCheckPathsWithinRoom(
                regionPathsThroughRoom, roomConn.source_room
            )

            # Nasty combinatorial
            fullLocationPaths = _combineLocationCheckPaths(
                fullLocationPaths, roomLocationPaths
            )

        # Find paths from destination room entry door to final region (so long as we actually need to)
        finalRoomConnection = _safeListGet(roomConnPath, len(roomConnPath) - 1)
        finalSourceRegionName = (
            finalRoomConnection.dest_door if finalRoomConnection else sourceRegionName
        )
        if finalSourceRegionName != destinationRegionName:
            destinationRegionPaths = findRegionPathsThroughRoom(
                destinationRoom,
                finalSourceRegionName,
                destinationRegionName,
            )
            destinationLocationPaths = (
                _convertRegionPathsToLocationCheckPathsWithinRoom(
                    destinationRegionPaths, destinationRoom.name
                )
            )

            fullLocationPaths = _combineLocationCheckPaths(
                fullLocationPaths, destinationLocationPaths
            )

        allLocationPaths.extend(fullLocationPaths)

        # This takes a LONG time but reduces the file size to something managable.
        # Only do this when saving because memory can handle quite a lot.
        if SCRIPT_OPTIONS["shouldSaveToFile"]:
            allLocationPaths = cullLogicallyEquivalentPaths(allLocationPaths)

    return allLocationPaths


def findRegionPathsThroughRoom(
    room: Room,
    sourceRegion: str,
    destinationRegion: str,
) -> List[List[Region]]:
    """Iteratively find all paths from `sourceRegion` to `destinationRegion` in a DAG of Regions within a room.
    Avoids revisiting the same room in a path to prevent loops. Avoids paths where the only rule is "cannot_access".

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
        # Avoid connections where all rules contain "cannot_access"
        validConnections = [
            connection
            for connection in region.connections
            if len(connection.rule) == 0
            or any("cannot_access" not in rule for rule in connection.rule)
        ]
        for connection in validConnections:
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


def findRoomConnectionPaths(
    level: Level,
    graph: Dict[str, List[RoomConnection]],
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str = "",
) -> List[List[RoomConnection]]:
    """Find all paths from sourceRoomName to destinationRoomName using DFS.

    Rooms may be revisited up to MAX_ROOM_VISITS times via different connections.

    Args:
        level (Level): Current level
        graph (Dict[str, List[RoomConnection]]): Maps room names to outgoing RoomConnections.
        sourceRoomName (str): Start room.
        sourceRegionName (str): Start region.
        destinationRoomName (str): Destination room.
        destinationRegionName (str): Destination region in final room.

    Returns:
        List[List[RoomConnection]]: A path from source to destination.
    """
    if sourceRoomName == destinationRoomName:
        return []

    roomsWhichCanReachDestination = getReachableRoomsForDestination(
        level, destinationRoomName
    )

    # DFS stack: (currentRoom, pathSoFar, roomVisitCounts)
    stack: list[tuple[str, list[RoomConnection], dict[str, int]]] = [
        (sourceRoomName, [], defaultdict(int))
    ]

    result = []
    while stack:
        currentRoom, pathSoFar, roomVisitCounts = stack.pop()

        # Increment visit count
        roomVisitCounts[currentRoom] += 1

        # Enforce max room visits
        if roomVisitCounts[currentRoom] > MAX_ROOM_VISITS:
            continue

        # Stop if this room cannot reach destination
        if currentRoom not in roomsWhichCanReachDestination:
            continue

        # Yield path if we've reached the destination
        if currentRoom == destinationRoomName:
            if destinationRegionName == "":
                result.append(pathSoFar)
            else:
                finalSourceRegionName = pathSoFar[-1].dest_door
                if (
                    finalSourceRegionName == destinationRegionName
                    or hasValidRegionPathToDestination(
                        level, currentRoom, finalSourceRegionName, destinationRegionName
                    )
                ):
                    result.append(pathSoFar)

            # Avoid a "continue" statement here since we may have to pass through a destination
            # room and later return via a differnet connection.

        for conn in graph.get(currentRoom, []):
            nextRoom = conn.dest_room

            # If we can, validate that the room can be traversed to the connection via its regions.
            # This gets cached, so re-using it later is memory expensive, not compute expensive.
            currSourceRegionName: str
            if len(pathSoFar) > 0:
                currSourceRegionName = pathSoFar[-1].dest_door
            else:
                currSourceRegionName = sourceRegionName

            if hasValidRegionPathToDestination(
                level, currentRoom, currSourceRegionName, conn.source_door
            ):
                # Copy visit counts for each path extension
                stack.append((nextRoom, pathSoFar + [conn], roomVisitCounts.copy()))
            else:
                # Calling this out deliberately. Ignore if no valid region paths exist.
                pass

    return result


def findRoomConnectionPaths7a(
    level: Level, graph: Dict[str, List[RoomConnection]], destinationRoomName: str
) -> List[List[RoomConnection]]:
    """
    Compute all valid room paths through 7a from sublevel 'a' up to the sublevel
    containing the destinationRoomName. Each sublevel is traversed independently.

    Args:
        level (Level): Current Level
        graph: Full room graph for level 7a
        destinationRoomName: Stop traversal at the sublevel containing this room

    Yields:
        List[RoomConnection]: Full path from 7a start to destinationRoomName
    """

    sublevels = ["a", "b", "c", "d", "e", "f", "g"]
    destSublevel = destinationRoomName.split("-")[0]

    # Only traverse sublevels up to the destination sublevel
    sublevelsToTraverse = []
    for s in sublevels:
        sublevelsToTraverse.append(s)
        if s == destSublevel:
            break

    allPaths: List[List[RoomConnection]] = [[]]

    for sublevelId in sublevelsToTraverse:
        # If this is the sublevel containing the destination room, end there
        sublevelSourceRoom, sublevelExitRoom = SUBLEVEL_ENTRY_EXIT_7A[sublevelId]
        sublevelDestRoom = (
            destinationRoomName if sublevelId == destSublevel else sublevelExitRoom
        )

        newPaths: List[List[RoomConnection]] = []
        sublevelGraph = {
            k: v for k, v in graph.items() if k.startswith(sublevelId)
        }  # Only inform the sublevel algorithm about its own rooms
        for pathPrefix in allPaths:
            for subPath in findRoomPathsWithin7aSublevel(
                level, sublevelGraph, sublevelSourceRoom, sublevelDestRoom, sublevelId
            ):
                newPaths.append(pathPrefix + subPath)

        allPaths = newPaths

    return allPaths


def findRoomPathsWithin7aSublevel(
    level: Level,
    graph: Dict[str, List[RoomConnection]],
    sourceRoomName: str,
    destinationRoomName: str,
    sublevelId: str,
) -> List[List[RoomConnection]]:
    """
    Find all room paths within a 7a sublevel between two rooms.

    Optimized with:
    - Precomputed sublevel entry/exit rooms
    - Max room visits to avoid infinite loops
    - Cached paths per sublevel

    Args:
        level (Level): Current Level
        graph (Dict[str, List[RoomConnection]]): Forward graph of RoomConnections
        sourceRoomName (str): Start room within the sublevel
        destinationRoomName (str): End room within the sublevel
        sublevelLetter (str): The letter of the sublevel (a-g)

    Yields:
        List[RoomConnection]: A valid path from sourceRoomName to destinationRoomName
    """
    entryRoom, exitRoom = SUBLEVEL_ENTRY_EXIT_7A[sublevelId]
    computeFullSublevel = (
        sourceRoomName == entryRoom and destinationRoomName == exitRoom
    )

    entryRegion = CELESTE_LEVEL_CONSTANTS[f"{level.name}{sublevelId}"]["source_region"]
    if computeFullSublevel and sublevelId in SUBLEVEL_ROOM_PATH_CACHE_7A:
        pathsFound = SUBLEVEL_ROOM_PATH_CACHE_7A[sublevelId]
    elif computeFullSublevel:
        pathsFound = findRoomConnectionPaths(
            level, graph, entryRoom, entryRegion, exitRoom
        )
        SUBLEVEL_ROOM_PATH_CACHE_7A[sublevelId] = pathsFound
    else:
        pathsFound = findRoomConnectionPaths(
            level, graph, entryRoom, entryRegion, destinationRoomName
        )

    return pathsFound


def findFullRoomPaths(
    level: Level,
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str = "",
) -> List[List[RoomConnection]]:
    """Find a list of all room paths through a Celeste Level between two rooms.

    Args:
        level (Level): Search within this level.
        sourceRoomName (str): Start at this room.
        sourceRegionName (str): Start at this region
        destinationRoomName (str): End at this room.
        destinationRegionName (str): The final region destination in the final room.

    Returns:
        List[List[RoomConnection]]: A set of lists, each list representing one possible path through Rooms from Source to Destination.
    """

    if sourceRoomName == destinationRoomName:
        return []  # Note: This is incorrect if we ever need to loop back to the origin. I don't believe this happens.

    roomConnectionsGraph = getConnectionGraphForLevel(level)

    potentialRoomPaths: List[List[RoomConnection]]
    if level.name == "7a":
        # Because 7a is a special baby boy WITH TOO MANY DAMN ROOMS
        potentialRoomPaths = findRoomConnectionPaths7a(
            level, roomConnectionsGraph, destinationRoomName
        )
    else:
        potentialRoomPaths = findRoomConnectionPaths(
            level,
            roomConnectionsGraph,
            sourceRoomName,
            sourceRegionName,
            destinationRoomName,
            destinationRegionName,
        )

    return potentialRoomPaths


def getConnectionGraphForLevel(level: Level) -> defaultdict[str, list[RoomConnection]]:
    """Return the forward graph for a level, caching by level.name."""
    if level.name not in ROOM_CONNECTION_GRAPH_CACHE:
        ROOM_CONNECTION_GRAPH_CACHE[level.name] = buildConnectionGraphForLevel(level)
    return ROOM_CONNECTION_GRAPH_CACHE[level.name]


def getCullFingerPrint(path: CelesteLocationCheckPath) -> str:
    """Generate a unique hash for a CelesteLocationCheckPath for deduplication."""
    # Flatten rules into a single string (or JSON string) for hashing
    rules_str = str(path.rules)
    return hashlib.md5(rules_str.encode("utf-8")).hexdigest()


def getLevel(levelData: CelesteLevelData, levelName: str) -> Level:
    level = LEVEL_CACHE.get(levelName)
    if level is None:
        level = next(level for level in levelData.levels if level.name == levelName)
        LEVEL_CACHE[levelName] = level

    return level


def getReachableRoomsForDestination(level: Level, destinationRoomName: str) -> set[str]:
    """Return all roomsw which can reach a destination, caching by (level.name, destinationRoomName)."""
    cacheKey = (level.name, destinationRoomName)
    if cacheKey not in REACHABLE_ROOMS_CACHE:
        reverseGraph = getReverseGraphForLevel(level)
        REACHABLE_ROOMS_CACHE[cacheKey] = calculateReachableRoomsForDestination(
            destinationRoomName, reverseGraph
        )
    return REACHABLE_ROOMS_CACHE[cacheKey]


def getRegionPathsCacheKey(
    level: Level, roomName: str, sourceRegionName, targetRegionName
) -> str:
    return f"{level.name}_{roomName}-{sourceRegionName}-{targetRegionName}"


def getRegionPathsThroughRoom(
    level: Level, roomName: str, sourceRegionName: str, targetRegionName: str
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
    regionPathsThroughRoom: Optional[List[List[Region]]] = ROOM_REGION_PATH_CACHE.get(
        roomPathCacheKey
    )
    if regionPathsThroughRoom is None:
        currRoom = getRoom(level, roomName)

        regionPathsThroughRoom = findRegionPathsThroughRoom(
            currRoom, sourceRegionName, targetRegionName
        )

        ROOM_REGION_PATH_CACHE[roomPathCacheKey] = regionPathsThroughRoom

    return regionPathsThroughRoom


def getReverseGraphForLevel(level: Level) -> defaultdict[str, list[str]]:
    """Return the reverse graph for a level, caching by level.name."""
    if level.name not in REVERSE_ROOM_GRAPH_CACHE:
        forwardGraph = getConnectionGraphForLevel(level)
        REVERSE_ROOM_GRAPH_CACHE[level.name] = buildReverseConnectionGraph(forwardGraph)
    return REVERSE_ROOM_GRAPH_CACHE[level.name]


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


def hasValidRegionPathToDestination(
    level: Level, roomName: str, sourceRegion: str, destinationRegion: str
) -> bool:
    """Determines whether or not a region path through a particular room exists.

    Args:
        level (Level): Current Level
        roomName (str): Current Room
        sourceRegion (str): Start from this region
        destinationRegion (str): End at this region

    Returns:
        bool: True, if a region path exists. False otherwise.
    """
    return (
        len(getRegionPathsThroughRoom(level, roomName, sourceRegion, destinationRegion))
        > 0
    )


def _combineLocationCheckPaths(
    sourceCheckPaths: List[CelesteLocationCheckPath],
    targetCheckPaths: List[CelesteLocationCheckPath],
) -> List[CelesteLocationCheckPath]:
    """Combines two location check paths. If source is empty, returns a copy of target.
    Conceptually, this is a Cartesian product* between the two inputs.

    Args:
        sourceRegionPaths (List[CelesteLocationCheckPath]): The source list of location check paths.
        targetRegionPaths (List[CelesteLocationCheckPath]): The target list of location check paths.

    Returns:
        List[CelesteLocationCheckPath]: A list of combined region paths, or a copy of target, if source
        does not exist.
    """
    if not sourceCheckPaths:
        return targetCheckPaths

    combinedPaths: List[CelesteLocationCheckPath] = []
    for sourcePath in sourceCheckPaths:
        for targetPath in targetCheckPaths:
            combinedPaths.append(
                CelesteLocationCheckPath(
                    regions=sourcePath.regions + targetPath.regions,
                    rules=sourcePath.rules + targetPath.rules,
                )
            )

    return combinedPaths


def _convertRegionPathsToLocationCheckPathsWithinRoom(
    regionPaths: List[List[Region]],
    roomName: str,
) -> List[CelesteLocationCheckPath]:
    """Converts Region Paths into Location Check Paths within a single room.

    Args:
        regionPaths (List[List[Region]]): Region Path
        roomName (str): Room in which all regions in the path reside.

    Returns:
        List[CelesteLocationCheckPath]: One CelesteLocationCheckPath per list of Regions.
    """
    checkPaths = []
    for path in regionPaths:
        regions: List[str] = []
        rules: List[List[List[str]]] = []
        for i, currentRegion in enumerate(path):
            regions.append(f"{roomName}_{currentRegion.name}")

            if i + 1 < len(path):
                nextRegion = path[i + 1]
                rule = currentRegion.ruleByDest.get(nextRegion.name, [])
                if rule:
                    rules.append(rule)

        checkPaths.append(CelesteLocationCheckPath(regions, rules))

    return checkPaths


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
def generateLocationChecks(shouldSaveToFile: bool) -> List[CelesteLocationCheck]:
    SCRIPT_OPTIONS["shouldSaveToFile"] = shouldSaveToFile
    # NOTE: Close CelesteLocationData.json before running this otherwise the update will be SLOOOOOOOOW.

    rawCelesteLevelData = readCelesteLevelData()
    rawCelesteLocationData = readCelesteLocationData()
    locations = rawCelesteLocationData.locations

    # [TEST/DEBUG] Leave for testing/debugging purposes
    # locations = list(
    #     location
    #     for location in rawCelesteLocationData.locations
    #     if location.level_name == "1a"
    #     and location.room_name == "5"
    #     and location.region_name == "north-west"
    # )

    # Known logic issues:
    # Celestial Resort - Roof - all checks aren't respecting NOT keysantity
    # Core A - car
    # Core B - all checkpoints and level clear
    # Summit A - all checkpoints, crystal heart has some incorrect logic (for at least non-gemsanity)

    startTime = time.perf_counter()
    lastCheckpointTime = startTime

    for index, location in enumerate(locations):
        level = getLevel(rawCelesteLevelData, location.level_name)
        locations[index].region_paths_to_location = findAllPaths(
            level,
            CELESTE_LEVEL_CONSTANTS[level.name]["source_room"],
            CELESTE_LEVEL_CONSTANTS[level.name]["source_region"],
            location.room_name,
            location.region_name,
        )

        # Progress + timing every level change
        prevLevel = _safeListGet(locations, index - 1)
        if prevLevel is None:
            DebugLogger.logDebug(
                f"Starting location calculations for level {level.name}."
            )
        elif level.name != prevLevel.level_name:
            now = time.perf_counter()
            elapsedTotal = now - startTime
            elapsedSinceLast = now - lastCheckpointTime
            lastCheckpointTime = now

            DebugLogger.logDebug(
                f"Calculated paths for {index + 1} locations | "
                f"+{elapsedSinceLast:.1f}s | total {elapsedTotal:.1f}s"
            )

            DebugLogger.logDebug(
                f"Starting location calculations for level {level.name}."
            )

    endTime = time.perf_counter()
    DebugLogger.logDebug(
        f"Finished path calculation for {len(locations)} locations in "
        f"{endTime - startTime:.1f} seconds."
    )

    if shouldSaveToFile:
        DebugLogger.logDebug(f"Saving {len(locations)} to disk.")
        writeLocationsToJsonDataFile(locations)
    else:
        DebugLogger.logDebug(f"Skipping location file write to disk.")

    return locations
