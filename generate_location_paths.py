from celeste_data_file_reader import readCelesteLevelData
from collections import defaultdict
from data.CelesteLevelData import Level, Room, RoomConnection
from MissingDataException import MissingDataException
from typing import Any, Dict, Iterator, List, Optional


def findAllPaths(
    level: Level,
    sourceRoomName: str,
    sourceRoomRegionName: str,
    destinationRoomName: str,
) -> List[Any]:
    """
    Finds all the paths through a Celeste Level between two rooms.

    :param level: Search within this level.
    :type level: object
    :param sourceRoomName: Begin the search in this room.
    :type sourceRoomName: str
    :param sourceRoomRegionName: Begin the search in this region.
    :type sourceRoomRegionName: str
    :param destinationRoomName: Description
    :type destinationRoomName: str
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
    roomConnectionPath = findPathBetweenRooms(level, sourceRoom, destinationRoom)
    return roomConnectionPath


def findPathBetweenRooms(
    level: Level, sourceRoom: Room, destinationRoom: Room
) -> List[List[RoomConnection]]:
    # Convert room connections to a graph for rapid access
    roomConnectionsGraph = defaultdict(list)
    for conn in level.room_connections:
        roomConnectionsGraph[conn.source_room].append(conn)

    return list(
        findPathFromRoomConnections(
            roomConnectionsGraph, sourceRoom.name, destinationRoom.name
        )
    )


def findPathFromRoomConnections(
    graph: Dict[str, List[RoomConnection]], start: str, destination: str
) -> Iterator[List[RoomConnection]]:
    """
    Iteratively find all paths from `start` to `destination` in a DAG of RoomConnections.
    Avoids revisiting the same room in a path to prevent loops.
    """
    # Stack stores tuples: (current_room, path_so_far, rooms_seen_so_far)
    stack: List[tuple[str, List[RoomConnection], set[str]]] = [(start, [], {start})]

    while stack:
        current, path, seen = stack.pop()

        if current == destination:
            yield path
            continue

        for conn in graph.get(current, []):
            next_room = conn.dest_room
            if next_room not in seen:  # Prevent revisiting rooms in this path
                stack.append((next_room, path + [conn], seen | {next_room}))


rawLevelData = readCelesteLevelData()
result = findAllPaths(rawLevelData.levels[1], "1", "main", "8")

print("===========")
for index, path in enumerate(result):
    print(
        f"Path {index + 1}: {
            ' | '.join(
                f'{step.source_room} {step.source_door}->{step.dest_room} {step.dest_door}'
                for step in path
            )
        }"
    )
    print("===========")
