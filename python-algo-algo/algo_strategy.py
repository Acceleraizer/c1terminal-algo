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
        self.next_attack_check = 6

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state:gamelib.GameState):
        # if (game_state.turn_number == -1):
        #     # crash
        #     a = 1/0
        # sim = Simulator(self.config, game_state)
        # scenario = [[SCOUT, game_state.number_affordable(SCOUT), [6, 7]]]
        # sim.place_mobile_units(scenario)
        # expected_dmg = sim.simulate()
        # gamelib.debug_write(f"Prediction: {expected_dmg} damage!")
        self.build_defences(game_state)
        self.maybe_spawn_interceptors()
        if game_state.turn_number < 4:
            game_state.attempt_spawn(INTERCEPTOR, [[1, 12], [26, 12]])
        else:
            # game_state.attempt_spawn(INTERCEPTOR, [[20, 6]])
            self.plan_attack(game_state)
        


    def plan_attack(self, game_state:gamelib.GameState):
        if not self.next_attack_check == game_state.turn_number:
            return
        mp = game_state.get_resource(MP)
        spawn_location_options = [[3,10], [13, 0], [14, 0]]
        # check demos first
        best_loc = []
        best_damage = 0
        for loc in spawn_location_options:
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, mp // 3, loc]]
            sim.place_mobile_units(scenario)
            dmg = sim.simulate()
            if dmg >= best_damage:
                best_loc = loc
                best_damage = dmg


        # check if we should just sent scouts
        mode = DEMOLISHER
        sim = Simulator(self.config, game_state)
        scenario = [[SCOUT, game_state.number_affordable(SCOUT), best_loc]]
        sim.place_mobile_units(scenario)
        dmg = sim.simulate()
        if dmg > best_damage:
            mode = SCOUT

        # what if we wait one more round
        # sim = Simulator(self.config, game_state)
        # scenario = [[DEMOLISHER, game_state.project_future_MP()//3, best_loc]]
        # sim.place_mobile_units(scenario)
        # dmg = sim.simulate()
        # if dmg > best_damage:
        #     self.next_attack_check += 1
        #     return

        if mode == SCOUT:
            self.next_attack_check += 4
        else:
            self.next_attack_check += 3
        game_state.attempt_spawn(mode, best_loc, 1000)



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
                

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations_primary = [[25, 12], [3, 11], [18, 10], [17, 9]]
        turret_locations_secondary = [[2, 11], [24, 11], [16, 8], [15, 7]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations_primary)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations_key = [[2, 13], [25, 13], [18, 11], [19, 11]]
        wall_locations_key_2 = [[26, 13], [24, 12],[1, 13],[3, 12], [17, 10], [16, 9], [15, 8], [4,11], [19,10], [18,9]]
        wall_locations_path =  [[0, 13], [1, 13], [26, 13], [27, 13], [3, 12], [24, 12], [4, 11], [23, 11], [5, 10], [17, 10], [22, 10], [6, 9], [16, 9], [21, 9], [7, 8], [15, 8], [20, 8], [8, 7], [14, 7], [19, 7], [9, 6], [13, 6], [10, 6], [12, 6], [11, 6]]
        game_state.attempt_spawn(WALL, wall_locations_key + wall_locations_key_2+ wall_locations_path)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations_key)
        game_state.attempt_spawn(TURRET, turret_locations_secondary)
        game_state.attempt_upgrade(wall_locations_key_2)

        # Lastly, if we have spare SP, let's build some supports
        support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        game_state.attempt_upgrade(turret_locations_primary)
        game_state.attempt_upgrade(turret_locations_secondary)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def maybe_spawn_interceptors(self):
        pass
if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
