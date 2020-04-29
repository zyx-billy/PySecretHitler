"""secret_hitler.stages

Describes the various stages of the game and the user actions that can be performed at each stage.
"""

from typing import Callable, List

from secret_hitler.board import Board, Tile, Faction, Vote, PresidentialPower
from secret_hitler.exceptions import GameError, UnreachableStateError, UnimplementedFeature
from secret_hitler.player import Player, Identity
from secret_hitler.prompts import Prompts


class IllegalActionError(GameError):
    """Base class for all exceptions thrown while performing a user action"""
    def __init__(self, stage: "Stage", action_name: str, reason: str):
        self.stage = stage
        self.action_name = action_name
        self.reason = reason
        super().__init__(f"Cannot perform action {action_name} at state {type(stage).__name__}: {reason}")


# type alias for user action handler methods
ActionHandler = Callable[["Stage", str, str], "Stage"]


class Stage:
    """Base classs for all game stages
    Derived concrete stages must:
    - call this base class's __init__ method
    - override the prompts method
    - implement user actions
    """
    all_stages: List["Stage"] = []
    user_actions: List[ActionHandler] = []

    def __init__(self, board: Board):
        self.board: Board = board

    def perform_action(self, action: str, choice: str) -> "Stage":
        if (not hasattr(self, action)) or (getattr(self, action).__func__ not in self.user_actions):
            raise IllegalActionError(self, action, "Action does not exist")
        self._current_action = getattr(self, action)
        return self._current_action(choice)

    def signal_illegal_action(self, reason: str):
        raise IllegalActionError(self, self._current_action.__name__ if self._current_action else "", reason)

    def prompts(self) -> Prompts:
        """Returns the user prompts for each player.
        Will only be called once per stage instance (immediately after __init__).
        """
        return Prompts()


# decorators for registering stages and their actions
def game_stage(cls):
    """register cls as a game stage and register its user actions"""
    Stage.all_stages.append(cls)
    cls.user_actions = []
    for method in cls.__dict__.values():
        if hasattr(method, "is_user_action"):
            cls.user_actions.append(method)
    return cls


def user_action(f):
    """mark f as a user_action"""
    f.is_user_action = True
    return f


# concrete stages of the game
@game_stage
class RevealIdentities(Stage):
    def __init__(self, board: Board):
        super().__init__(board)
        self.num_identity_acks = 0

    def prompts(self) -> Prompts:
        prompts = Prompts()
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
                        method=self.ack_identity,
                        prompt_str=f"You are: {player.identity.value}." + teammate_info,
                        choices=["Got it!"])
        return prompts

    @user_action
    def ack_identity(self, ack: str) -> Stage:
        self.num_identity_acks += 1
        if self.num_identity_acks == len(self.board.players):
            return NewPresident(self.board, need_advance_president=False)
        return self


@game_stage
class NewPresident(Stage):
    def __init__(self, board: Board, need_advance_president=True):
        super().__init__(board)
        if need_advance_president:
            self.board.advance_president()

    def prompts(self) -> Prompts:
        prompts = Prompts()
        # president nominate chancellor
        prompts.add(self.board.get_president(),
                    method=self.nominate_chancellor,
                    prompt_str="Nominate your chancellor",
                    choices=[p.name for p in self.board.players])
        return prompts

    @user_action
    def nominate_chancellor(self, nominee: str) -> Stage:
        if nominee == self.board.get_president().name:
            self.signal_illegal_action("Chancellor cannot be the same as current president")
        if self.board.prev_chancellor and nominee == self.board.prev_chancellor.name:
            self.signal_illegal_action("Chancellor cannot be the same as previous chancellor")
        if self.board.prev_president and nominee == self.board.prev_president.name and len(self.board.players) > 5:
            self.signal_illegal_action("Chancellor cannot be the same as previous president")
        nominated_chancellor = self.board.get_player(nominee)
        return ChancellorNominated(self.board, nominated_chancellor)


