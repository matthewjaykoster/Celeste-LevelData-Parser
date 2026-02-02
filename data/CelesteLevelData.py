from dataclasses import asdict, dataclass
from typing import Any, List, Optional


@dataclass
class CelesteLevelData:
    """Represents the data structure of the CelesteLevelData.json file."""

    levels: List[Level]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLevelData:
        return CelesteLevelData(
            levels=[Level.fromJsonDict(level) for level in data["levels"]]
        )


@dataclass
class Level:
    """Represents the data structure of a Level within the CelesteLevelData.json file."""

    name: str
    display_name: str
    rooms: List[Room]
    room_connections: List[RoomConnection]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Level:
        return Level(
            name=data["name"],
            display_name=data["display_name"],
            rooms=[Room.fromJsonDict(room) for room in data["rooms"]],
            room_connections=[
                RoomConnection.fromJsonDict(roomConnection)
                for roomConnection in data["room_connections"]
            ],
        )


@dataclass
class Room:
    """Represents the data structure of a Room within the CelesteLevelData.json file."""

    name: str
    regions: List[Region]
    doors: List[Door]
    checkpoint: str
    checkpoint_region: str

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Room:
        return Room(
            name=data["name"],
            regions=[Region.fromJsonDict(region) for region in data["regions"]],
            doors=[Door.fromJsonDict(door) for door in data["doors"]],
            checkpoint=data["checkpoint"],
            checkpoint_region=data["checkpoint_region"],
        )


@dataclass
class Region:
    """Represents the data structure of a Region within the CelesteLevelData.json file."""

    name: str
    connections: List[Connection]
    locations: Optional[List[Location]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Region:
        locations = data.get("locations")
        return Region(
            name=data["name"],
            connections=[
                Connection.fromJsonDict(connection)
                for connection in data["connections"]
            ],
            locations=(
                [Location.fromJsonDict(location) for location in data["locations"]]
                if locations is not None
                else None
            ),
        )


@dataclass
class Connection:
    """Represents the data structure of a Connection within the CelesteLevelData.json file."""

    dest: str
    rule: List[List[str]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Connection:
        return Connection(dest=data["dest"], rule=data["rule"])


@dataclass
class Location:
    """Represents the data structure of a Location within the CelesteLevelData.json file."""

    name: str
    display_name: str
    type: str
    rule: List[List[str]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Location:
        return Location(
            name=data["name"],
            display_name=data["display_name"],
            type=data["type"],
            rule=data["rule"],
        )


@dataclass
class Door:
    """Represents the data structure of a Door within the CelesteLevelData.json file."""

    name: str
    direction: str
    blocked: bool
    closes_behind: bool

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> Door:
        return Door(
            name=data["name"],
            direction=data["direction"],
            blocked=data["blocked"],
            closes_behind=data["closes_behind"],
        )


@dataclass
class RoomConnection:
    """Represents the data structure of a RoomConnection within the CelesteLevelData.json file."""

    source_room: str
    source_door: str
    dest_room: str
    dest_door: str

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> RoomConnection:
        return RoomConnection(
            source_room=data["source_room"],
            source_door=data["source_door"],
            dest_room=data["dest_room"],
            dest_door=data["dest_door"],
        )
