from enum import Enum

class Identity(Enum):
    LIBERAL = 0
    FASCIST = 1 # non-hitler fascist
    HITLER = 2

class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.identity = None
