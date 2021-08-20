LANGUAGE_CHANNELS = {
    "#french": ["fr"],
    "#russian": ["ru", "by"],    # Be conservative here
    "#german": ["de"],
}
# Flip around for easier use
DEFAULT_LANGUAGE_CHANNELS = {
    code: channel
    for channel, codes in LANGUAGE_CHANNELS.items()
    for code in codes
}
