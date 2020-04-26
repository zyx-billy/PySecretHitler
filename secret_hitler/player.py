from enum import Enum

from secret_hitler.exceptions import UnreachableStateError

class Identity(Enum):
    LIBERAL = "Liberal"
    FASCIST = "Fascist"
    HITLER = "Hitler"

class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.identity = None
