import json
import os
from typing import List
import uuid

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

from secret_hitler.game import Game
from secret_hitler.exceptions import GameError

games = dict()

MAX_GAMES_ALLOWED = 1

class RequestError(Exception):
    pass

class GameHandle:
    def __init__(self, host: str):
        self.host = host
        self.game = Game()
        self.players = dict()   # player_id -> player_name
        self.handles = dict()   # player_id -> ws_handle
        self.ids = dict()       # player_name -> player_id
        self.prompts = None     # player_name -> secret_hitler.Prompt

    def add_player(self, player: str, ws_handle):
        self.game.add_player(player)
        player_id = uuid.uuid4()
        self.players[player_id] = player
        self.handles[player_id] = ws_handle
        self.ids[player] = player_id

        # broadcast updated player list to everyone
        for player in self.players:
            self.handles[self.ids[player]].send_state_update({
                "players": list(self.players.keys())
            })
        
        return player_id
    
    def get_identity(self, player_id: str):
        return self.game.get_identity(self.players[player_id])
    
    def begin_game(self):
        self.game.begin_game()
        # send identities to every player
        for player in self.players:
            self.handles[self.ids[player]].send_new_prompt(self.game.get_identity(player))
    
    def perform_action(self, player, action, choice):
        # check if user is authorized
        if self.players[player] not in self.prompts:
            raise RequestError("Cannot perform request. Unauthorized to do so.")
        (prompts, state_updates) = getattr(self.game, action)(choice)

        # send state updates to everyone
        for ws in self.handles.values():
            ws.send_state_updates(state_updates)
        
        # update internal prompt store
        self.prompts = prompts
        # send prompt to users who need prompts
        for prompt_player in prompts:
            self.handles[self.ids[prompt_player]].send_new_prompt(prompts[prompt_player])
    
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
                    respond_to_error("Cannot create game. Server at max capacity.")
                new_game_id = uuid.uuid4()
                self.game = GameHandle(request["host"])
                self.player_id = self.game.add_player(request["host"], self)
                games[new_game_id] = self.game
                self.respond_to_success("Game created successfully.")
                self.send_game_id(new_game_id)
                return
            
            if request["type"] == "reconnect":
                self.game = safe_get_game(request)
                self.safe_get_player(request) # makes sure player_id exists in self.game
                self.player_id = request["player_id"]
                # send full state to get client up to date
                self.send_state_update(self.game.get_full_state())
                self.send_player_identity()
                # send current prompt if there exists one
                self.send_new_prompt(self.game.get_prompt_of_player(self.player_id))
                return
            
            if request["type"] == "join_game":
                self.game = safe_get_game(request)
                self.ensure_properties(request, ["player_name"])
                if request["player_name"] in self.game:
                    respond_to_error("Cannot join. User name already exists in game.")
                self.player_id = self.game.add_player(request["player_name"], self)
                self.respond_to_success(f"Joined game. Currently {len(self.game.players)} players in game.")
                self.send_player_id()
                return
            
            if request["type"] == "begin_game":
                self.game.begin_game()
                return
            
            if request["type"] == "user_action":
                self.ensure_properties(request, ["action", "choice"])
                self.game.perform_action(self.player, request["action"], request["choice"])
                action = request["action"]
                self.respond_to_success(f"Action {action} performed successfully.")

        except RequestError as err:
            self.respond_to_error(str(err))
        except GameError as err:
            self.respond_to_error(str(err))
        except Exception as err:
            self.respond_to_error("Unknown exception occurred: " + str(err))

    def send_player_identity(self, identity = None):
        identity = identity or self.game.get_identity(self.player_id)
        self.send_state_update({
            "identity": identity
        })

    def send_game_begun(self):
        self.write_message(json.dumps({
            "type": "game_begun"
        }))
    
    def send_state_update(self, updates):
        self.write_message(json.dumps({
            "type": "state_update",
            "updates": updates
        }))
    
    def send_new_prompt(self, prompt):
        self.write_message(json.dumps({
            "type": "prompt",
            "action": prompt.method,
            "prompt": prompt.prompt_str,
            "choices": prompt.choices
        }))

    def send_game_id(self, game_id):
        self.write_message(json.dumps({
            "type": "game_id",
            "game_id": game_id
        }))
    
    def send_player_id(self):
        self.write_message(json.dumps({
            "type": "player_id",
            "player_id": self.player_id
        }))

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
        self.write_message(json.dumps({
            "type": "error",
            "msg": reason
        }))
    
    def respond_to_success(self, msg: str, data = {}):
        response = {
            "type": "success",
            "msg": msg
        }
        response.update(data)
        self.write_message(json.dumps(response))


application = tornado.web.Application([
    (r"/ws", WSHandler),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(__file__), "default_filename": "index.html"}),
])


if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(3737)
    print("Serving site at port 3737")
    tornado.ioloop.IOLoop.instance().start()
