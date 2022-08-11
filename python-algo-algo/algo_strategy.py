from calendar import c
import gamelib
import random
import math
from sys import maxsize, stderr
import json
# import tensorflow
from simulator import Simulator
from helpers import *

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
        self.next_attack_check = -1
        self.early_game = True
        global EARLY_GAME_MAP, MID_GAME_MAP
        EARLY_GAME_MAP = \
        {"wall_l1" : [[3, 11], [5, 11], [22, 11], [24, 11], [4, 10], [6, 10], [21, 10], [23, 10], [6, 9], [21, 9], [7, 8], [20, 8], [7, 7], [20, 7]],
        "inters" : [[3, 10], [24, 10], [6, 7], [21, 7]]}
        MID_GAME_MAP = \
        {"wall_l2" :[[0, 13], [1, 13], [23, 13], [26, 13], [27, 13], [19, 12], [23, 11], [22, 10], [21, 9]]
        ,"wall_l1" : [[3, 13], [24, 13], [25, 13], [4, 12], [26, 12], [5, 11], [6, 10], [18, 10], [7, 9], [17, 9], [8, 8], [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8], [15, 8], [16, 8]]
        ,"turret_l1" : [[2, 13], [3, 12], [20, 12], [24, 12], [25, 12], [19, 11]]
        ,"cost": 0
        , "wall_l2_2": [[3, 13], [4, 13], [24, 13], [25, 13], [4, 12], [5, 12], [5, 11], [20, 8]]
        ,"support_l1": [[13, 6], [14, 6], [15, 6], [14, 5]]}
        MID_GAME_MAP["cost"] = 2*len(MID_GAME_MAP["wall_l2"]) + 0.5*len(MID_GAME_MAP["wall_l1"]) + 6*len(MID_GAME_MAP["turret_l1"])
        gamelib.debug_write(f"Mid game map cost: {MID_GAME_MAP['cost']}")
        

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
        self.switch_to_mid_game(game_state)
        if self.early_game:
            self.interceptor_stall(game_state)
        else:
            self.build_defences(game_state)

        self.plan_attack(game_state)
        

    def interceptor_stall(self, game_state:gamelib.GameState):
        game_state.attempt_spawn(WALL, EARLY_GAME_MAP["wall_l1"])
        game_state.attempt_spawn(INTERCEPTOR, EARLY_GAME_MAP["inters"], 1)
        

    def switch_to_mid_game(self, game_state:gamelib.GameState):
        if not self.early_game:
            return
        sp_avail = game_state.get_resource(SP)
        for wall_loc in EARLY_GAME_MAP["wall_l1"]:
            sp_avail += compute_refund(game_state, wall_loc)

        if sp_avail >= MID_GAME_MAP['cost']:
            self.early_game = False
            game_state.attempt_remove(EARLY_GAME_MAP["wall_l1"])
            self.next_attack_check = game_state.turn_number +1


        




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
                

    def build_defences(self, game_state:gamelib.GameState):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l1'])
        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l2'])
        game_state.attempt_spawn(TURRET, MID_GAME_MAP['turret_l1'])
        game_state.attempt_upgrade(MID_GAME_MAP['wall_l2'])
        for wall_loc in MID_GAME_MAP["wall_l2_2"]:
            game_state.attempt_spawn(WALL, wall_loc)
            game_state.attempt_upgrade(wall_loc)
        game_state.attempt_spawn(SUPPORT, MID_GAME_MAP["support_l1"])


    def plan_attack(self, game_state:gamelib.GameState):
        if not (self.next_attack_check == game_state.turn_number):
            return
        gamelib.debug_write(10)

        mp = game_state.get_resource(MP)
        spawn_location_options = [[4, 9], [13, 0], [14, 0]]

        # check demos first
        best_loc = [13, 0]
        best_damage = 0
        best_turrets = 0
        best_structures = 0
        for loc in spawn_location_options:
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, int(mp//3), loc]]
            sim.place_mobile_units(scenario)
            dmg, turrets, structures = sim.simulate()
            if dmg > best_damage or turrets > best_turrets or structures>= best_structures:
                best_loc = loc
                best_damage = dmg
                best_turrets = turrets
                best_structures = structures

        # check if we should just sent scouts
        mode = DEMOLISHER
        sim = Simulator(self.config, game_state)
        scenario = [[SCOUT, game_state.number_affordable(SCOUT), best_loc]]
        sim.place_mobile_units(scenario)
        dmg, turrets, structures= sim.simulate()
        if dmg > best_damage or turrets > best_turrets or structures>= best_structures:
            mode = SCOUT
            best_loc = loc
            best_damage = dmg
            best_turrets = turrets
            best_structures = structures

        # what if we wait one more round
        # sim = Simulator(self.config, game_state)
        # scenario = [[DEMOLISHER, game_state.project_future_MP()//3, best_loc]]
        # sim.place_mobile_units(scenario)
        # dmg = sim.simulate()
        # if dmg > best_damage:
        #     self.next_attack_check += 1
        #     return

        # check hybrid(s)
        hybrid_locs = [[[6,7],[14,0]], [[5,8], [6,7]]]
        demo_count = int(mp//4)
        scout_count = int(mp - demo_count*3)
        best_hybrid_loc = hybrid_locs[0]
        best_hybrid_damage = 0
        best_hybrid_structures = 0
        best_hybrid_turrets = 0
        for demo_loc, scout_loc in hybrid_locs:
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, demo_count, demo_loc], [SCOUT, scout_count, scout_loc]]
            sim.place_mobile_units(scenario)
            dmg, turrets, structures= sim.simulate()


            if dmg > best_hybrid_damage or turrets > best_hybrid_turrets or structures>= best_hybrid_structures:
                best_hybrid_loc = [demo_loc, scout_loc]
                best_hybrid_damage = dmg
                best_hybrid_turrets = turrets
                best_hybrid_structures = structures
        
        if best_hybrid_damage > best_damage or best_hybrid_turrets > best_turrets or best_hybrid_structures > best_structures:
            game_state.attempt_spawn(DEMOLISHER, best_hybrid_loc[0], demo_count)
            game_state.attempt_spawn(SCOUT, best_hybrid_loc[1], scout_count)
            self.next_attack_check += 2

        else:
            self.next_attack_check += 1
            if best_damage == 0 and best_structures == 0:
                return

            # if mode == SCOUT:
            #     self.next_attack_check += 4
            # else:
            self.next_attack_check += 2
            game_state.attempt_spawn(mode, best_loc, 1000)
        
        




if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
