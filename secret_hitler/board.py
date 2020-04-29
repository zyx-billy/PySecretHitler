"""secret_hitler.board

Maintains game state and provides common methods for manipulating the game state.
Also keeps track of changes to the game state for partially updating game clients.
"""

from enum import Enum
import random
from typing import Dict, List, Optional, Tuple

from secret_hitler.exceptions import GameError, UnreachableStateError
from secret_hitler.player import Player, Identity


class DuplicatePlayerNameError(GameError):
    def __init__(self, dup_name):
        self.dup_name = dup_name
        super().__init__(f"Duplicate name not allowed: {dup_name}")


class NonexistentPlayerNameError(GameError):
    def __init__(self, player_name):
        self.player_name = player_name
        super().__init__(f"Nonexistent player used: {player_name}")


class NonexistentTileError(GameError):
    def __init__(self, tile):
        self.tile = tile
        super().__init__(f"Cannot discard non-existent tile: {tile}")


class InvalidNumPlayersError(GameError):
    def __init__(self, num_players):
        self.num_players = num_players
        super().__init__(f"Invalid number of players {num_players}. Min: 5, Max 10.")

# Board elements


class Vote(Enum):
    JA = "ja"
    NEIN = "nein"


class Tile(Enum):
    LIBERAL_POLICY = "Liberal"
    FASCIST_POLICY = "Fascist"


class Faction(Enum):
    LIBERAL = "Liberal"
    FASCIST = "Fascist"

    @staticmethod
    def from_tile(tile: Tile):
        if tile == Tile.LIBERAL_POLICY:
            return Faction.LIBERAL
        elif tile == Tile.FASCIST_POLICY:
            return Faction.FASCIST
        raise UnreachableStateError("Invalid Tile Enum value")


class PresidentialPower(Enum):
    INVESTIGATE_LOYALTY = 0
    CALL_SPECIAL_ELECTION = 1
    POLICY_PEEK = 2
    EXECUTION = 3

    def description(self):
        if self == PresidentialPower.INVESTIGATE_LOYALTY:
            return "The President investigates a player's identity card"
        elif self == PresidentialPower.CALL_SPECIAL_ELECTION:
            return "The President picks the next presidential candidate"
        elif self == PresidentialPower.POLICY_PEEK:
            return "The President examines the top three cards"
        elif self == PresidentialPower.EXECUTION:
            return "The President must kill a player"
        raise UnreachableStateError("Invalid PresidentialPower Enum value")


