class Player:
    """
    Represents a player the client knows about, mirrors the similar class in the server.
    Needs to be constructed using a player_info message sent from the server.
    """
    def __init__(self, player_info_message):
        """
        Initialize a Player from the given player_info_message sent by the server

        :param player_info_message:
        :return:
        """
        # Required fields
        self.login = player_info_message["login"]
        self.global_rating = player_info_message["global_rating"]
        self.ladder_rating = player_info_message["ladder_rating"]
        self.number_of_games = player_info_message["number_of_games"]

        # Optional fields
        self.avatar = player_info_message.get("avatar")
        self.country = player_info_message.get("country")
        self.clan = player_info_message.get("clan")
        self.league = player_info_message.get("league")

    # I'm pretty sure the trueskill library can do this for us, but I don't currently have internet
    # with which to check, so I'll cargo-cult this to make the nice refactor work.
    def get_ranking(self):
        return int(max(0, round((self.global_rating[0] - 3 * self.global_rating[1])/100.0)*100))
