from collections import defaultdict
from classes.MissingDataException import MissingDataException
from data.celeste_data_file_reader import readCelesteLevelData
from data.CelesteLevelData import Level, Region, Room, RoomConnection
from typing import Any, Dict, Iterator, List


def findAllPaths(
    level: Level,
    sourceRoomName: str,
    sourceRoomRegionName: str,
    destinationRoomName: str,
) -> List[List[Any]]:
    """Finds all the paths through a Celeste Level between two rooms.

    Args:
        level (Level): Search within this level.
        sourceRoomName (str): Start at this room.
        sourceRoomRegionName (str): Start at this region in the source room.
        destinationRoomName (str): End at this room.

    Raises:
        MissingDataException: _description_
        MissingDataException: _description_
        MissingDataException: _description_
        MissingDataException: _description_

    Returns:
        List[Any]: A list containing all paths (as lists of rooms and regions) between source and destination.
    """

    if level.rooms is None or len(level.rooms) == 0:
        raise MissingDataException("Level has no defined rooms.")

    sourceRoom = next(
        (room for room in level.rooms if room.name == sourceRoomName), None
    )
    if sourceRoom is None:
        raise MissingDataException(f"Unable to find source room named {sourceRoomName}")

    sourceRegion = next(
        (
            region
            for region in sourceRoom.regions
            if region.name == sourceRoomRegionName
        ),
        None,
    )
    if sourceRegion is None:
        raise MissingDataException(
            f"Unable to find source room region named {sourceRoomName}"
        )

    destinationRoom = next(
        (room for room in level.rooms if room.name == destinationRoomName), None
    )
    if destinationRoom is None:
        raise MissingDataException(
            f"Unable to find source room named {destinationRoomName}"
        )

    print(
        f"Finding path from Room {sourceRoomName} -> {sourceRoomRegionName} to Room {destinationRoomName}."
    )
    roomConnectionPath = findRoomPathsBetweenRooms(
        level, sourceRoom.name, destinationRoom.name
    )
    return roomConnectionPath


def findRoomPathsBetweenRooms(
    level: Level, sourceRoomName: str, destinationRoomName: str
) -> List[List[RoomConnection]]:
    """Find a list of all room paths through a Celeste Level from `sourceRoomName` to `destinationRoomName`.

    Args:
        level (Level): Search within this level.
        sourceRoomName (str): Start at this room.
        destinationRoomName (str): End at this room.

    Returns:
        List[List[RoomConnection]]: A set of lists, each list representing one possible path from Source to Destination.
    """

    # Convert room connections to a graph for rapid access
    roomConnectionsGraph = defaultdict(list)
    for conn in level.room_connections:
        roomConnectionsGraph[conn.source_room].append(conn)

    # Utilize room connections as a graph to "quickly" find paths
    return list(
        findRoomPathsFromRoomConnections(
            roomConnectionsGraph, sourceRoomName, destinationRoomName
        )
    )


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


def findRegionPathsWithinRoom(
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


def printRoomPaths(paths: List[List[Any]]):
    print("===========")
    for index, path in enumerate(paths):
        print(
            f"Path {index + 1}: {
                ' | '.join(
                    f'{step.source_room} {step.source_door}->{step.dest_room} {step.dest_door}'
                    for step in path
                )
            }"
        )
        print("===========")


def printRegionPathsWithLogic(paths: List[List[Region]]):
    # Path with logic per step
    for path in paths:
        currStr = ""
        for index, region in enumerate(path):
            currStr += region.name

            if index + 1 < len(path):
                nextConnection = next(
                    connection
                    for connection in region.connections
                    if connection.dest == path[index + 1].name
                )
                currStr += f" --[{', '.join('/'.join(sublist) for sublist in nextConnection.rule)}]-> "

        print(currStr)


# TODO - Remove testing code below
rawLevelData = readCelesteLevelData()
# paths = findRoomPathsBetweenRooms(rawLevelData.levels[1], "1", "8")
# printRoomPaths(paths)

regionPaths = findRegionPathsWithinRoom(
    room=rawLevelData.levels[1].rooms[5],
    sourceRegion="bottom",
    destinationRegion="top",
)
printRegionPathsWithLogic(regionPaths)
