import pytest

from model.game import Game
from model.gameset import Gameset
from model.player import Player
from model.playerset import Playerset


@pytest.fixture
def player(mocker):
    return mocker.MagicMock(spec=Player)


@pytest.fixture
def game(mocker):
    return mocker.MagicMock(spec=Game)


@pytest.fixture
def playerset(mocker):
    return mocker.MagicMock(spec=Playerset)


@pytest.fixture
def gameset(mocker):
    return mocker.MagicMock(spec=Gameset)
