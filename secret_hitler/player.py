"""secret_hitler.player

A Player object encapsulates information related to the a game player.
"""

from enum import Enum


class Identity(Enum):
    LIBERAL = "Liberal"
    FASCIST = "Fascist"
    HITLER = "Hitler"


class Player:
    def __init__(self, name):
        self.name = name        # unique identifier
        self.identity = None
