from data.celeste_data_file_reader import readCelesteLocationData


rawCelesteLocationData = readCelesteLocationData()
maxRegionPathLengthByLevel = {}

for location in rawCelesteLocationData.locations:
    for regionPath in location.region_paths_to_location:
        if len(regionPath.regions) > (
            maxRegionPathLengthByLevel.get(location.level_name) or 0
        ):
            maxRegionPathLengthByLevel[location.level_name] = len(regionPath.regions)

for idx, key in enumerate(maxRegionPathLengthByLevel):
    print(f"{key}: {maxRegionPathLengthByLevel[key]}")
