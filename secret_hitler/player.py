from enum import Enum

from secret_hitler.exceptions import UnreachableStateError

class Identity(Enum):
    LIBERAL = "Liberal"
    FASCIST = "Fascist"
    HITLER = "Hitler"

class Player:
    def __init__(self, name):
        self.name = name        # unique identifier
        self.identity = None
