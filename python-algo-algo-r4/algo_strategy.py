from calendar import c
from configparser import MissingSectionHeaderError
from re import S
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
from copy import deepcopy

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
        global ALL_LAYOUTS
        global EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_FORTIFICATION, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, MID_GAME_EXTRA_SHIELD, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD
        global SINGLE_SPAWNS, HYBRID_SPAWNS
        global MID_GAME_MAP_COST
        
        EARLY_GAME_MAP = \
        {"wall_l2" : []
        ,"wall_l1" : []
        ,"turret_l1" : []
        ,"scouts": []#[[4,9], [7,4], [10,3]]
        ,"inters" : [[3,10], [7,6], [11,2], [18,4], [22, 8]]
        }
        MID_GAME_MAP = \
        {"wall_l2" : [[3, 13], [23, 13], [5, 12],  [22, 12]]
        ,"turret_l1" : [[4, 12], [19, 12], [24, 12]]
        ,"wall_l1" : [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13], [6, 11], [19, 11], [23, 11], [7, 10], [18, 10], [21, 10], [8, 9], [17, 9], [20, 9], [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8], [15, 8], [16, 8]]
        ,"support_l2": [[17, 12], [18, 12]]
        }
        MID_GAME_FORTIFICATION = \
        {"wall_l2" : [[16, 13], [19, 13], [22, 11], [18, 13], [20, 12], [21, 10], [20, 9]]
        ,"turret_l1" : [[23, 12], [18, 11]]
        }

        MID_GAME_EXTRA_LEFT = \
        {"wall_l2" : [[0, 13], [1, 13], [2, 13]] + [[6, 11], [7, 10], [8, 9]]
        ,"turret_l1" : [[1, 12], [2, 12], [3, 12]]
        }
        MID_GAME_EXTRA_RIGHT = \
        {"wall_l2": [[25, 13], [26, 13], [27, 13], [19, 8]] + [[19, 11], [18, 10], [17, 9]]
        ,"turret_l1" : [[17, 10], [22, 10], [21, 9], [17, 8]]
        }
        MID_GAME_EXTRA_SHIELD = \
        {"support_l2" : [[17, 11], [16, 10], [16, 9]]
        }
        MID_GAME_DEFENCE =\
        {"inters_left" : [[2,11]]
        ,"inters_right" :[[24,10], [22,8]]
        }

        LATE_GAME_LEFT = \
        {"wall_l2": [[7,10], [8,9]]
        ,"turret_l1" : [[1, 12], [3, 11], [5, 10]]
        }
        LATE_GAME_RIGHT = \
        {"wall_l2": [[20,11], [19,10]]
        ,"turret_l1" : [[17, 9], [22, 9], [21, 8]]
        }
        LATE_GAME_SHIELD = \
        {"shield_l2": [[15, 10], [15, 9], [14, 10], [14, 9], [13, 10], [13, 9], [12, 10], [12, 9]]
        ,"wall_l2" : [[15, 11], [13, 11], [14, 11], [12, 11]]
        }

        SINGLE_SPAWNS = \
        {"spawn": [[4, 9], [13, 0], [14, 0]]
        }
        HYBRID_SPAWNS = \
        {"spawn_scout" : [[6, 7], [5, 8]]
        ,"spawn_demos" : [[14, 0], [6, 7]]
        }

        ALL_LAYOUTS = [EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_FORTIFICATION, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, MID_GAME_EXTRA_SHIELD, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD] + \
        [SINGLE_SPAWNS, HYBRID_SPAWNS]

        self.damage_taken_tracker = deque()
        self.damage_tracker_memory = 5

        self.last_attack = -1
        self.target_stats = [0,1,0,0]
        self.predicted_stats = [0,0,0,0]
        self.enemy_last_health = 30
        self.last_stats = [0,0,0,0]
        self.period = 2
        self.min_period = 2
        self.max_period = 4
        self.left_risk, self.right_risk = 0, 0
        self.enemy_total_spending = [0, 0]
        self.enemy_total_income = [0, 0]
        self.enemy_last_resources = [35, 0]
        self.enemy_last_spending = [0, 0]
        self.enemy_last_income = [0, 0]
        

        # self.flip_all_layouts()

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
                self.enemy_last_income[SP] += 1
            # if e[4] == 1:
            #     self.last_stats[0] += 1
            #     gamelib.debug_write("We scored!")
        
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
        global TURN_STATE
        TURN_STATE = turn_state
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
        self.reflect(game_state)
        if game_state.turn_number > 0:
            self.switch_to_mid_game(game_state)
        if self.early_game:
            self.early_game_plan(game_state)
        else:
            ok = self.build_defences(game_state)
            if not ok:
                self.interceptor_defence(game_state)
        self.plan_attack(game_state)


    def compute_total_cost_of_layout(self, layout):
        global STRUCTURECOSTS
        STRUCTURECOSTS = [["wall_l1", 0.5], ["wall_l2", 2], ["turret_l1", 6], ["turret_l2", 12], ["support_l1", 4], ["support_l2", 6]]
        total = 0
        for key, cost in STRUCTURECOSTS:
            if key in layout:
                total += len(layout[key])*cost
        return total

    def compute_total_cost_of_layout_transition(self, before_layout, after_layout):
        return


    def flip_all_layouts(self):
        for layout in ALL_LAYOUTS:
            for k, ls in layout.items():
                for n in range(len(ls)):
                    ls[n] = [27 - ls[n][0], ls[n][1]]
                layout[k] = deepcopy(ls)
                


    def reflect(self, game_state:gamelib.GameState):
        # recompute stats
        self.last_stats[0] = self.enemy_last_health - game_state.enemy_health
        self.enemy_last_health = game_state.enemy_health

        self.left_risk, self.right_risk = self.damage_taken(game_state)

        self.enemy_last_income[SP] += 5 
        enemy_no_spend_sp = self.enemy_last_resources[SP] + self.enemy_last_income[SP]
        enemy_now_sp = game_state.get_resource(SP, 1)
        gamelib.debug_write(f"no: {enemy_no_spend_sp}, now: {enemy_now_sp}")

        self.enemy_last_spending[SP] = enemy_no_spend_sp - enemy_now_sp
        self.enemy_total_spending[SP]  += self.enemy_last_spending[SP]
        gamelib.debug_write(f"Spent: {self.enemy_total_spending[SP]}")

        self.reflect_on_attack(game_state)

        self.enemy_last_income[SP] = 0
        self.enemy_last_resources[SP] = enemy_now_sp



    def reflect_on_attack(self, game_state:gamelib.GameState):
        if not game_state.turn_number-1 == self.last_attack:
            return


        if self.predicted_stats[0] >= 2* self.last_stats[0] or self.predicted_stats[1] >= 2* self.last_stats[1]:
            self.period = min(self.max_period, self.period+1)

        if self.last_stats[0] > 0:
            self.period = self.min_period

        gamelib.debug_write(f"after reflection: period = {self.period}. predicted {self.predicted_stats} got {self.last_stats}")


    def early_game_plan(self, game_state:gamelib.GameState):
        if EARLY_GAME_MAP["turret_l1"]:
            game_state.attempt_spawn(TURRET, EARLY_GAME_MAP["turret_l1"])
        if EARLY_GAME_MAP["wall_l1"]:
            game_state.attempt_spawn(WALL, EARLY_GAME_MAP["wall_l1"])
        if EARLY_GAME_MAP["wall_l2"]:
            self.rush_l2(game_state, EARLY_GAME_MAP["wall_l2"], WALL)
        if EARLY_GAME_MAP["inters"]:
            game_state.attempt_spawn(INTERCEPTOR, EARLY_GAME_MAP["inters"], 1)
        if EARLY_GAME_MAP["scouts"]:
            game_state.attempt_spawn(SCOUT, EARLY_GAME_MAP["scouts"], 1)
        

    def switch_to_mid_game(self, game_state:gamelib.GameState):
        if not self.early_game:
            return
        sp_avail = game_state.get_resource(SP)
        cost = self.compute_total_cost_of_layout(MID_GAME_MAP)
        gamelib.debug_write(f"COST {cost}")
        if (sp_avail >= cost and self.enemy_total_spending[SP] >= 50) or sp_avail >= cost + 5:
            self.early_game = False
            self.decide_orientation(game_state)


    def mid_game_plan(self, game_state:gamelib.GameState):
        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l1'])
        game_state.attempt_spawn(WALL, MID_GAME_MAP['wall_l2'])
        
        turrets_undone = 0
        for turret in MID_GAME_MAP['turret_l1']:
            turrets_undone += (not game_state.contains_stationary_unit(turret))
        
        n = game_state.attempt_spawn(TURRET, MID_GAME_MAP['turret_l1'])
        n = game_state.attempt_upgrade(MID_GAME_MAP['wall_l2'])
        n = self.rush_l2(game_state, MID_GAME_MAP["support_l2"], SUPPORT)

        # Phase 1 done

        n = game_state.attempt_spawn(TURRET, MID_GAME_FORTIFICATION['turret_l1'])
        n, up = self.rush_l2(game_state, MID_GAME_FORTIFICATION["wall_l2"], WALL)
        # Phase 1.5 done
        return


    def decide_orientation(self, game_state:gamelib.GameState):
        gamelib.debug_write("DECIDING ORIENTATION")
        spawn_location_options = [[13, 27], [14, 27]]
        mp = 15
        cloned_game_state = gamelib.GameState(self.config, TURN_STATE)
        cloned_game_state._player_resources[0]["SP"] = 1000
        self.mid_game_plan(cloned_game_state)
        # check default oreintation
        best_loc_default = spawn_location_options[-1]
        best_stats_default = [0, 0, 0, 0]
        for loc in spawn_location_options:
            sim = Simulator(self.config, cloned_game_state, 1)
            scenario = [[DEMOLISHER, int(mp//3), loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            gamelib.debug_write(loc, stats)
            _, best_stats_default, best_loc_default = self.compare_stats(best_stats_default, best_loc_default, stats, loc)
        for loc in spawn_location_options:
            sim = Simulator(self.config, cloned_game_state, 1)
            scenario = [[SCOUT, mp, loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            gamelib.debug_write(loc, stats)
            _, best_stats_default, best_loc_default = self.compare_stats(best_stats_default, best_loc_default, stats, loc)

        # check mirror orientation
        best_loc_mirror = spawn_location_options[-1]
        best_stats_mirror = [0,0,0,0]
        for loc in spawn_location_options:
            cloned_game_state = gamelib.GameState(self.config, TURN_STATE)
            cloned_game_state._player_resources[0]["SP"] = 1000
            self.flip_all_layouts()
            self.mid_game_plan(cloned_game_state)
            sim = Simulator(self.config, cloned_game_state, 1)
            scenario = [[DEMOLISHER, int(mp//3), loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            gamelib.debug_write(loc, stats)
            b, best_stats_mirror, best_loc_mirror = self.compare_stats(best_stats_mirror, best_loc_mirror, stats, loc)
            gamelib.debug_write(b, best_stats_mirror)
            
        for loc in spawn_location_options:
            sim = Simulator(self.config, cloned_game_state, 1)
            scenario = [[SCOUT, mp, loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            gamelib.debug_write(loc, stats)
            b, best_stats_mirror, best_loc_mirror = self.compare_stats(best_stats_mirror, best_loc_mirror, stats, loc)
            gamelib.debug_write(best_stats_mirror)

        default_is_safer, _, _ = self.compare_stats(best_stats_default, best_loc_default, best_stats_mirror, best_loc_mirror)
        gamelib.debug_write(default_is_safer, best_stats_default, best_stats_mirror)
        if default_is_safer:
            self.flip_all_layouts()

        return 

        
    def interceptor_defence(self, game_state:gamelib.GameState):
        mp = game_state.get_resource(MP)
        if self.left_risk > self.right_risk:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_left"], max(5, int(mp/2)))
        else:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][0], 1)
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][1], max(5, int(mp/2)))


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

        
        self.mid_game_plan(game_state)
        # gamelib.debug_write(f"Damage: {self.left_risk}, {self.right_risk}")

        threshold = 200
        if self.left_risk < threshold and self.right_risk < threshold:
            self.rush_l2(game_state, MID_GAME_EXTRA_SHIELD["support_l2"], SUPPORT)

            # stop if we are running out of stuff
            if game_state.get_resource(SP) < 5:
                return True
        if self.left_risk > self.right_risk:
            extra_first = MID_GAME_EXTRA_LEFT
            extra_second = MID_GAME_EXTRA_RIGHT
        else:
            extra_first = MID_GAME_EXTRA_RIGHT
            extra_second = MID_GAME_EXTRA_LEFT

        todo = 0
        for turret in extra_first["turret_l1"]:
            todo += game_state.can_spawn(TURRET, turret)
        n = game_state.attempt_spawn(TURRET, extra_first["turret_l1"])
        if n < todo:
            return True
        
        self.rush_l2(game_state, extra_first["wall_l2"], WALL)
        
        if self.left_risk < threshold or  self.right_risk < threshold:
            self.rush_l2(game_state, MID_GAME_EXTRA_SHIELD["support_l2"], SUPPORT)

        self.rush_l2(game_state, extra_second["wall_l2"], WALL)

        self.late_game_shields(game_state)
        
        # n, up = self.rush_l2(game_state, LATE_GAME_SHIELD["shield_l2"], SUPPORT)
        # if n == 0 and up == 0:
        #     return True
        # # even more defences if possible
        
        # if self.left_risk > self.right_risk:
        #     extra_first = LATE_GAME_LEFT
        #     extra_second = LATE_GAME_RIGHT
        # else:
        #     extra_first = LATE_GAME_RIGHT
        #     extra_second = LATE_GAME_LEFT
        
        # n = game_state.attempt_spawn(TURRET, extra_first["turret_l1"])
        # if n == 0 and game_state.get_resource(MP) <= 6:
        #     return True
        
        # self.rush_l2(game_state,  extra_first["wall_l2"], WALL)
        # self.rush_l2(game_state,  extra_second["wall_l2"], WALL)
        return True

    
    def late_game_shields(self, game_state:gamelib.GameState):
        for n in range (len(LATE_GAME_SHIELD["wall_l2"])):
            set = (LATE_GAME_SHIELD["wall_l2"][n], LATE_GAME_SHIELD["shield_l2"][2*n],  LATE_GAME_SHIELD["shield_l2"][2*n+1])
            done = game_state.contains_stationary_unit(set[2])
            self.rush_l2(game_state, [set[0]], WALL)
            self.rush_l2(game_state, [set[1]], SUPPORT)
            n, up = self.rush_l2(game_state, [set[2]], SUPPORT)
            if not done and not n:
                return


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

        best_score = 25*best_dmg + 10*best_tur + best_costdmg
        score = 25*dmg + 10*tur + costdmg
        if score > best_score:
            return True, new_stats, new_locs
        return False, best_stats, best_locs


    def plan_attack(self, game_state:gamelib.GameState):
        if game_state.turn_number < self.last_attack + self.period:
            return

        mp = game_state.get_resource(MP)
        spawn_location_options = SINGLE_SPAWNS["spawn"]
        # gamelib.debug_write(f"Turn {game_state.turn_number} {spawn_location_options}")
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
        n_spawns = len(HYBRID_SPAWNS["spawn_demos"])
        hybrid_locs = [[HYBRID_SPAWNS["spawn_scout"][i], HYBRID_SPAWNS["spawn_demos"][i]] for i in range(n_spawns)]
        # gamelib.debug_write(f"Turn {game_state.turn_number} {hybrid_locs}")
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
        attack = attack or better
        if not attack:
            return
        
        self.predicted_stats = best_stats
        self.last_stats = [0,0,0,0]
        self.last_attack = game_state.turn_number

        gamelib.debug_write(f"TURN {game_state.turn_number}: {best_stats}, {best_loc}, {better}, {best_hybrid_loc}")
        if not better:
            game_state.attempt_spawn(DEMOLISHER, best_hybrid_loc[0], demo_count)
            game_state.attempt_spawn(SCOUT, best_hybrid_loc[1], scout_count)

        else:
            n = game_state.attempt_spawn(mode, best_loc, 1000)
            # gamelib.debug_write(f"{best_loc}, {mode}, {n}")
        
        




if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
