# PySecretHitler

A (non-official) Python adaptation of [the board game "Secret Hitler"](https://www.secrethitler.com/) (licensed under [CC BY–NC–SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)) so friends can play at home!

## Project Overview

- Core game logic implemented as a standalone python module `secret_hitler`.
- HTTP server written with [Tornado](https://github.com/tornadoweb/tornado).
- Interactive client-side (browser) view logic implemented with [React](https://github.com/facebook/react) (using JSX).
- Real-time two-way communication over WebSocket.

## Development Guide

System dependencies: Python 3.6 or higher

Create venv for development. Then enter it.
```
$ python -m venv <venv_dir>
$ source <venv_dir>/bin/activate
```

Install python package dependencies:
```
$ python -m pip install -r requirements.txt
```

Install package locally for development:
```
$ python -m pip install -e .
```
