"""secret_hitler.game

Main game handle. Provides an external interface for the game.
"""
from typing import Dict, Optional, Tuple

from secret_hitler import stages
from secret_hitler.board import Board
from secret_hitler.exceptions import GameError
from secret_hitler.prompts import Prompt


class Game:
    def __init__(self):
        self.board: Board = Board()
        self.stage: stages.Stage = None

    def requires_game_started(self, attempt: str):
        if self.stage is None:
            raise GameError(f"Requires game to have begun to {attempt}")

    def requires_game_not_started(self, attempt: str):
        if self.stage is not None:
            raise GameError(f"Requires game to not have begun to {attempt}")

    def get_full_state(self) -> Dict:
        self.requires_game_started("get the full state")
        return self.board.get_full_state()

    def get_identity(self, name) -> str:
        self.requires_game_started("get player identity")
        return self.board.get_player(name).identity.value

    def add_player(self, name: str) -> None:
        self.requires_game_not_started("add a player")
        self.board.add_player(name)

    def begin_game(self) -> Tuple[Dict[str, Prompt], Dict]:
        self.requires_game_not_started("begin game")
        self.board.begin_game()
        self.stage = stages.RevealIdentities(self.board)
        return (self.stage.prompts().get_dict(), self.board.extract_updates())

    def perform_action(self, action, choice) -> Tuple[Optional[Dict[str, Prompt]], Dict]:
        next_stage = self.stage.perform_action(action, choice)
        if next_stage == self.stage:
            # this stage not done yet
            return (None, self.board.extract_updates())

        # state done
        self.stage = next_stage
        return (self.stage.prompts().get_dict(), self.board.extract_updates())
