from enum import Enum

class Identity(Enum):
    LIBERAL = 0
    FASCIST = 1 # non-hitler fascist
    HITLER = 2

    def __str__(self):
        if self.value == 0:
            return "Liberal"
        if self.value == 1:
            return "Fascist"
        return "Hitler"

class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.identity = None
