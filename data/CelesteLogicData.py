from dataclasses import asdict, dataclass
from typing import Any, List


@dataclass
class CelesteLogicData:
    """Represents the Celeste Location Data file."""

    locationLogic: List[LocationCheckLogic]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> CelesteLogicData:
        return CelesteLogicData(
            locationLogic=[
                LocationCheckLogic.fromJsonDict(logic)
                for logic in data["locationLogic"]
            ]
        )

    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocationCheckLogic:
    """Represents the logic necessary to check a given location"""

    level_display_name: str
    room_name: str
    location_display_name: str
    location_type: str

    # Logic rules are structured as a list of lists. Every list contained within the outer list
    # can be logically OR'ed together in order to create the full logic. Inner lists represent
    # logical ANDs.
    #
    # Example: [["springs", "dream_blocks"], ["dash_refills"]] represents a check which can be
    #          obtained either by having springs AND dream_blocks OR by having dash_refills.
    logic_rule: List[List[str]]

    @classmethod
    def fromJsonDict(cls, data: dict[str, Any]) -> LocationCheckLogic:
        return LocationCheckLogic(
            level_display_name=data["level_display_name"],
            room_name=data["room_name"],
            location_display_name=data["location_display_name"],
            location_type=data["location_type"],
            logic_rule=data["logic_rule"],
        )

    def toJsonDict(self) -> dict[str, Any]:
        return asdict(self)
