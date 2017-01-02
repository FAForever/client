from Setting import Setting

hide_private_games = Setting("play/hidePrivateGames", bool)
sort_games = Setting("play/sortGames", int)
sub_factions = Setting("play/subFactions", bool)

# mods selected by user, are not overwritten by temporary mods selected when joining game
selected_mods = Setting('play/mods')
