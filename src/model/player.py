from PyQt5.QtCore import pyqtSignal
from model.transaction import transactional
from model.modelitem import ModelItem


class Player(ModelItem):
    newCurrentGame = pyqtSignal(object, object, object)

    """
    Represents a player the client knows about.
    """
    def __init__(self,
                 id_,
                 login,
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

    def rounded_rating_estimate(self):
        """
        Get the conservative estimate of the players global trueskill rating,
        rounded to nearest 100
        """
        return round((self.rating_estimate/100))*100

    @property
    def rating_estimate(self):
        """
        Get the conservative estimate of the players global trueskill rating
        """
        return int(max(0, (self.global_rating[0] - 3 * self.global_rating[1])))

    def ladder_estimate(self):
        """
        Get the conservative estimate of the players ladder trueskill rating
        """
        return int(max(0, (self.ladder_rating[0] - 3 * self.ladder_rating[1])))

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
