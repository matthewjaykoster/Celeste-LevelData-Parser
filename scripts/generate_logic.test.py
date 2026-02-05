from typing import List
from data.celeste_data_file_reader import readCelesteLocationData
from scripts.generate_logic import (
    collapseLocationCheckPathLogic,
    cullRules,
    remapLogicRules,
)


def _testCull():
    rules = [
        [
            "celestialresorta-frontdoorkey",
            "celestialresorta-hallwaykey1",
            "sinking_platforms",
        ],
        [
            "$KEYSANITY_IS_DISABLED",
            "celestialresorta-frontdoorkey",
            "sinking_platforms",
        ],
        [
            "celestialresorta-frontdoorkey",
            "celestialresorta-hallwaykey1",
            "dash_refills",
            "sinking_platforms",
        ],
        [
            "$KEYSANITY_IS_DISABLED",
            "celestialresorta-frontdoorkey",
            "dash_refills",
            "sinking_platforms",
        ],
        ["$KEYSANITY_IS_DISABLED", "celestialresorta-hallwaykey1", "sinking_platforms"],
        ["$KEYSANITY_IS_DISABLED", "sinking_platforms"],
        [
            "$KEYSANITY_IS_DISABLED",
            "celestialresorta-hallwaykey1",
            "dash_refills",
            "sinking_platforms",
        ],
        ["$KEYSANITY_IS_DISABLED", "dash_refills", "sinking_platforms"],
    ]

    print(cullRules(rules))


def _testCollapseLocationCheckPathLogic():
    """Lazy test function for collapseLocationCheckPathLogic(...)."""
    sampleLogic = [[["traffic_blocks"]], [["traffic_blocks"]], [["springs"]]]
    print(collapseLocationCheckPathLogic(sampleLogic))

    sampleLogicTwo = [
        [["traffic_blocks"]],
        [["traffic_blocks", "dream_blocks"], ["dash_refills"]],
        [["springs"]],
    ]
    print(collapseLocationCheckPathLogic(sampleLogicTwo))

    sampleLogicThree = [
        [["dash_refills"]],
        [["springs"]],
        [["springs"]],
        [["dash_refills", "springs"]],
        [["dash_refills"]],
        [["badeline_boosters", "springs"]],
        [["traffic_blocks", "dash_refills"]],
        [["traffic_blocks", "springs"]],
        [["traffic_blocks", "dash_refills"]],
        [["traffic_blocks", "dash_refills"]],
        [["traffic_blocks", "dash_refills"]],
        [["springs", "coins", "dash_refills"]],
        [["traffic_blocks"]],
        [["traffic_blocks"]],
        [["springs"]],
        [["traffic_blocks", "badeline_boosters"]],
        [["dream_blocks"]],
        [["dream_blocks"]],
        [["dream_blocks", "springs", "coins"]],
        [["dream_blocks"]],
        [["dream_blocks"]],
        [["dream_blocks"]],
        [["dream_blocks"]],
        [["dream_blocks"]],
        [["dream_blocks", "badeline_boosters"]],
        [["dash_refills"]],
        [["sinking_platforms"]],
        [["coins"]],
        [["coins"], ["dash_refills"]],
        [["dash_refills"]],
        [["badeline_boosters"]],
        [["blue_boosters"]],
        [["blue_boosters", "blue_clouds"]],
        [["blue_boosters", "moving_platforms"]],
        [["blue_boosters", "springs"]],
        [["move_blocks"]],
        [["move_blocks"]],
        [["blue_clouds"]],
        [["move_blocks", "blue_boosters"]],
        [["blue_boosters"]],
        [["move_blocks", "dash_refills", "springs"]],
        [
            [
                "badeline_boosters",
                "dash_refills",
                "move_blocks",
                "blue_boosters",
                "springs",
            ]
        ],
        [["red_boosters"]],
        [["swap_blocks"]],
        [["swap_blocks"]],
        [["swap_blocks", "dash_refills"]],
        [["2500 M Key"], ["$KEYSANITY_IS_DISABLED"]],
        [["swap_blocks", "red_boosters", "dash_refills"]],
        [["red_boosters"]],
        [["swap_blocks"]],
        [["springs", "dash_refills", "dash_switches"]],
        [["badeline_boosters", "swap_blocks", "springs", "red_boosters"]],
    ]
    resultThree = collapseLocationCheckPathLogic(sampleLogicThree)
    print(list({frozenset(p) for p in resultThree}))

    rawCelesteLocationData = readCelesteLocationData()
    sampleFour = next(
        location
        for location in rawCelesteLocationData.locations
        if location.level_name == "7a"
        and location.room_name == "f-07"
        and location.location_name == "strawberry"
    )
    resultFour: List[List[str]] = []
    for path in sampleFour.region_paths_to_location:
        path.rules.append(sampleFour.location_rule)
        resultFour = resultFour + collapseLocationCheckPathLogic(path.rules)
    print(list({frozenset(p) for p in resultFour}))


def _testPrintRemap():
    sample = [
        [["Front Door Key"]],
        [["sinking_platforms"], ["dash_refills"]],
        [["Hallway Key 1"]],
        [["sinking_platforms"]],
    ]

    sample = remapLogicRules(sample)
    print(collapseLocationCheckPathLogic(sample))


# _testCollapseLocationCheckPathLogic()
# _testPrintRemap()
_testCull()
