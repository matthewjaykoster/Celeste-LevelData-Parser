from data.CelesteLevelData import RoomConnection
from data.celeste_data_file_reader import readCelesteLevelData


rawCelesteLocationData = readCelesteLevelData()


def reverseConnKey(conn: RoomConnection) -> tuple[str, str, str, str]:
    return (conn.dest_room, conn.dest_door, conn.source_room, conn.source_door)


for level in rawCelesteLocationData.levels:
    for roomConn in level.room_connections:
        for roomConnMatch in level.room_connections:
            if roomConn.connKey() == roomConnMatch.connKey():
                continue

            if roomConn.connKey() == reverseConnKey(roomConnMatch):
                print(
                    f"Level {level.name} has a reversable connection: {roomConn.connKey()}"
                )
