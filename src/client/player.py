class Player:
    """
    Represents a player the client knows about, mirrors the similar class in the server.
    Needs to be constructed using a player_info message sent from the server.
    """
    def __init__(self,
                 id=None,
                 login=None,
                 global_rating=(1500, 500),
                 ladder_rating=(1500, 500),
                 number_of_games=0,
                 avatar=None,
                 country=None,
                 clan=None,
                 league=None):
        """
        Initialize a Player
        """
        # Required fields
        self.id = id
        self.login = login
        if not id or not login:
            raise KeyError("Player missing id or login attribute {}".format(self))

        # Optional fields
        self.global_rating = global_rating
        self.ladder_rating = ladder_rating
        self.number_of_games = number_of_games
        self.avatar = avatar or None
        self.country = country or None
        self.clan = clan or None
        self.league = league or None

    def __hash__(self):
        """
        Index by id
        """
        return self.id.__hash__()

    def __index__(self):
        return self.id

    def __eq__(self, other):
        """
        Equality by id

        :param other: player object to compare with
        """
        if not isinstance(other, Player):
            return False
        return other.id == self.id

    def __getitem__(self, item):
        """
        Allow dictionary access

        # FIXME: Don't use Player as a dictionary
        """
        if isinstance(item, str):
            return getattr(self, item)

    def rounded_rating_estimate(self):
        """
        Get the conservative estimate of the players global trueskill rating, rounded to nearest 100
        """
        return round((self.rating_estimate()/100))*100

    def rating_estimate(self):
        """
        Get the conservative estimate of the players global trueskill rating
        """
        return int(max(0, (self.global_rating[0] - 3 * self.global_rating[1])))

    @property
    def rating_mean(self):
        return self.global_rating[0]

    @property
    def rating_deviation(self):
        return self.global_rating[1]

    @property
    def ladder_rating_mean(self):
        return self.ladder_rating[0]

    @property
    def ladder_rating_deviation(self):
        return self.ladder_rating[1]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Player(id={}, login={}, global_rating={}, ladder_rating={})".format(
            self.id,
            self.login,
            self.global_rating,
            self.ladder_rating
        )
