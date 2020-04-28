"""secret_hitler.execeptions

Common exceptions thrown by the game.
"""


class GameError(Exception):
    """Base class for all exceptions thrown by secret_hitler"""
    pass


class UnreachableStateError(GameError):
    pass


class UnimplementedFeature(GameError):
    pass
