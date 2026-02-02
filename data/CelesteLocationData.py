from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, List, Optional

from data.CelesteLevelData import Region


class CelesteLocationType(str, Enum):
    BINOCULARS = "binoculars"
    CAR = "car"
    CASSETTE = "cassette"
    CHECKPOINT = "checkpoint"
    CLUTTER = "clutter"
    CRYSTAL_HEART = "crystal_heart"
    GEM = "gem"
    KEY = "key"
    LEVEL_CLEAR = "level_clear"
    GOLDEN_STRAWBERRY = "golden_strawberry"
    ROOM_ENTER = "room_enter"
    STRAWBERRY = "strawberry"


@dataclass
class CelesteLocationData:
    """Represents the Celeste Location Data file."""

    locations: List[CelesteLocationCheck]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLocationData:
        return CelesteLocationData(
            locations=[
                CelesteLocationCheck.fromJsonDict(location)
                for location in data["locations"]
            ]
        )

    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CelesteLocationCheck:
    """Represents information about a location check."""

    level_name: str  # The level where the location is located.
    level_display_name: str  # The name of the level displayed to the user
    room_name: str  # The room where the location is located.
    region_name: str  # The region where the location is located.
    location_name: str  # The name of the location
    location_display_name: str  # The name of the location displayed to the user
    location_type: str  # The location type, as defined in the CelesteLocationType enum.
    location_rule: List[
        List[str]
    ]  # The location-specific logic, not inclusive of the path taken to find the location.
    region_paths_to_location: List[
        List[CelesteLocationCheckPathRegion]
    ]  # The path of regions from the origin of a given Celeste level to the location.

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLocationCheck:
        return CelesteLocationCheck(
            level_name=data["level_name"],
            level_display_name=data["level_display_name"],
            room_name=data["room_name"],
            region_name=data["region_name"],
            location_name=data["location_name"],
            location_display_name=data["location_display_name"],
            location_type=data["location_type"],
            location_rule=data["location_rule"],
            region_paths_to_location=[
                [
                    CelesteLocationCheckPathRegion.fromJsonDict(regionPathNode)
                    for regionPathNode in list
                ]
                for list in data["region_paths_to_location"]
            ],
        )

    ##
    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CelesteLocationCheckPathRegion:
    """A minimal representation of a node on a Celeste Region Path"""

    region_name: str
    rule_to_next: List[List[str]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLocationCheckPathRegion:
        return CelesteLocationCheckPathRegion(
            region_name=data["region"], rule_to_next=data["rule_to_next"]
        )

    @classmethod
    def fromCelesteRegionPath(
        cls, region: Region, nextRegion: Optional[Region] = None
    ) -> CelesteLocationCheckPathRegion:
        return CelesteLocationCheckPathRegion(
            region_name=region.name,
            rule_to_next=(
                []
                if nextRegion is None
                else next(
                    # Note: If we miss a connection here, it's often an indicator that we're doing
                    # a room transition, so we let it slide. I'd like a check here but I don't
                    # want to refactor the pathfinding logic to include room data.
                    (
                        connection.rule
                        for connection in region.connections
                        if connection.dest == nextRegion.name
                    ),
                    [],
                )
            ),
        )

    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)
