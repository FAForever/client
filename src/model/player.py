from PyQt5.QtCore import pyqtSignal

from model.modelitem import ModelItem
from model.rating import RatingType
from model.transaction import transactional


class Player(ModelItem):
    newCurrentGame = pyqtSignal(object, object, object)

    """
    Represents a player the client knows about.
    """
    def __init__(self,
                 id_,
                 login,
                 ratings={},
                 global_rating=(1500, 500),
                 ladder_rating=(1500, 500),
                 number_of_games=0,
                 avatar=None,
                 country=None,
                 clan=None,
                 league=None):
        ModelItem.__init__(self)
        """
        Initialize a Player
        """
        # Required fields
        # Login should be mutable, but we look up things by login right now
        self.id = int(id_)
        self.login = login

        self.add_field("global_rating", global_rating)
        self.add_field("ladder_rating", ladder_rating)
        self.add_field("number_of_games", number_of_games)
        self.add_field("avatar", avatar)
        self.add_field("country", country)
        self.add_field("clan", clan)
        self.add_field("league", league)
        self.add_field("ratings", ratings)

        # The game the player is currently playing
        self._currentGame = None

    @property
    def id_key(self):
        return self.id

    def copy(self):
        p = Player(self.id, self.login, **self.field_dict)
        p.currentGame = self.currentGame
        return p

    @transactional
    def update(self, **kwargs):
        _transaction = kwargs.pop("_transaction")

        old_data = self.copy()
        ModelItem.update(self, **kwargs)
        self.emit_update(old_data, _transaction)

    def __index__(self):
        return self.id

    @property
    def global_estimate(self):
        """
        Get the conservative estimate of the players global trueskill rating
        """
        return int(max(0, (self.global_rating[0] - 3 * self.global_rating[1])))

    @property
    def ladder_estimate(self):
        """
        Get the conservative estimate of the players ladder trueskill rating
        """
        return int(max(0, (self.ladder_rating[0] - 3 * self.ladder_rating[1])))

    @property
    def global_rating_mean(self):
        return round(self.global_rating[0])

    @property
    def global_rating_deviation(self):
        return round(self.global_rating[1])

    @property
    def ladder_rating_mean(self):
        return round(self.ladder_rating[0])

    @property
    def ladder_rating_deviation(self):
        return round(self.ladder_rating[1])

    def rating_estimate(self, rating_type=RatingType.GLOBAL.value):
        try:
            mean = self.ratings[rating_type]["rating"][0]
            deviation = self.ratings[rating_type]["rating"][1]
            return int(max(0, (mean - 3 * deviation)))
        except Exception:
            return 0

    def rating_mean(self, rating_type=RatingType.GLOBAL.value):
        try:
            return round(self.ratings[rating_type]["rating"][0])
        except Exception:
            return 1500

    def rating_deviation(self, rating_type=RatingType.GLOBAL.value):
        try:
            return round(self.ratings[rating_type]["rating"][1])
        except Exception:
            return 500

    def quantity_of_games(self, rating_type=RatingType.GLOBAL.value):
        try:
            return int(self.ratings[rating_type]["number_of_games"])
        except Exception:
            return 0

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return ("Player(id={}, login={}, global_rating={}, "
                "ladder_rating={})").format(
            self.id,
            self.login,
            self.global_rating,
            self.ladder_rating
        )

    @property
    def currentGame(self):
        return self._currentGame

    @transactional
    def set_currentGame(self, game, _transaction=None):
        if self.currentGame == game:
            return
        old = self._currentGame
        self._currentGame = game
        _transaction.emit(self.newCurrentGame, self, game, old)

    @currentGame.setter
    def currentGame(self, val):
        # CAVEAT: this will emit signals immediately!
        self.set_currentGame(val)
