"""
Generates logical pathways through a Celeste level for every location contained within /data/CelesteLogicData.json.
"""

from collections import defaultdict, deque
from classes.DebugLogger import DebugLogger
from classes.MissingDataException import MissingDataException
from data.CelesteLocationData import (
    CelesteLocationCheckPath,
    CelesteLocationCheckPathRegion,
    CelestePathRegionNode,
)
from data.celeste_data_file_reader import readCelesteLevelData, readCelesteLocationData
from data.CelesteLevelData import CelesteLevelData, Level, Region, Room, RoomConnection
from typing import Any, Dict, Iterator, List, Optional, Tuple, TypeVar
from data.celeste_data_file_writer import writeLocationsToJsonDataFile
import time

T = TypeVar("T")


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

# Measured max path lengths from a previous algorithm - needed to prune room graph
CELESTE_LEVEL_MAX_PATH_LENGTHS = {
    "0a": 11,
    "1a": 53,
    "1b": 32,
    "1c": 6,
    "2a": 54,
    "2b": 34,
    "2c": 6,
    "3a": 45,
    "3b": 46,
    "3c": 6,
    "4a": 74,
    "4b": 40,
    "4c": 6,
    "5a": 70,
    "5b": 43,
    "5c": 6,
    "6b": 56,
    "6c": 6,
    "7a": 153,
    "7b": 56,
    "7c": 6,
    "9a": 61,
    "9c": 8,
    "10a": 78,
    "10b": 118,
}
ROOM_PATH_LENGTH_BUFFER_MULTIPLIER = 1.5
MIN_MAX_PATH_LENGTH = 10

# Simple in-memory JSON caches
LEVEL_CACHE = {}
ROOM_CACHE = {}

# Caches to help DFS move more quickly
REACHABLE_ROOMS_CACHE: dict[tuple[str, str], set[str]] = {}
REVERSE_ROOM_GRAPH_CACHE: dict[str, defaultdict[str, list[str]]] = {}
ROOM_CONNECTION_GRAPH_CACHE: dict[str, defaultdict[str, list[RoomConnection]]] = {}
ROOM_CONNECTION_PATH_CACHE = {}
SUBLEVEL_ENTRY_EXIT_7A: Dict[str, Tuple[str, str]] = {
    "a": ("a-00", "a-06"),  # a-06 connects to b-00
    "b": ("b-00", "b-09"),  # b-09 connects to c-00
    "c": ("c-00", "c-09"),  # c-09 connects to d-00
    "d": ("d-00", "d-11"),  # d-11 connects to e-00b
    "e": ("e-00", "e-13"),  # e-13 connects to f-00
    "f": ("f-00", "f-11"),  # f-11 connects to g-00
    "g": ("g-00", "g-03"),  # g-03 is the final exit
}
SUBLEVEL_PATH_CACHE_7A: Dict[str, List[List["RoomConnection"]]] = {}


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


