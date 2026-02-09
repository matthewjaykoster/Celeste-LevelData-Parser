from data.celeste_data_file_reader import readCelesteLogicData

EXECPTED_NO_LOGIC_LOCATION_KEYS = [
    "Prologue - -1 - Car",
    "Prologue - 0 - Start",
    "Prologue - 3 - Level Clear",
    "Forsaken City A - 1 - Start",
    "Forsaken City A - 3 - Strawberry",
    "Forsaken City B - 00 - Start",
    "Forsaken City C - 00 - Start",
    "Old Site A - start - Start",
    "Old Site A - s2 - Crystal Heart",
    "Old Site A - d3 - Binoculars",
    "Old Site A - d6 - Strawberry",
    "Old Site B - start - Start",
    "Old Site C - 00 - Start",
    "Celestial Resort A - s0 - Start",
    "Celestial Resort A - s2 - Strawberry 1",
    "Celestial Resort A - s2 - Strawberry 2",
    "Celestial Resort A - s3 - Front Door Key",
    "Celestial Resort B - 00 - Start",
    "Celestial Resort B - back - Binoculars",
    "Celestial Resort C - 00 - Start",
    "Golden Ridge A - a-00 - Start",
    "Golden Ridge B - a-00 - Start",
    "Golden Ridge C - 00 - Start",
    "Mirror Temple A - a-00b - Start",
    "Mirror Temple A - a-00x - Strawberry",
    "Mirror Temple B - start - Start",
    "Mirror Temple C - 00 - Start",
    "Reflection A - 00 - Start",
    "Reflection B - a-00 - Start",
    "Reflection C - 00 - Start",
    "The Summit A - a-00 - Start",
    "The Summit B - a-00 - Start",
    "The Summit C - 01 - Start",
    "The Summit C - 01 - Binoculars",
    "Epilogue - outside - Start",
    "Core A - 00 - Start",
    "Core B - 00 - Start",
    "Core C - intro - Start",
    "Farewell - intro-00-past - Start",
    "Farewell - end-golden - Binoculars 1",
    "Farewell - end-golden - Binoculars 2",
]


#################
# Script Logic  #
#################
def main() -> None:
    rawLogicData = readCelesteLogicData()
    for check in rawLogicData.locationLogic:
        if (
            f"{check.level_display_name} - {check.room_name} - {check.location_display_name}"
            in EXECPTED_NO_LOGIC_LOCATION_KEYS
        ):
            print(
                f"[EXPECTED] No logic found for: {check.level_display_name} - {check.room_name} - {check.location_display_name}"
            )
        elif len(check.logic_rule) == 0:
            print(
                f"No logic found for: {check.level_display_name} - {check.room_name} - {check.location_display_name}"
            )


#################
# Entry Point   #
#################

if __name__ == "__main__":
    main()