@game_stage
class ChancellorNominated(Stage):
    def __init__(self, board: Board, nominee: Player):
        super().__init__(board)
        self.nominee: Player = nominee
        self.votes: List[Vote] = []

    def prompts(self) -> Prompts:
        prompts = Prompts()
        # everyone votes
        for player in self.board.players:
            prompts.add(player,
                        method=self.vote_for_chancellor,
                        prompt_str=f"Vote for chancellor: {self.nominee.name}",
                        choices=["ja", "nein"])
        return prompts

    @user_action
    def vote_for_chancellor(self, vote: str) -> Stage:
        self.votes.append(Vote(vote))

        if len(self.votes) < len(self.board.players):
            # NOT done voting
            return self

        # done voting
        if self.votes.count(Vote.JA) > (len(self.board.players) // 2):
            # vote passed
            self.board.establish_new_chancellor(self.nominee)
            return PresidentDecidesLegislation(self.board)

        # vote did not pass, move on to a new president
        # TODO: implement election tracker
        return NewPresident(self.board)


@game_stage
class PresidentDecidesLegislation(Stage):
    def __init__(self, board: Board):
        super().__init__(board)
        self.drawn_tiles: List[Tile] = self.board.draw_three_tiles()

    def prompts(self) -> Prompts:
        prompts = Prompts()
        # president discards a tile
        prompts.add(self.board.get_president(),
                    method=self.president_discards_tile,
                    prompt_str="Discard a policy tile",
                    choices=[t.value for t in self.drawn_tiles])
        return prompts

    @user_action
    def president_discards_tile(self, tile: str) -> Stage:
        self.board.discard_tile(self.drawn_tiles, Tile(tile))
        return ChancellorDecidesLegislation(self.board, self.drawn_tiles)


@game_stage
class ChancellorDecidesLegislation(Stage):
    def __init__(self, board: Board, remaining_tiles: List[Tile]):
        super().__init__(board)
        self.remaining_tiles: List[Tile] = remaining_tiles

    def prompts(self) -> Prompts:
        prompts = Prompts()
        # chancellor discards a tile
        prompts.add(self.board.chancellor,
                    method=self.chancellor_discards_tile,
                    prompt_str="Discard a policy tile",
                    choices=[t.value for t in self.remaining_tiles])
        return prompts

    @user_action
    def chancellor_discards_tile(self, tile: str) -> Stage:
        self.board.discard_tile(self.remaining_tiles, Tile(tile))
        # enact tile
        selected_policy = self.remaining_tiles[0]
        self.board.enact_policy(selected_policy)

        # check winner status
        winner = self.board.get_winner()
        if winner is not None:
            return GameOver(self.board, winner)

        # check if exists presidential power if policy is a fascist policy
        if selected_policy == Tile.FASCIST_POLICY:
            pp = self.board.get_latest_presidential_power()
            if pp is not None:
                return PerformPresidentialPower(self.board, pp)

        # no winner and no presidential power, move on to new president
        return NewPresident(self.board)


@game_stage
class PerformPresidentialPower(Stage):
    def __init__(self, board: Board, power: PresidentialPower):
        super().__init__(board)
        self.power: PresidentialPower = power

    def prompts(self) -> Prompts:
        prompts = Prompts()
        # dependent on the presidential power
        if self.power is None:
            raise UnreachableStateError("Unexpectedly entered presidentail_power stage")
        # case on presidential power
        if self.power == PresidentialPower.INVESTIGATE_LOYALTY:
            raise UnimplementedFeature("Presidential Power: investigate loyalty")
        elif self.power == PresidentialPower.CALL_SPECIAL_ELECTION:
            raise UnimplementedFeature("Presidential Power: call special election")
        elif self.power == PresidentialPower.POLICY_PEEK:
            top_three_tiles_str = ", ".join([t.value for t in self.board.peek_top_three_tiles()])
            prompts.add(self.board.get_president(),
                        method=self.done_policy_peek,
                        prompt_str=f"The top three tiles are: {top_three_tiles_str}",
                        choices=["Got it!"])
        elif self.power == PresidentialPower.EXECUTION:
            prompts.add(self.board.get_president(),
                        method=self.execute_player,
                        prompt_str=f"Execute one a player",
                        choices=[p.name for p in self.board.players])
        else:
            raise UnreachableStateError("Invalid presidential power: " + str(self.power))
        return prompts

    def power_to_action(self, power: PresidentialPower):
        if power == PresidentialPower.POLICY_PEEK:
            return self.done_policy_peek
        elif power == PresidentialPower.EXECUTION:
            return self.execute_player

    @user_action
    def done_policy_peek(self, ack: str) -> Stage:
        return NewPresident(self.board)

    @user_action
    def execute_player(self, player: str) -> Stage:
        self.board.execute_player_and_advance_president(player)
        return NewPresident(self.board, need_advance_president=False)


@game_stage
class GameOver(Stage):
    def __init__(self, board: Board, winner: Faction):
        super().__init__(board)

    def prompts(self) -> Prompts:
        # empty prompts halts the game
        return Prompts()
