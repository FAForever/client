from games.gamemodel import GameSortModel
from model.game import GameState


class CoopGameFilterModel(GameSortModel):
    def __init__(self, me, model):
        GameSortModel.__init__(self, me, model)

    def filter_accepts_game(self, game):
        if game.state != GameState.OPEN:
            return False
        if game.featured_mod != ("coop" or "nomadscoop"):
            return False
        return True
