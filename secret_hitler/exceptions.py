class GameError(Exception):
    pass

class UnreachableStateError(GameError):
    pass

class UnimplementedFeature(GameError):
    pass
