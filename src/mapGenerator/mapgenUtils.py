import re

versionPattern = re.compile("\\d\\d?\\d?\\.\\d\\d?\\d?\\.\\d\\d?\\d?")
generatedMapPattern = re.compile(
    "neroxis_map_generator_({})_(.*)".format(versionPattern.pattern),
)


def isGeneratedMap(name):
    '''
    Can't even place it in mapgenManager file outside object as separate
    function  without getting import errors on start
    '''
    return re.match(generatedMapPattern, name)
