from enum import Enum
from typing import List

from secret_hitler.board import Board, Tile
from secret_hitler.exceptions import GameError
from secret_hitler.player import Player

class InvalidCommandError(Exception):
    def __init__(self, state, command, reason):
        self.state = state
        self.command = command
        self.reason = reason
        super().__init__(f"Cannot perform command {command} at state {state}: {reason}")

class CommandStateError(Exception):
    def __init__(self, expected_state, actual_state):
        self.expected = expected_state
        self.actual = actual_state
        super().__init__(f"Expected: {self.expected}, Actual: {self.actual}")

class Stage(Enum):
    NEW_GAME = 0
    NEW_PRESIDENT = 1
    CHANCELLOR_NOMINATED = 2
    PRESIDENT_DECIDES_LEGISLATION = 3
    CHANCELLOR_DECIDES_LEGISLATION = 4
    PERFORM_PRESIDENTIAL_POWER = 5
    GAME_OVER = 6

class Game:
    def __init__(self):
        self.board : Board = Board()
        self.state : Stage = Stage.NEW_GAME
        self.winner : Tile = None

    def requires_state(self, state: Stage):
        if self.state != state:
            raise CommandStateError(state, self.state)
    
    def shift_state(self, state: Stage):
        self.state = state

    def add_player(self, name: str):
        requires_state(Stage.NEW_GAME)
        self.board.add_player(name)
        shift_state(Stage.NEW_GAME)
    
    def begin_game(self):
        requires_state(Stage.NEW_GAME)
        self.board.assign_identities()
        shift_state(Stage.NEW_PRESIDENT)

    def nominate_chancellor(self, nominee: str):
        requires_state(Stage.NEW_PRESIDENT)
        if nominee == self.board.get_president():
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as current president")
        if nominee == self.board.prev_chancellor:
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as previous chancellor")
        if nominee == self.board.prev_president and len(self.board.players) > 5:
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as previous president")
        self.board.nominated_chancellor = self.board.get_player(nominee)
        shift_state(Stage.CHANCELLOR_NOMINATED)
    
    # True for Ja, False for Nein
    def vote_for_chancellor(self, votes: List[bool]):
        requires_state(Stage.CHANCELLOR_NOMINATED)
        if len(votes) != len(self.board.players):
            raise InvalidCommandError(self.state, "vote_for_chancellor",
                                      f"Number of votes ({len(votes)}) does not equal number of active players "
                                      f"({len(self.board.players)})")
        
        if votes.count(True) > (len(self.board.players) // 2):
            # vote passed
            self.board.prev_chancellor = self.board.chancellor
            self.board.chancellor = self.board.nominated_chancellor
            self.board.nominated_chancellor = None
            self.board.draw_three_tiles()
            shift_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
            return
        
        # vote failed
        self.board.nominated_chancellor = None
        shift_state(Stage.NEW_PRESIDENT)

    def president_discards_tile(self, tile: Tile):
        requires_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
        self.board.discard_tile(tile)
        shift_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)

    def chancellor_discards_tile(self, tile: Tile):
        requires_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)
        self.board.discard_tile(tile)
        # check game status
        self.winner = self.board.get_winner()
        if self.winner:
            shift_state(Stage.GAME_OVER)
            return
        
        if self.board.get_current_presidential_power:
            shift_state(Stage.PERFORM_PRESIDENTIAL_POWER)
            return
        
        # no winner and no presidential power, shift president
        self.board.advance_president()
        shift_state(Stage.NEW_PRESIDENT)
