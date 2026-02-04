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
        CelesteLocationCheckPath
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
                CelesteLocationCheckPath.fromJsonDict(checkpath)
                for checkpath in data["region_paths_to_location"]
            ],
        )

    ##
    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CelesteLocationCheckPath:
    """A minimal representation of a Celeste Region Path"""

    # The list of regions which leads from the origin of a Celeste Level to the location.
    regions: List[str]

    # A triple-nested List of logic rules representing the necessary unlocks to get to a location.
    # using the list of regions above. The outermost list represents the "path" of logic, and each
    # pair of inner lists represents a logic rule for a single step in the process, using the outer
    # of the two lists to represent logical ORs and the inner of the two lists to represent logical
    # ANDs.
    #
    # Example: [ [ [ "dash_refills" ] ], [ [ "springs", "dream_blocks" ] ] ] is a two-region
    #           path, the first of which requires dash_refills and the second of which
    #           requires springs and dream_blocks.
    #
    # Example: [ [ [ "dash_refills" ], [ "springs" ] ], [ [ "springs", "dream_blocks" ] ] ]
    #           is a two-region path, the first of which requires dash refills OR springs and
    #           the second of which requires springs and dream blocks.
    rules: List[List[List[str]]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLocationCheckPath:
        return CelesteLocationCheckPath(regions=data["regions"], rules=data["rules"])

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
            region_name=data["region_name"], rule_to_next=data["rule_to_next"]
        )

    @classmethod
    def fromCelesteRegionPathNode(
        cls,
        currentRegionNode: CelestePathRegionNode,
        nextRegionNode: Optional[CelestePathRegionNode] = None,
    ) -> CelesteLocationCheckPathRegion:
        return CelesteLocationCheckPathRegion(
            region_name=f"{currentRegionNode.room_name}-{currentRegionNode.region.name}",
            rule_to_next=(
                []
                if nextRegionNode is None
                or currentRegionNode.room_name
                != nextRegionNode.room_name  # If we don't do this, we get an issue if the next room's door entry region name is the same as a region connected to the current region's exit door region
                else next(
                    (
                        connection.rule
                        for connection in currentRegionNode.region.connections
                        if connection.dest == nextRegionNode.region.name
                    ),
                    [],
                )
            ),
        )

    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CelestePathRegionNode:
    """A Celeste Path Region which is aware of its room."""

    room_name: str
    region: Region
