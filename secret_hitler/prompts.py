from typing import List

from secret_hitler.player import Player

class Prompt:
    def __init__(self, method: str, prompt_str: str, choices: List[str]):
        self.method = method
        self.prompt_str = prompt_str
        self.choices = choices

class Prompts:
    def __init__(self):
        self.prompts = dict()

    def add(self, player: Player, method: str, prompt_str: str, choices: List[str]):
        self.prompts[player.name] = Prompt(method, prompt_str, choices)
