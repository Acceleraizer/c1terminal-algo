import gamelib
import random
import math
import warnings
from sys import maxsize, stderr
import json
# import tensorflow
from simulator import Simulator, timer

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""
class StructureInfo:
    def __init__(self, gameunit, loc):
        self.x = loc[0]
        self.y = loc[1]
        self.health = gameunit.health
        self.owner = gameunit.player_index
        self.type = gameunit.unit_type
        self.pending_removal = gameunit.pending_removal
        self.upgraded = gameunit.upgraded
    
    def __str__(self):
        return f"[{self.x},{self.y}], HP:{self.health}, Player:{self.owner}, Type:{self.type}, Remove:{self.pending_removal}, Upgrade:{self.upgraded}"

class AlgoStrategy(gamelib.AlgoCore):

    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 3)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state:gamelib.GameState):
        if (game_state.turn_number == 5):
            # crash
            a = 1/0
        sim = Simulator(self.config, game_state)
        scenario = [[SCOUT, 10, [6, 7]]]
        sim.place_mobile_units(scenario)
        sim.simulate()

        # Todo: debug log a bunch of things to check state representation
        # board_state = self.parse_board_state(game_state)
        # structures = board_state[-1]
        # if structures:
        #     gamelib.debug_write(structures[0])
        # gamelib.debug_write(board_state)


    def parse_board_state(self, game_state : gamelib.GameState):
        my_resources = game_state.get_resources(0)
        their_resources = game_state.get_resources(1)
        my_health = game_state.my_health
        their_health = game_state.enemy_health
        board = []
        # This only parses the static board state, so there should be no mobile units
        for cell in game_state.game_map:
            state = game_state.game_map[cell]
            if state:
                board.append(StructureInfo(state[0], cell))

        return [my_resources, their_resources, my_health, their_health, board]
                

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
