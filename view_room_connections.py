from SourceRoom import SourceRoom
from celeste_data_file_parser import parseCelesteLevelData

rawLevelData = parseCelesteLevelData()

for level in rawLevelData.levels:
    print(f'Level: {level.display_name} ({len(level.rooms)} rooms)')

    # Load data from json connections
    connectionSourceRooms = {}
    for roomConn in level.room_connections:
        if roomConn.source_room in connectionSourceRooms:
            curr_room = connectionSourceRooms[roomConn.source_room]
            
            curr_room.next_rooms.append({
                'source_door': roomConn.source_door,
                'dest_room': roomConn.dest_room
            })
        else:
            connectionSourceRooms[roomConn.source_room] = SourceRoom(roomConn.source_room)
            curr_room = connectionSourceRooms[roomConn.source_room]

            curr_room.next_rooms = [{
                'source_door': roomConn.source_door,
                'dest_room': roomConn.dest_room
            }]

    # Output
    if (len(connectionSourceRooms) > 0):
        print('Room Flow:')
        for room_id, source in connectionSourceRooms.items():
            for room in source.next_rooms:
                print(f'  {room_id} {room['source_door']} to {room['dest_room']}')

    print('===================================')