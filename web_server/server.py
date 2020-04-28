import json
import os
from typing import Dict, List
import uuid

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

from secret_hitler.game import Game
from secret_hitler.prompts import Prompt
from secret_hitler.exceptions import GameError

games: Dict[str, "GameHandle"] = dict()

MAX_GAMES_ALLOWED = 1


class RequestError(Exception):
    pass


class GameHandle:
    def __init__(self, host: str):
        self.host: str = host                            # player_name of host
        self.game: Game = Game()                         # game server instance
        self.players: Dict[str, str] = dict()            # player_id -> player_name
        self.handles: Dict[str, WSHandler] = dict()      # player_id -> ws_handle
        self.ids: Dict[str, str] = dict()                # player_name -> player_id
        self.prompts: Dict[str, Prompt] = dict()         # player_name -> secret_hitler.Prompt
        self.has_begun: bool = False                     # has the game begun?

    def add_player(self, player: str, ws_handle):
        self.game.add_player(player)
        player_id = str(uuid.uuid4())
        self.players[player_id] = player
        self.handles[player_id] = ws_handle
        self.ids[player] = player_id

        # broadcast updated player list to everyone
        for player_id in self.players.keys():
            self.handles[player_id].send_state_update({
                "players": list(self.players.values())
            })

        return player_id

    def update_ws_handle(self, player_id: str, ws_handle):
        self.handles[player_id] = ws_handle

    def get_identity(self, player_id: str):
        return self.game.get_identity(self.players[player_id])

    def get_full_state(self):
        return self.game.get_full_state()

    def update_prompts(self, prompts):
        print("updating prompts to: " + str(prompts))
        # update internal prompt store
        self.prompts = prompts
        # send prompt to users who need prompts
        for prompt_player in prompts:
            self.handles[self.ids[prompt_player]].send_new_prompt(prompts[prompt_player])

    def begin_game(self):
        (prompts, state_updates) = self.game.begin_game()
        self.has_begun = True
        # send prompts
        self.update_prompts(prompts)
        # send identities to every player. Broadcast game_begun & full_state (ignore state_updates)
        full_state = self.get_full_state()
        for player_id in self.players.keys():
            self.handles[player_id].send_player_identity(self.game.get_identity(self.players[player_id]))
            self.handles[player_id].send_game_begun()
            self.handles[player_id].send_state_update(full_state)

    def perform_action(self, player_id, action, choice):
        # check if user is authorized
        if self.players[player_id] not in self.prompts:
            raise RequestError("Cannot perform request. Unauthorized to do so.")
        (prompts, state_updates) = self.game.perform_action(action, choice)

        if prompts:
            self.update_prompts(prompts)

        if state_updates:
            # send state updates to everyone
            for ws in self.handles.values():
                ws.send_state_update(state_updates)

    def get_prompt_of_player(self, player_id):
        player = self.players[player_id]
        if player not in self.prompts:
            return None
        return self.prompts[player]


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.game = None
        self.player_id = None
        print("new ws connection!")

    def on_close(self):
        print("connection closed")

    def check_origin(self, origin):
        return True

    def on_message(self, message):
        try:
            request = json.loads(message)
            self.ensure_properties(request, ["type"])

            if request["type"] == "new_game":
                self.ensure_properties(request, ["host"])
                if len(games) >= MAX_GAMES_ALLOWED:
                    self.respond_to_error("Cannot create game. Server at max capacity.")
                new_game_id = str(uuid.uuid4())
                self.game = GameHandle(request["host"])
                self.player_id = self.game.add_player(request["host"], self)
                games[new_game_id] = self.game
                self.respond_to_success("Game created successfully.")
                self.send_game_id(new_game_id)
                self.send_player_id()
                return

            if request["type"] == "reconnect":
                self.game = self.safe_get_game(request)
                self.safe_get_player(request)  # makes sure player_id exists in self.game
                self.player_id = request["player_id"]
                self.game.update_ws_handle(self.player_id, self)
                if self.game.has_begun:
                    # send game_begun to send client into game proper
                    self.send_game_begun()
                    # send full state to get client up to date
                    self.send_state_update(self.game.get_full_state())
                    self.send_player_identity()
                    # send current prompt if there exists one
                    self.send_new_prompt(self.game.get_prompt_of_player(self.player_id))
                else:
                    # send player_id to send client into waiting room
                    self.send_player_id()
                    # if player is host, send is_host
                    if self.game.host == self.game.players[self.player_id]:
                        self.send_is_host()
                    # send waiting room players
                    self.send_state_update({
                        "players": list(self.game.players.values())
                    })
                return

            if request["type"] == "join_game":
                self.game = self.safe_get_game(request)
                self.ensure_properties(request, ["player_name"])
                if request["player_name"] in self.game.players.values():
                    self.respond_to_error("Cannot join. User name already exists in game.")
                self.player_id = self.game.add_player(request["player_name"], self)
                self.respond_to_success(f"Joined game. Currently {len(self.game.players)} players in game.")
                self.send_game_id(request["game_id"])
                self.send_player_id()
                return

            if request["type"] == "begin_game":
                self.game.begin_game()
                return

            if request["type"] == "user_action":
                self.ensure_properties(request, ["action", "choice"])
                self.game.perform_action(self.player_id, request["action"], request["choice"])
                action = request["action"]
                self.respond_to_success(f"Action {action} performed successfully.")

        except RequestError as err:
            self.respond_to_error(str(err))
            self.recover_from_execption()
        except GameError as err:
            self.respond_to_error(str(err))
            self.recover_from_execption()
        # except Exception as err:
        #     self.respond_to_error("Unknown exception occurred: " + str(err))

    def recover_from_execption(self):
        if self.game is None:
            return
        # TODO: better recovery from all kinds of states
        if self.game.has_begun:
            # send full state to get client up to date
            self.send_state_update(self.game.get_full_state())
            self.send_player_identity()
            # send current prompt if there exists one
            self.send_new_prompt(self.game.get_prompt_of_player(self.player_id))

    def safe_send(self, obj):
        try:
            self.write_message(json.dumps(obj))
        except Exception as err:
            print("Encountered error during ws send: " + str(err))

    def send_player_identity(self, identity=None):
        identity = identity or self.game.get_identity(self.player_id)
        self.send_state_update({
            "identity": identity
        })

    def send_game_begun(self):
        self.safe_send({
            "type": "game_begun"
        })

    def send_state_update(self, updates):
        print("sending update: " + str(updates))
        self.safe_send({
            "type": "state_update",
            "updates": updates
        })

    def send_new_prompt(self, prompt):
        print("sending prompt: " + str(prompt))
        if prompt:
            self.safe_send({
                "type": "prompt",
                "action": prompt.method,
                "prompt": prompt.prompt_str,
                "choices": prompt.choices
            })

    def send_game_id(self, game_id):
        self.safe_send({
            "type": "game_id",
            "game_id": game_id
        })

    def send_player_id(self):
        self.safe_send({
            "type": "player_id",
            "player_id": self.player_id
        })

    def send_is_host(self):
        self.safe_send({
            "type": "is_host"
        })

    def safe_get_game(self, request):
        self.ensure_properties(request, ["game_id"])
        if request["game_id"] not in games:
            raise RequestError("Game does not exist.")
        return games[request["game_id"]]

    def safe_get_player(self, request):
        self.ensure_properties(request, ["player_id"])
        if request["player_id"] not in self.game.players:
            raise RequestError("Player does not exist")
        return self.game.players[request["player_id"]]

    def ensure_properties(self, request, props: List[str]):
        for prop in props:
            if prop not in request:
                raise RequestError(f"Invalid Request. Did not find expected field {prop}.")

    def respond_to_error(self, reason: str):
        self.safe_send({
            "type": "error",
            "msg": reason
        })

    def respond_to_success(self, msg: str, data={}):
        response = {
            "type": "success",
            "msg": msg
        }
        response.update(data)
        self.safe_send(response)


application = tornado.web.Application([
    (r"/ws", WSHandler),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(__file__), "default_filename": "index.html"}),
])


if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(3737)
    print("Serving site at port 3737")
    tornado.ioloop.IOLoop.instance().start()