def findAllPaths(
    level: Level,
    sourceRoomName: str,
    sourceRegionName: str,
    destinationRoomName: str,
    destinationRegionName: str,
) -> List[List[CelestePathRegionNode]]:
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

    allRegionPaths: List[List[CelestePathRegionNode]] = []

    for roomConnPath in roomConnectionPaths:
        fullRegionPaths: List[List[CelestePathRegionNode]] = []

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
                level,
                roomConn.source_room,
                currSourceRegionName,
                currTargetRegionName,
            )
            regionNodePathsThroughRoom = _convertRegionPathsToRegionNodesWithinRoom(
                regionPathsThroughRoom, roomConn.source_room
            )

            if len(regionPathsThroughRoom) == 0:
                # These SHOULD get thrown out during the room pathfinding.
                raise ValueError(
                    f"Failed to find path through room: {getRegionPathsCacheKey(level, roomConn.source_room, currSourceRegionName, currTargetRegionName)}"
                )

            # Nasty combinatorial
            fullRegionPaths = _combineRegionNodePaths(
                fullRegionPaths, regionNodePathsThroughRoom
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
            destinationRegionNodesPathsThroughRoom = (
                _convertRegionPathsToRegionNodesWithinRoom(
                    destinationRegionPaths, destinationRoom.name
                )
            )

            fullRegionPaths = _combineRegionNodePaths(
                fullRegionPaths, destinationRegionNodesPathsThroughRoom
            )

        allRegionPaths.extend(fullRegionPaths)

    return allRegionPaths


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


def findRoomPathsFromRoomConnections(
    graph: Dict[str, List[RoomConnection]],
    reachableRoomsForDestination: set[str],
    sourceRoomName: str,
    destinationRoomName: str,
    maxRoomVisits: int = 2,  # optional: limit re-entries into the same room
) -> Iterator[List[RoomConnection]]:
    """Find all paths from sourceRoomName to destinationRoomName using DFS.
    Optimized with destination reachability and max room visits.
    Rooms may be revisited up to maxRoomVisits times via different connections.

    Args:
        graph (Dict[str, List[RoomConnection]]): Maps room names to outgoing RoomConnections.
        reachableRoomsForDestination (set[str]): The set of rooms which can possibly reach the destination.
        sourceRoomName (str): Start room.
        destinationRoomName (str): Destination room.
        maxRoomVisits (int): How many times a room may be visited in the same path.

    Yields:
        List[RoomConnection]: A path from source to destination.
    """

    # DFS stack: (currentRoom, pathSoFar, roomVisitCounts)
    stack: list[tuple[str, list[RoomConnection], dict[str, int]]] = [
        (sourceRoomName, [], defaultdict(int))
    ]

    while stack:
        currentRoom, pathSoFar, roomVisitCounts = stack.pop()

        # Increment visit count
        roomVisitCounts[currentRoom] += 1

        # Enforce max room visits
        if roomVisitCounts[currentRoom] > maxRoomVisits:
            continue

        # Stop if this room cannot reach destination
        if currentRoom not in reachableRoomsForDestination:
            continue

        # Yield path if we've reached the destination
        if currentRoom == destinationRoomName:
            yield pathSoFar
            # Keep searching for alternative paths

        for conn in graph.get(currentRoom, []):
            nextRoom = conn.dest_room
            # Copy visit counts for each path extension
            newVisitCounts = roomVisitCounts.copy()
            stack.append((nextRoom, pathSoFar + [conn], newVisitCounts))


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
        return []  # Note: This is incorrect if we ever need to loop back to the origin. I don't believe this happens.

    # These get calculated for every location, so cache what we can
    roomConnectionsGraph = getConnectionGraphForLevel(level)

    if level.name == "7a":
        # Because 7a is a special baby boy WITH TOO MANY DAMN ROOMS
        potentialRoomPaths = list(
            findRoomPathsThrough7a(roomConnectionsGraph, destinationRoomName)
        )
    else:
        reachableRoomsForDestination = getReachableRoomsForDestination(
            level, destinationRoomName
        )

        potentialRoomPaths = list(
            findRoomPathsFromRoomConnections(
                roomConnectionsGraph,
                reachableRoomsForDestination,
                sourceRoomName,
                destinationRoomName,
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


def findRoomPathsThrough7a(
    graph: Dict[str, List["RoomConnection"]],
    destinationRoomName: str,
    maxRoomVisits: int = 2,
) -> Iterator[List["RoomConnection"]]:
    """
    Compute all valid room paths through 7a from sublevel 'a' up to the sublevel
    containing the destinationRoomName. Each sublevel is traversed independently.

    Args:
        graph: Full room graph for level 7a
        destinationRoomName: Stop traversal at the sublevel containing this room
        maxRoomVisits: Max room visits for each DFS

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

    pathsSoFar: List[List["RoomConnection"]] = [[]]

    for sublevel in sublevelsToTraverse:
        entryRoom, exitRoom = SUBLEVEL_ENTRY_EXIT_7A[sublevel]
        # If this is the sublevel containing the destination room, end there
        sublevelDestRoom = destinationRoomName if sublevel == destSublevel else exitRoom

        newPaths: List[List["RoomConnection"]] = []
        for pathPrefix in pathsSoFar:
            for subPath in findRoomPathsWithin7aSublevel(
                graph, entryRoom, sublevelDestRoom, sublevel, maxRoomVisits
            ):
                newPaths.append(pathPrefix + subPath)

        pathsSoFar = newPaths

    for fullPath in pathsSoFar:
        yield fullPath


def findRoomPathsWithin7aSublevel(
    graph: Dict[str, List[RoomConnection]],
    sourceRoomName: str,
    destinationRoomName: str,
    sublevelLetter: str,
    maxRoomVisits: int = 2,
) -> Iterator[List[RoomConnection]]:
    """
    Find all room paths within a 7a sublevel between two rooms.

    Optimized with:
    - Precomputed sublevel entry/exit rooms
    - Max room visits to avoid infinite loops
    - Cached paths per sublevel

    Args:
        graph (Dict[str, List[RoomConnection]]): Forward graph of RoomConnections
        sourceRoomName (str): Start room within the sublevel
        destinationRoomName (str): End room within the sublevel
        sublevelLetter (str): The letter of the sublevel (a-g)
        maxRoomVisits (int): How many times a room may be revisited in a single path

    Yields:
        List[RoomConnection]: A valid path from sourceRoomName to destinationRoomName
    """

    # If computing all paths for the entire sublevel, check cache
    entryRoom, exitRoom = SUBLEVEL_ENTRY_EXIT_7A[sublevelLetter]
    computeFullSublevel = (
        sourceRoomName == entryRoom and destinationRoomName == exitRoom
    )

    if computeFullSublevel and sublevelLetter in SUBLEVEL_PATH_CACHE_7A:
        for path in SUBLEVEL_PATH_CACHE_7A[sublevelLetter]:
            yield path
        return

    # DFS stack: (currentRoom, pathSoFar, roomVisitCounts)
    stack: List[Tuple[str, List["RoomConnection"], Dict[str, int]]] = [
        (sourceRoomName, [], defaultdict(int))
    ]
    pathsFound: List[List["RoomConnection"]] = []

    while stack:
        currentRoom, pathSoFar, roomVisitCounts = stack.pop()

        # Increment visit count
        roomVisitCounts[currentRoom] += 1
        if roomVisitCounts[currentRoom] > maxRoomVisits:
            continue

        # Yield path if we've reached the destination
        if currentRoom == destinationRoomName:
            pathsFound.append(pathSoFar)
            yield pathSoFar
            continue

        # Explore outgoing connections
        for conn in graph.get(currentRoom, []):
            nextRoom = conn.dest_room
            # Enforce sublevel boundary: can't leave the current sublevel
            if not nextRoom.startswith(sublevelLetter + "-"):
                continue
            newVisitCounts = roomVisitCounts.copy()
            stack.append((nextRoom, pathSoFar + [conn], newVisitCounts))

    # Cache full sublevel paths
    if computeFullSublevel:
        SUBLEVEL_PATH_CACHE_7A[sublevelLetter] = pathsFound


def getConnectionGraphForLevel(level: Level) -> defaultdict[str, list[RoomConnection]]:
    """Return the forward graph for a level, caching by level.name."""
    if level.name not in ROOM_CONNECTION_GRAPH_CACHE:
        ROOM_CONNECTION_GRAPH_CACHE[level.name] = buildConnectionGraphForLevel(level)
    return ROOM_CONNECTION_GRAPH_CACHE[level.name]


def getLevel(levelData: CelesteLevelData, levelName: str) -> Level:
    level = LEVEL_CACHE.get(levelName)
    if level is None:
        level = next(level for level in levelData.levels if level.name == levelName)
        LEVEL_CACHE[levelName] = level

    return level


def getMaxPathLengthForLevel(levelName: str) -> int:
    """Defines the maximum allowed room path length by level (for algorithm path explosion pruning)

    Args:
        levelName (str): Celeste level name as defined in code (1a, 2b, etc)

    Returns:
        int: The max allowed room path length for that level.
    """
    base = CELESTE_LEVEL_MAX_PATH_LENGTHS.get(levelName)

    if base is None:
        # Fallback for unexpected levels
        return 250

    return max(
        MIN_MAX_PATH_LENGTH,
        int(base * ROOM_PATH_LENGTH_BUFFER_MULTIPLIER),
    )


def getReachableRoomsForDestination(level: Level, destinationRoomName: str) -> set[str]:
    """Return reachable rooms for a destination, caching by (level.name, destinationRoomName)."""
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
    regionPathsThroughRoom: Optional[List[List[Region]]] = (
        ROOM_CONNECTION_PATH_CACHE.get(roomPathCacheKey)
    )
    if regionPathsThroughRoom is None:
        currRoom = next(room for room in level.rooms if room.name == roomName)

        regionPathsThroughRoom = findRegionPathsThroughRoom(
            currRoom, sourceRegionName, targetRegionName
        )

        ROOM_CONNECTION_PATH_CACHE[roomPathCacheKey] = regionPathsThroughRoom

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


def _combineRegionNodePaths(
    fullRegionPaths: List[List[CelestePathRegionNode]],
    regionPathsThroughRoom: List[List[CelestePathRegionNode]],
) -> List[List[CelestePathRegionNode]]:
    """Combines accumulated region paths with all valid paths through a room.

    This function builds all possible combined paths by appending each
    path through the current room to each previously accumulated path.
    Conceptually, this is a Cartesian product between the two inputs.

    Args:
        fullRegionPaths (List[List[RegionNode]]): The list of region paths
            accumulated so far across previous rooms.
        regionPathsThroughRoom (List[List[RegionNode]]): All valid region paths
            through the current room.

    Returns:
        List[List[RegionNode]]: A new list of combined region paths. If
        `fullRegionPaths` is empty, this will return a copy of
        `regionPathsThroughRoom`. If `regionPathsThroughRoom` is empty,
        this will return an empty list.
    """
    if not fullRegionPaths:
        return [path.copy() for path in regionPathsThroughRoom]

    return [
        fullPath + roomPath
        for fullPath in fullRegionPaths
        for roomPath in regionPathsThroughRoom
    ]


def _convertRegionPathsToRegionNodesWithinRoom(
    regionPaths: List[List[Region]],
    roomName: str,
) -> List[List[CelestePathRegionNode]]:
    """Converts Region Paths into Region Node Paths.

    Args:
        regionPaths (List[List[Region]]): Region Path
        roomName (str): Room in which all regions in the path reside.

    Returns:
        List[List[RegionNode]]: The same list, converted to Region Nodes.
    """
    return [
        [CelestePathRegionNode(room_name=roomName, region=region) for region in path]
        for path in regionPaths
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

# NOTE: Close CelesteLocationData.json before running this otherwise the update will be SLOOOOOOOOW.

rawCelesteLevelData = readCelesteLevelData()
rawCelesteLocationData = readCelesteLocationData()
locations = rawCelesteLocationData.locations

# [TEST/DEBUG] Leave for testing/debugging purposes
# locations = list(
#     location
#     for location in rawCelesteLocationData.locations
#     if location.level_name == "3a"
#     and location.room_name == "s3"
#     and location.region_name == "north"
# )

startTime = time.perf_counter()
lastCheckpointTime = startTime

for index, location in enumerate(locations):
    level = getLevel(rawCelesteLevelData, location.level_name)
    paths: List[List[CelestePathRegionNode]] = findAllPaths(
        level,
        CELESTE_LEVEL_CONSTANTS[level.name]["source_room"],
        CELESTE_LEVEL_CONSTANTS[level.name]["source_region"],
        location.room_name,
        location.region_name,
    )

    # Convert paths into lists of minmal nodes, and then flatten those nodes into singular data structures.
    regionNodePaths: List[List[CelesteLocationCheckPathRegion]] = []
    for path in paths:
        convertedPath: List[CelesteLocationCheckPathRegion] = []
        for i in range(len(path) - 1):
            currentRegion = path[i]
            nextRegion = path[i + 1]
            node = CelesteLocationCheckPathRegion.fromCelesteRegionPathNode(
                currentRegion, nextRegion
            )
            convertedPath.append(node)

        finalNode = CelesteLocationCheckPathRegion.fromCelesteRegionPathNode(path[-1])
        convertedPath.append(finalNode)

        regionNodePaths.append(convertedPath)

    # Flatten to a smaller data structure, removing empty lists to save space
    regionPathsToLocation: List[CelesteLocationCheckPath] = []
    for regionPath in regionNodePaths:
        minimalLocationPath = CelesteLocationCheckPath(
            list(regionPath.region_name for regionPath in regionPath),
            list(
                regionPath.rule_to_next
                for regionPath in regionPath
                if len(regionPath.rule_to_next) > 0
            ),
        )
        regionPathsToLocation.append(minimalLocationPath)

    location.region_paths_to_location = regionPathsToLocation

    # Progress + timing every level change
    prevLevel = _safeListGet(locations, index - 1)
    if prevLevel is None:
        DebugLogger.logDebug(f"Starting location calculations for level {level.name}.")
    elif level.name != prevLevel.level_name:
        now = time.perf_counter()
        elapsedTotal = now - startTime
        elapsedSinceLast = now - lastCheckpointTime
        lastCheckpointTime = now

        DebugLogger.logDebug(
            f"Calculated paths for {index + 1} locations | "
            f"+{elapsedSinceLast:.1f}s | total {elapsedTotal:.1f}s"
        )

        DebugLogger.logDebug(f"Starting location calculations for level {level.name}.")

endTime = time.perf_counter()
DebugLogger.logDebug(
    f"Finished path calculation for {len(locations)} locations in "
    f"{endTime - startTime:.1f} seconds."
)

writeLocationsToJsonDataFile(locations)
