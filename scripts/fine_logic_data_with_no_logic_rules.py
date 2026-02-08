from data.celeste_data_file_reader import readCelesteLogicData


#################
# Script Logic  #
#################
def main() -> None:
    rawLogicData = readCelesteLogicData()
    for check in rawLogicData.locationLogic:
        if len(check.logic_rule) == 0:
            print(
                f"No logic found for: {check.level_display_name} - {check.room_name} - {check.location_display_name}"
            )


#################
# Entry Point   #
#################

if __name__ == "__main__":
    main()
