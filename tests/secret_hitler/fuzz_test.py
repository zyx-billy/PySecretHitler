"""fuzz test for secret_hitler"""

import random
import time
from typing import List

from secret_hitler.game import Game
from secret_hitler.stages import IllegalActionError, GameOver

MAX_NUM_PLAYERS = 6
MIN_NUM_PLAYERS = 5


def test_fuzz(cmdseedopt, repeat_id):
    seed = (cmdseedopt or int(time.time())) * repeat_id
    print(f"Starting fuzz test with PRNG seed = {str(seed)}")
    random.seed(seed)

    # game setup
    num_players = random.randint(MIN_NUM_PLAYERS, MAX_NUM_PLAYERS)
    player_names = [f"p{i}" for i in range(num_players)]
    game = Game()
    for name in player_names:
        game.add_player(name)

    (prompts, _) = game.begin_game()

    while prompts is not None and len(prompts) > 0:
        print(f"[New Stage] {type(game.stage).__name__}")
        # perform user actions in random order
        actionable_users: List[str] = list(prompts.keys())
        random.shuffle(actionable_users)
        for user in actionable_users:
            action = prompts[user].method
            choices = prompts[user].choices
            # perform action with the first allowable random choice
            random.shuffle(choices)
            able_to_perform_action = False
            for choice in choices:
                try:
                    (new_prompts, _) = game.perform_action(action, choice)
                    able_to_perform_action = True
                except IllegalActionError:
                    pass
                if able_to_perform_action:
                    print(f"[Action Success] {user}: {action}({choice})")
                    break
            assert able_to_perform_action
        prompts = new_prompts

    assert type(game.stage) == GameOver


if __name__ == "__main__":
    test_fuzz(None, 1)
