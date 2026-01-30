"""
Script which performs the simple task of listing all room connections contained with Celeste Level Data.
"""

from classes.SourceRoom import SourceRoom
from data.celeste_data_file_reader import readCelesteLevelData

rawLevelData = readCelesteLevelData()

for level in rawLevelData.levels:
    print(f"Level: {level.display_name} ({len(level.rooms)} rooms)")

    # Load data from json connections
    connectionSourceRooms = {}
    for roomConn in level.room_connections:
        if roomConn.source_room in connectionSourceRooms:
            curr_room = connectionSourceRooms[roomConn.source_room]

            curr_room.next_rooms.append(
                {"source_door": roomConn.source_door, "dest_room": roomConn.dest_room}
            )
        else:
            connectionSourceRooms[roomConn.source_room] = SourceRoom(
                roomConn.source_room
            )
            curr_room = connectionSourceRooms[roomConn.source_room]

            curr_room.next_rooms = [
                {"source_door": roomConn.source_door, "dest_room": roomConn.dest_room}
            ]

    # Output
    if len(connectionSourceRooms) > 0:
        print("Room Flow:")
        for room_id, source in connectionSourceRooms.items():
            for room in source.next_rooms:
                print(f"  {room_id} {room['source_door']} to {room['dest_room']}")

    print("===================================")
