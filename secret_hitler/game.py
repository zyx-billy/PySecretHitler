from enum import Enum
from typing import List

from secret_hitler.board import Board, Tile
from secret_hitler.exceptions import GameError
from secret_hitler.player import Player
from secret_hitler.prompts import Prompts

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
    
    def requires_game_started(self):
        if self.state == Stage.NEW_GAME:
            raise CommandStateError("Any other state", self.state)
    
    def gen_response(self):
        prompts = Prompts()
        if self.state == Stage.NEW_GAME:
            pass
        elif self.state == Stage.NEW_PRESIDENT:
            # president nominate chancellor
            prompts.add(self.board.get_president(),
                        method="nominate_chancellor",
                        prompt_str="Nominate your chancellor",
                        choices=[p.name for p in self.board.players])
        elif self.state == Stage.CHANCELLOR_NOMINATED:
            # everyone votes
            for player in self.board.players:
                prompts.add(player,
                            method="vote_for_chancellor",
                            prompt_str="Vote for chancellor",
                            choices=["ja","nein"])
        elif self.state == Stage.PRESIDENT_DECIDES_LEGISLATION:
            # president discards a tile
            prompts.add(self.board.get_president(),
                        method="president_discards_tile",
                        prompt_str="Discard a policy tile",
                        choices=map(str, self.board.drawn_tiles))
        elif self.state == Stage.CHANCELLOR_DECIDES_LEGISLATION:
            # chancellor discards a tile
            prompts.add(self.board.chancellor,
                        method="chancellor_discards_tile",
                        prompt_str="Discard a policy tile",
                        choices=map(str, self.board.drawn_tiles))
        
        return (prompts, self.board.extract_updates())

    def get_full_state(self):
        requires_game_started()
        return self.board.get_full_state()
    
    def get_identity(self, name):
        requires_game_started()
        return str(self.board.get_player(name).identity)

    def add_player(self, name: str):
        requires_state(Stage.NEW_GAME)
        self.board.add_player(name)
        shift_state(Stage.NEW_GAME)
        return gen_response()
    
    def begin_game(self):
        requires_state(Stage.NEW_GAME)
        self.board.begin_game()
        shift_state(Stage.NEW_PRESIDENT)
        return gen_response()

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
        return gen_response()
    
    def vote_for_chancellor(self, votes: List[str]):
        requires_state(Stage.CHANCELLOR_NOMINATED)
        if len(votes) != len(self.board.players):
            raise InvalidCommandError(self.state, "vote_for_chancellor",
                                      f"Number of votes ({len(votes)}) does not equal number of active players "
                                      f"({len(self.board.players)})")
        
        if votes.count("ja") > (len(self.board.players) // 2):
            # vote passed
            self.board.prev_chancellor = self.board.chancellor
            self.board.chancellor = self.board.nominated_chancellor
            self.board.nominated_chancellor = None
            self.board.draw_three_tiles()
            shift_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
            return gen_response()
        
        # vote failed
        self.board.nominated_chancellor = None
        shift_state(Stage.NEW_PRESIDENT)
        return gen_response()

    def president_discards_tile(self, tile: Tile):
        requires_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
        self.board.discard_tile(tile)
        shift_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)
        return gen_response()

    def chancellor_discards_tile(self, tile: Tile):
        requires_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)
        self.board.discard_tile(tile)
        # check game status
        self.winner = self.board.get_winner()
        if self.winner:
            shift_state(Stage.GAME_OVER)
            return gen_response()
        
        if self.board.get_current_presidential_power:
            shift_state(Stage.PERFORM_PRESIDENTIAL_POWER)
            return gen_response()
        
        # no winner and no presidential power, shift president
        self.board.advance_president()
        shift_state(Stage.NEW_PRESIDENT)
        return gen_response()
