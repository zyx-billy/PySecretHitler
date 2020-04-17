import os

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("new ws connection!")
    
    def on_message(self, message):
        print(f"message received: {message}. Replying with 42.")
        self.write_message("42")
    
    def on_close(self):
        print("connection closed")

    def check_origin(self, origin):
        return True

application = tornado.web.Application([
    (r"/ws", WSHandler),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(__file__), "default_filename": "index.html"}),
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(3737)
    print("Serving site at port 3737")
    tornado.ioloop.IOLoop.instance().start()
