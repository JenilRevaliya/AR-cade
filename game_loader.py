import os
import importlib.util
import inspect
from game_base import BaseGame

def load_games():
    """
    Scans the 'games/' directory for modules, finds classes that inherit from
    BaseGame, and returns them.
    """
    games = []
    # Ensure the 'games' directory exists
    if not os.path.isdir('games'):
        return games

    game_files = [f for f in os.listdir('games') if f.startswith('game_') and f.endswith('.py')]

    for game_file in game_files:
        module_name = game_file[:-3]
        spec = importlib.util.spec_from_file_location(module_name, os.path.join('games', game_file))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find all classes in the module that are subclasses of BaseGame
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseGame) and obj is not BaseGame:
                games.append(obj)

    return games