from enum import Enum

from secret_hitler.exceptions import UnreachableStateError

class Identity(Enum):
    LIBERAL = 0
    FASCIST = 1 # non-hitler fascist
    HITLER = 2

    def __str__(self):
        if self == Identity.LIBERAL:
            return "Liberal"
        elif self == Identity.FASCIST:
            return "Fascist"
        elif self == Identity.HITLER:
            return "Hitler"
        raise UnreachableStateError("Invalid Identity Enum value")

class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.identity = None
