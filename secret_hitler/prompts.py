"""secret_hitler.prompts

A Prompt encapsulates a request for user action, along with the available choices the user can respond with.
"""

from typing import Callable, Dict, List

from secret_hitler.player import Player


class Prompt:
    def __init__(self, method: str, prompt_str: str, choices: List[str]):
        self.method = method
        self.prompt_str = prompt_str
        self.choices = choices

    def __str__(self):
        return f"{self.method}({self.prompt_str}): {str(self.choices)}"


class Prompts:
    def __init__(self):
        self.prompts: Dict[str, Prompt] = dict()

    def add(self, player: Player, method: Callable, prompt_str: str, choices: List[str]) -> None:
        self.prompts[player.name] = Prompt(method.__name__, prompt_str, choices)

    def get_dict(self) -> Dict[str, Prompt]:
        return self.prompts
