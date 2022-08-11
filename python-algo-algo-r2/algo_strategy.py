from calendar import c
from configparser import MissingSectionHeaderError
from stringprep import in_table_c21_c22
from tarfile import ExFileObject
import gamelib
import random
import math
from sys import maxsize, stderr
import json
# import tensorflow
from simulator import Simulator
from helpers import *
from collections import deque

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
        self.early_game = True
        global EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, EARLY_TO_MID_DIFF, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD

        EARLY_GAME_MAP = \
        {"wall_l1" : [[3, 11], [5, 11], [22, 11], [24, 11], [4, 10], [6, 10], [21, 10], [23, 10], [6, 9], [21, 9], [7, 8], [20, 8], [7, 7], [20, 7]]
        ,"turret_l1" : []
        ,"inters" : [[3, 10], [24, 10], [6, 7], [21, 7], [15,1]]
        }
        MID_GAME_MAP = \
        {"wall_l2" : [[0, 13], [1, 13], [23, 13], [26, 13], [27, 13], [4, 12], [21, 12], [5, 11], [23, 11]]
        ,"wall_l1" :[[23, 12], [6, 10], [7, 9], [18, 9], [8, 8], [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8], [15, 8], [16, 8], [17, 8]] + [[3, 13], [19, 10], [22, 10], [21, 9]]
        ,"turret_l1" : [[2, 13], [3, 12], [20, 12], [24, 12], [25, 12], [20, 11]]
        ,"cost": 0
        , "wall_l2_aux" : [[3, 13], [22, 10], [21, 9]]
        ,"support_l1": [[16, 6], [17, 6], [18, 6], [17, 5]]}
        MID_GAME_MAP["cost"] = 2*len(MID_GAME_MAP["wall_l2"]) + 0.5*len(MID_GAME_MAP["wall_l1"]) + 6*len(MID_GAME_MAP["turret_l1"])
        gamelib.debug_write(f"Mid game map cost: {MID_GAME_MAP['cost']}")

        MID_GAME_EXTRA_LEFT = \
        {"wall_l2" : [[5, 12], [6, 11]]
        ,"turret_l1" :[[2, 12], [4, 11], [4, 10]]
        }
        MID_GAME_EXTRA_RIGHT = \
        {"wall_l2": [[24, 13], [25, 13], [19, 12], [26, 12], [20, 8]]
        ,"turret_l1" : [[19, 11], [23, 10], [22, 9]]
        }

        EARLY_TO_MID_DIFF = \
        {"wall_l1": [wall for wall in EARLY_GAME_MAP["wall_l1"] if wall not in (MID_GAME_MAP["wall_l1"]+MID_GAME_MAP["wall_l2"])]
        }

        MID_GAME_DEFENCE =\
        {"inters_left" : [[2,11]]
        ,"inters_right" :[[24,10], [22,8]]
        }

        LATE_GAME_LEFT = \
        {"wall_l2": [[1, 12], [3, 11], [5, 10]]
        ,"turret_l1" : [[7,10], [8,9]]
        }
        LATE_GAME_RIGHT = \
        {"wall_l2": [[20,11], [19,10]]
        ,"turret_l1" : [[23, 12], [18, 9], [21, 8]]
        }
        LATE_GAME_SHIELD = \
        {"shield_l2": [[16, 11], [17, 11], [16, 10], [17, 10], [15, 9], [16, 9]]
        }

        self.damage_taken_tracker = deque()
        self.damage_tracker_memory = 5

        self.last_attack = -1
        self.target_stats = [0,1,0,0]
        self.predicted_stats = [0,0,0,0]
        self.last_stats = [0,0,0,0]
        self.period = 1
        self.max_period = 5
        

    """
    ====================================
    """

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        damage_events = events['damage']
        left, right = 0,0

        # Format: [loc(i,i), dmg(f), unittype(i), id(s), p_no(i)]
        for e in damage_events:
            if e[4] == 1: #owner is us
                if e[0][0] <= 13:
                    left += e[1]
                else:
                    right += e[1]

        death_events = events['death']
        for e in death_events:
            if e[4] == 2 and e[2] == 2:
                self.last_stats[1] += 1


        breach_events = events['breach']
        for e in breach_events:
            if e[4] == 2: #they breached us
                if e[0][0] <= 13:
                    left += e[1]*100
                else:
                    right += e[1]*100
            if e[4] == 1:
                self.last_stats[0] += 1
        
        self.damage_taken_tracker[-1][0] += left
        self.damage_taken_tracker[-1][1] += right
        # gamelib.debug_write(f"ACTION FRAME: {left} {right} number of events {len(damage_events)}")

        

    

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

        # prepare queue for next round
        self.damage_taken_tracker.append([0,0])
        if len(self.damage_taken_tracker) > self.damage_tracker_memory:
            self.damage_taken_tracker.popleft()

        game_state.submit_turn()

 
    def starter_strategy(self, game_state:gamelib.GameState):
        self.reflect_on_attack(game_state)
        self.switch_to_mid_game(game_state)
        if self.early_game:
            self.early_game_plan(game_state)
        else:
            ok = self.build_defences(game_state)
            if not ok:
                self.interceptor_defence(game_state)
            else:
                self.plan_attack(game_state)
            

    def reflect_on_attack(self, game_state:gamelib.GameState):
        if not game_state.turn_number-1 == self.last_attack:
            return

        if self.predicted_stats[0] >= 2* self.last_stats[0] and self.predicted_stats[1] >= 2* self.last_stats[1]:
            self.period = min(self.max_period, self.period+1)

        if self.last_stats[0] > 0:
            self.period = 1

        gamelib.debug_write(f"after reflection: period = {self.period}. predicted {self.predicted_stats} got {self.last_stats}")


    def early_game_plan(self, game_state:gamelib.GameState):
        if game_state.turn_number > 0:
            game_state.attempt_spawn(WALL, EARLY_GAME_MAP["wall_l1"])
        game_state.attempt_spawn(INTERCEPTOR, EARLY_GAME_MAP["inters"], 1)
        

    def switch_to_mid_game(self, game_state:gamelib.GameState):
        if not self.early_game:
            return
        sp_avail = game_state.get_resource(SP)
        for wall_loc in EARLY_TO_MID_DIFF["wall_l1"]:
            sp_avail += compute_refund(game_state, wall_loc)

        if sp_avail >= MID_GAME_MAP['cost']:
            self.early_game = False
            if EARLY_TO_MID_DIFF["wall_l1"]:
                game_state.attempt_remove(EARLY_TO_MID_DIFF["wall_l1"])
            self.next_attack_check = game_state.turn_number +1


        
    def interceptor_defence(self, game_state:gamelib.GameState):
        left, right = self.damage_taken(game_state)
        mp = game_state.get_resource(MP)
        if left > right:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_left"], max(5, int(mp/2)))
        else:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][0], 1)
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][1], max(5, int(mp/2)))



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
                

    def rush_l2(self, game_state:gamelib.GameState, loc_list, type):
        n = 0
        up = 0
        for loc in loc_list:
            n += game_state.attempt_spawn(type, loc)
            up += game_state.attempt_upgrade(loc)
        return n, up


    def build_defences(self, game_state:gamelib.GameState):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l1'])
        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l2'])
        
        turrets_undone = 0
        for turret in MID_GAME_MAP['turret_l1']:
            turrets_undone += (not game_state.contains_stationary_unit(turret))
        
        n = game_state.attempt_spawn(TURRET, MID_GAME_MAP['turret_l1'])
        # if not complete, panic
        if n == 0 and turrets_undone > 0:
            return False

        n = game_state.attempt_upgrade(MID_GAME_MAP['wall_l2'])
        # if not complete, panic
        if n == 0 and game_state.get_resource(SP) < 1.5:
            return False
        game_state.attempt_upgrade(MID_GAME_MAP['wall_l2_aux'])

        # Phase 1 done

        left, right = self.damage_taken(game_state)
        gamelib.debug_write(f"Damage: {left}, {right}")

        threshold = 200
        if left < threshold and right < threshold:
            game_state.attempt_spawn(SUPPORT, MID_GAME_MAP["support_l1"])
            return True
        if left > right:
            extra_first = MID_GAME_EXTRA_LEFT
            extra_second = MID_GAME_EXTRA_RIGHT
        else:
            extra_first = MID_GAME_EXTRA_RIGHT
            extra_second = MID_GAME_EXTRA_LEFT

        n = game_state.attempt_spawn(TURRET, extra_first["turret_l1"])
        if n == 0 and game_state.get_resource(MP) <= 6:
            return True
        
        self.rush_l2(game_state, extra_first["wall_l2"], WALL)
        
        if left < threshold or  right < threshold:
            game_state.attempt_spawn(SUPPORT, MID_GAME_MAP["support_l1"])

        self.rush_l2(game_state, extra_second["wall_l2"], WALL)

        
        n, up = self.rush_l2(game_state, LATE_GAME_SHIELD["shield_l2"], SUPPORT)
        if n == 0 and up == 0:
            return True
        # even more defences if possible
        
        if left > right:
            extra_first = LATE_GAME_LEFT
            extra_second = LATE_GAME_RIGHT
        else:
            extra_first = LATE_GAME_RIGHT
            extra_second = LATE_GAME_LEFT
        
        n = game_state.attempt_spawn(TURRET, extra_first["turret_l1"])
        if n == 0 and game_state.get_resource(MP) <= 6:
            return True
        
        self.rush_l2(game_state,  extra_first["wall_l2"], WALL)
        self.rush_l2(game_state,  extra_second["wall_l2"], WALL)
        return True


    def damage_taken(self, game_state:gamelib.GameState):
        weights = [0.1, 0.1, 0.25, 0.4, 1]
        tot_left, tot_right = 0, 0

        for t in range(min(game_state.turn_number, self.damage_tracker_memory)):
            left, right = self.damage_taken_tracker.popleft()
            tot_left += left * weights[t]
            tot_right += right * weights[t]
            self.damage_taken_tracker.append([left, right])
        return tot_left, tot_right


    # True if new is better
    def compare_stats(self, best_stats, best_locs, new_stats,new_locs):
        best_dmg, best_tur, best_strct, best_costdmg = best_stats
        dmg, tur, strct, costdmg = new_stats
        if costdmg > best_costdmg or dmg > best_dmg:
            return True, new_stats, new_locs
        return False, best_stats, best_locs


    def plan_attack(self, game_state:gamelib.GameState):
        if game_state.turn_number < self.last_attack + self.period:
            return

        mp = game_state.get_resource(MP)
        spawn_location_options = [[4, 9], [13, 0], [14, 0]]
        attack = False
        # check demos first
        best_loc = spawn_location_options[-1]
        best_stats = self.target_stats
        for loc in spawn_location_options:
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, int(mp//3), loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            better, best_stats, best_loc = self.compare_stats(best_stats, best_loc, stats, loc)
            attack = attack or better

        # check if we should just sent scouts
        mode = DEMOLISHER
        sim = Simulator(self.config, game_state)
        scenario = [[SCOUT, game_state.number_affordable(SCOUT), best_loc]]
        sim.place_mobile_units(scenario)
        stats = sim.simulate()
        better, best_stats, best_loc= self.compare_stats(best_stats, best_loc, stats, best_loc)
        if better:
            mode = SCOUT
            attack = attack or better

        # check hybrid(s)
        hybrid_locs = [[[6,7],[14,0]], [[5,8], [6,7]]]
        demo_count = int(mp//4)
        scout_count = int(mp - demo_count*3)
        best_hybrid_loc = hybrid_locs[0]
        best_hybrid_stats = self.target_stats
        for locs in hybrid_locs:
            demo_loc, scout_loc = locs
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, demo_count, demo_loc], [SCOUT, scout_count, scout_loc]]
            sim.place_mobile_units(scenario)
            hybrid_stats = sim.simulate()
            better, best_hybrid_stats, best_hybrid_loc = self.compare_stats(best_hybrid_stats, best_hybrid_loc, hybrid_stats, locs)
            attack = attack or better

       
        better, best_stats, best_loc = self.compare_stats(best_hybrid_stats, best_hybrid_loc, best_stats, best_loc)
        if not attack:
            return
        
        self.predicted_stats = best_stats
        self.last_stats = [0,0,0,0]
        self.last_attack = game_state.turn_number

        gamelib.debug_write(f"TURN {game_state.turn_number}: {best_stats}, {best_loc}")
        if not better:
            game_state.attempt_spawn(DEMOLISHER, best_hybrid_loc[0], demo_count)
            game_state.attempt_spawn(SCOUT, best_hybrid_loc[1], scout_count)

        else:
            game_state.attempt_spawn(mode, best_loc, 1000)
        
        




if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