# Board configs
# num_players -> num_liberals, num_fascists, presidential_powers
NUM_PLAYERS_TO_BOARD_CONFIG: Dict[int, Tuple[int, int, List[Optional[PresidentialPower]]]] = {
    2: (1, 0,
        [None,
         None,
         PresidentialPower.POLICY_PEEK,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    4: (2, 1,
        [None,
         None,
         PresidentialPower.POLICY_PEEK,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    5: (3, 1,
        [None,
         None,
         PresidentialPower.POLICY_PEEK,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    6: (4, 1,
        [None,
         None,
         PresidentialPower.POLICY_PEEK,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    7: (4, 2,
        [None,
         PresidentialPower.INVESTIGATE_LOYALTY,
         PresidentialPower.CALL_SPECIAL_ELECTION,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    8: (5, 2,
        [None,
         PresidentialPower.INVESTIGATE_LOYALTY,
         PresidentialPower.CALL_SPECIAL_ELECTION,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    9: (5, 3,
        [PresidentialPower.INVESTIGATE_LOYALTY,
         PresidentialPower.INVESTIGATE_LOYALTY,
         PresidentialPower.CALL_SPECIAL_ELECTION,
         PresidentialPower.EXECUTION,
         PresidentialPower.EXECUTION,
         None]),
    10: (6, 3,
         [PresidentialPower.INVESTIGATE_LOYALTY,
          PresidentialPower.INVESTIGATE_LOYALTY,
          PresidentialPower.CALL_SPECIAL_ELECTION,
          PresidentialPower.EXECUTION,
          PresidentialPower.EXECUTION,
          None])
}

LIBERAL_WINNING_PROGRESS = 5
FASCIST_WINNING_PROGRESS = 6

# Main board class


class Board:
    def __init__(self):
        self.players: List[Player] = []  # active players only
        self.eliminated_players: List[Player] = []
        self.president_idx: int = 0
        self.chancellor: Player = None
        self.prev_president: Optional[Player] = None
        self.prev_chancellor: Optional[Player] = None
        self.nominated_chancellor: Player = None
        self.unused_tiles: List[Tile] = [Tile.LIBERAL_POLICY] * 6 + [Tile.FASCIST_POLICY] * 11
        self.discarded_tiles: List[Tile] = []
        self.election_tracker: int = 0
        self.liberal_progress: int = 0
        self.fascist_progress: int = 0
        self.fascist_powers: List[Optional[PresidentialPower]] = []

        # keeps track of updated properties
        self.updates = set()

        random.shuffle(self.unused_tiles)

    # State update tracking
    private_state_translations = {
        "players": (lambda me, l: [p.name for p in l]),
        "eliminated_players": (lambda me, l: [p.name for p in l]),
        "president_idx": ("president", (lambda me, id: me.players[id].name)),
        "chancellor": (lambda me, c: c and c.name),
        "unused_tiles": (lambda me, l: len(l)),
        "discarded_tiles": (lambda me, l: len(l)),
        "election_tracker": None,
        "liberal_progress": None,
        "fascist_progress": None,
        "fascist_powers": (lambda me, l: [p.description() if p else "" for p in l]),
    }

    def register_update(self, prop):
        self.updates.add(prop)

    def extract_updates(self, custom_updates=None):
        new_updates = custom_updates or self.updates
        response = dict()
        for prop in new_updates:
            if prop not in Board.private_state_translations:
                continue

            elif Board.private_state_translations[prop] is None:
                response[prop] = getattr(self, prop)
            elif type(Board.private_state_translations[prop]) is not tuple:
                response[prop] = Board.private_state_translations[prop](self, getattr(self, prop))
            else:
                (alias, transformer) = Board.private_state_translations[prop]
                response[alias] = transformer(self, getattr(self, prop))

        self.updates = set()
        return response

    def get_full_state(self):
        return self.extract_updates(Board.private_state_translations.keys())

    # Player manipulation
    def add_player(self, name: str) -> None:
        self.register_update("players")
        if any(p.name == name for p in self.players):
            raise DuplicatePlayerNameError(name)
        self.players.append(Player(name))

    def get_player(self, name: str) -> Player:
        for p in self.players:
            if p.name == name:
                return p
        raise NonexistentPlayerNameError(name)

    def begin_game(self) -> None:
        self.register_update("players")
        self.register_update("fascist_powers")
        if len(self.players) not in NUM_PLAYERS_TO_BOARD_CONFIG:
            raise InvalidNumPlayersError(len(self.players))

        board_config = NUM_PLAYERS_TO_BOARD_CONFIG[len(self.players)]
        identities = ([Identity.LIBERAL] * board_config[0]
                      + [Identity.FASCIST] * board_config[1]
                      + [Identity.HITLER])
        random.shuffle(identities)

        for i in range(len(self.players)):
            self.players[i].identity = identities[i]

        self.fascist_powers = board_config[2]

    # Other state manipulations
    def get_president(self) -> Player:
        return self.players[self.president_idx]

    def advance_president(self) -> None:
        self.register_update("president_idx")
        self.register_update("chancellor")
        self.prev_president = self.get_president()
        self.prev_chancellor = self.chancellor
        self.president_idx = (self.president_idx + 1) % len(self.players)

    def establish_new_chancellor(self, nominee: Player) -> None:
        self.register_update("chancellor")
        self.chancellor = nominee

    def enact_policy(self, policy: Tile) -> None:
        # the enacted tile is destroyed (does not put back into any tile list)
        print("enacting policy: " + policy.value)
        if policy == Tile.LIBERAL_POLICY:
            self.liberal_progress += 1
            self.register_update("liberal_progress")
        elif policy == Tile.FASCIST_POLICY:
            self.fascist_progress += 1
            self.register_update("fascist_progress")
        # reset election tracker
        if self.election_tracker > 0:
            self.election_tracker = 0
            self.register_update("election_tracker")

    def recycle_used_tiles(self) -> None:
        # shuffle discarded tiles and put under unused tiles
        random.shuffle(self.discarded_tiles)
        self.unused_tiles += self.discarded_tiles
        self.discarded_tiles = []
        self.register_update("unused_tiles")
        self.register_update("discarded_tiles")

    def draw_three_tiles(self) -> List[Tile]:
        if len(self.unused_tiles) < 3:
            self.recycle_used_tiles()

        drawn_tiles = self.unused_tiles[:3]
        self.unused_tiles = self.unused_tiles[3:]
        self.register_update("unused_tiles")
        return drawn_tiles

    def discard_tile(self, drawn_tiles: List[Tile], tile: Tile) -> None:
        if tile not in drawn_tiles:
            raise NonexistentTileError(tile)
        drawn_tiles.remove(tile)
        self.discarded_tiles.append(tile)
        self.register_update("discarded_tiles")

    def advance_election_tracker(self) -> bool:
        self.election_tracker += 1
        self.register_update("election_tracker")
        return self.election_tracker == 3  # true if need to enter chaos

    def enter_chaos(self) -> None:
        # enact the top unused tile
        if len(self.unused_tiles) < 1:
            self.recycle_used_tiles()
        selected_policy = self.unused_tiles[0]
        self.unused_tiles = self.unused_tiles[1:]
        self.register_update("unused_tiles")
        self.enact_policy(selected_policy)
        # reset election tracker and term limits
        self.election_tracker = 0
        self.prev_chancellor = None
        self.prev_president = None
        self.register_update("election_tracker")
        self.register_update("prev_chancellor")
        self.register_update("prev_president")

    def get_winner(self) -> Optional[Faction]:
        self.winner: Optional[Faction] = None
        if self.liberal_progress == LIBERAL_WINNING_PROGRESS:
            self.winner = Faction.LIBERAL
            self.register_update("winner")
        elif self.fascist_progress == FASCIST_WINNING_PROGRESS:
            self.winner = Faction.LIBERAL
            self.register_update("winner")
        return self.winner

    def get_latest_presidential_power(self) -> Optional[PresidentialPower]:
        if self.fascist_progress == 0:
            return None
        return self.fascist_powers[self.fascist_progress - 1]

    def peek_top_three_tiles(self) -> List[Tile]:
        if len(self.unused_tiles) < 3:
            self.recycle_used_tiles()
        return self.unused_tiles[:3]

    # have to be done at the same time due to weird president_idx logic
    def execute_player_and_advance_president(self, player_name: str) -> None:
        unlucky_person = None
        unlucky_idx = 0
        for player in self.players:
            if player.name == player_name:
                unlucky_person = player
                break
            unlucky_idx += 1

        if unlucky_person is None:
            raise UnreachableStateError("Cannot execute non-live player: " + player_name)

        # save prev president and chancellor
        self.register_update("president_idx")
        self.register_update("chancellor")
        self.prev_president = self.get_president()
        self.prev_chancellor = self.chancellor

        # find out next president_idx
        if self.president_idx < unlucky_idx:
            next_president_idx = self.president_idx + 1
        else:
            next_president_idx = self.president_idx % (len(self.players) - 1)

        # actually eliminate the unlucky person
        self.players.remove(unlucky_person)
        self.eliminated_players.append(unlucky_person)
        self.register_update("players")
        self.register_update("eliminated_players")

        # advance president
        self.president_idx = next_president_idx
