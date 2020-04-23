from enum import Enum
from typing import List

from secret_hitler.board import Board, Tile, PresidentialPower
from secret_hitler.exceptions import GameError, UnreachableStateError, UnimplementedFeature
from secret_hitler.player import Player, Identity
from secret_hitler.prompts import Prompts

class InvalidCommandError(GameError):
    def __init__(self, state, command, reason):
        self.state = state
        self.command = command
        self.reason = reason
        super().__init__(f"Cannot perform command {command} at state {state}: {reason}")

class CommandStateError(GameError):
    def __init__(self, expected_state, actual_state):
        self.expected = expected_state
        self.actual = actual_state
        super().__init__(f"Expected: {self.expected}, Actual: {self.actual}")

class Stage(Enum):
    NEW_GAME = 0
    REVEAL_IDENTITIES = 1
    NEW_PRESIDENT = 2
    CHANCELLOR_NOMINATED = 3
    PRESIDENT_DECIDES_LEGISLATION = 4
    CHANCELLOR_DECIDES_LEGISLATION = 5
    PERFORM_PRESIDENTIAL_POWER = 6
    GAME_OVER = 7

class Game:
    def __init__(self):
        self.board : Board = Board()
        self.state : Stage = Stage.NEW_GAME
        self.winner : Tile = None
        self.identity_acks : int = 0

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
        elif self.state == Stage.REVEAL_IDENTITIES:
            # gather team info
            fascist_player_names = []
            hitler_name = ""
            for player in self.board.players:
                if player.identity == Identity.FASCIST:
                    fascist_player_names.append(player.name)
                elif player.identity == Identity.HITLER:
                    hitler_name = player.name
            # announce identites and teammates
            for player in self.board.players:
                teammate_info = ""
                if player.identity == Identity.FASCIST:
                    teammate_info += f" Hitler is: {hitler_name}."
                    if len(fascist_player_names) > 1:
                        fascists_name_list = ", ".join(fascist_player_names)
                        teammate_info += f" Your team: {fascists_name_list}"
                elif player.identity == Identity.HITLER and len(fascist_player_names) == 1:
                    teammate_info += f" Your teammate is: {fascist_player_names[0]}"
                prompts.add(player,
                            method="ack_identity",
                            prompt_str=f"You are: {str(player.identity)}." + teammate_info,
                            choices=["Got it!"])
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
                            prompt_str=f"Vote for chancellor: {self.board.nominated_chancellor.name}",
                            choices=["ja","nein"])
        elif self.state == Stage.PRESIDENT_DECIDES_LEGISLATION:
            # president discards a tile
            prompts.add(self.board.get_president(),
                        method="president_discards_tile",
                        prompt_str="Discard a policy tile",
                        choices=list(map(str, self.board.drawn_tiles)))
        elif self.state == Stage.CHANCELLOR_DECIDES_LEGISLATION:
            # chancellor discards a tile
            prompts.add(self.board.chancellor,
                        method="chancellor_discards_tile",
                        prompt_str="Discard a policy tile",
                        choices=list(map(str, self.board.drawn_tiles)))
        elif self.state == Stage.PERFORM_PRESIDENTIAL_POWER:
            # dependent on the presidential power
            presidential_power = self.board.get_current_presidential_power()
            if presidential_power is None:
                raise UnreachableStateError("Unexpectedly entered presidentail_power stage")
            # case on presidential power
            if presidential_power == PresidentialPower.INVESTIGATE_LOYALTY:
                raise UnimplementedFeature("Presidential Power: investigate loyalty")
            elif presidential_power == PresidentialPower.CALL_SPECIAL_ELECTION:
                raise UnimplementedFeature("Presidential Power: call special election")
            elif presidential_power == PresidentialPower.POLICY_PEEK:
                top_three_tiles_str = ", ".join(map(str, self.board.peek_top_three_tiles()))
                prompts.add(self.board.get_president(),
                            method="pp_done_policy_peek",
                            prompt_str=f"The top three tiles are: {top_three_tiles_str}",
                            choices=["Got it!"])
            elif presidential_power == PresidentialPower.EXECUTION:
                prompts.add(self.board.get_president(),
                            method="pp_execute_player",
                            prompt_str=f"Execute one a player",
                            choices=[p.name for p in self.board.players])
            else:
                raise UnreachableStateError("Invalid presidential power: " + presidential_power)
        elif self.state == Stage.GAME_OVER:
            # no prompts
            pass
        else:
            raise UnreachableStateError("Invalid state: " + self.state)
        
        return (prompts.get_dict(), self.board.extract_updates())
    
    def gen_empty_response(self):
        return (None, None)

    def get_full_state(self):
        self.requires_game_started()
        return self.board.get_full_state()
    
    def get_identity(self, name):
        self.requires_game_started()
        return str(self.board.get_player(name).identity)

    def add_player(self, name: str):
        self.requires_state(Stage.NEW_GAME)
        self.board.add_player(name)
        self.shift_state(Stage.NEW_GAME)
        return self.gen_response()
    
    def begin_game(self):
        self.requires_state(Stage.NEW_GAME)
        self.board.begin_game()
        self.shift_state(Stage.REVEAL_IDENTITIES)
        return self.gen_response()

    def ack_identity(self, ack):
        self.requires_state(Stage.REVEAL_IDENTITIES)
        self.identity_acks += 1
        if self.identity_acks == len(self.board.players):
            self.shift_state(Stage.NEW_PRESIDENT)
            return self.gen_response()
        return self.gen_empty_response()

    def nominate_chancellor(self, nominee: str):
        self.requires_state(Stage.NEW_PRESIDENT)
        if nominee == self.board.get_president().name:
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as current president")
        if self.board.prev_chancellor and nominee == self.board.prev_chancellor.name:
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as previous chancellor")
        if self.board.prev_president and nominee == self.board.prev_president.name and len(self.board.players) > 5:
            raise InvalidCommandError(self.state, "nominate_chancellor",
                                      "Chancellor cannot be the same as previous president")
        self.board.nominated_chancellor = self.board.get_player(nominee)
        self.shift_state(Stage.CHANCELLOR_NOMINATED)
        return self.gen_response()
    
    def vote_for_chancellor(self, vote: str):
        self.requires_state(Stage.CHANCELLOR_NOMINATED)
        res = self.board.cast_vote(vote == "ja")
        
        if res is None:
            # not yet done voting (more votes needed)
            return self.gen_empty_response()
        
        if res is True:
            # vote passed
            self.board.chancellor = self.board.nominated_chancellor
            self.board.register_update("chancellor")
            self.board.nominated_chancellor = None
            self.board.draw_three_tiles()
            self.shift_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
            return self.gen_response()
        
        # vote failed
        self.board.nominated_chancellor = None
        self.shift_state(Stage.NEW_PRESIDENT)
        # TODO: implement election tracker
        return self.gen_response()

    def president_discards_tile(self, tile: str):
        self.requires_state(Stage.PRESIDENT_DECIDES_LEGISLATION)
        self.board.discard_tile(Tile.from_str(tile))
        self.shift_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)
        return self.gen_response()

    def chancellor_discards_tile(self, tile: str):
        self.requires_state(Stage.CHANCELLOR_DECIDES_LEGISLATION)
        self.board.discard_tile(Tile.from_str(tile))
        # check game status
        self.winner = self.board.get_winner()
        if self.winner:
            self.shift_state(Stage.GAME_OVER)
            return self.gen_response()
        
        if self.board.get_current_presidential_power():
            self.shift_state(Stage.PERFORM_PRESIDENTIAL_POWER)
            return self.gen_response()
        
        # no winner and no presidential power, shift president
        self.board.advance_president()
        self.shift_state(Stage.NEW_PRESIDENT)
        return self.gen_response()
    
    # presidential power related
    def pp_done_policy_peek(self, ack):
        self.requires_state(Stage.PERFORM_PRESIDENTIAL_POWER)
        self.board.advance_president()
        self.shift_state(Stage.NEW_PRESIDENT)
        return self.gen_response()

    def pp_execute_player(self, player: str):
        self.requires_state(Stage.PERFORM_PRESIDENTIAL_POWER)
        self.board.execute_player(player)
        self.board.advance_president()
        self.shift_state(Stage.NEW_PRESIDENT)
        return self.gen_response()
