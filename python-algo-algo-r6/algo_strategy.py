from calendar import c
from pickle import NONE
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
        global ALL_LAYOUTS
        global EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_FORTIFICATION, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, MID_GAME_EXTRA_SHIELD, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD
        global SINGLE_SPAWNS, LEFT_ROUTE_SPAWNS, RIGHT_ROUTE_SPAWNS
        global MID_GAME_MAP_COST
        
        EARLY_GAME_MAP = \
        {"wall_l2" : [[6, 10], [21, 10]]
        ,"wall_l1" :  [[4, 10], [23, 10], [5, 9], [7, 9], [20, 9], [22, 9], [7, 8], [20, 8], [8, 7], [19, 7], [8, 6], [19, 6]]
        ,"inters" : [[4, 9], [23, 9], [7, 6], [20, 6]]
        }
        MID_GAME_MAP = \
        {"wall_l2" :[[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [23, 13], [25, 13], [26, 13], [27, 13], [6, 10], [7, 9]]
        ,"turret_l1" : [[3, 12], [5, 12], [6, 12], [7, 12], [24, 12]]
        ,"wall_l1" : [[23, 11], [21, 10], [22, 10], [5, 9], [20, 9], [7, 8], [20, 8], [8, 7], [19, 7], [8, 6], [9, 6], [18, 6], [10, 5], [17, 5], [11, 4], [13, 4], [14, 4], [16, 4], [12, 3], [15, 3]]
        ,"inters" : [[7,6]]
        ,"remove" : [[19, 6], [22, 9], [23, 10], [5, 10], [6, 9]]
        }
        MID_GAME_FORTIFICATION = \
        {"wall_l2" : []
        ,"wall_l1" : []
        ,"turret_l1" : []
        }

        MID_GAME_EXTRA_LEFT = \
        {"wall_l2" : [[9, 12], [9, 11], [7, 8], [8, 7], [9, 6], [10, 5]]
        ,"turret_l1" : [[4, 12], [8, 12], [8, 11]]
        }
        MID_GAME_EXTRA_RIGHT = \
        {"wall_l2": [[20, 13], [21, 13], [22, 13], [21, 10], [20, 9]]
        ,"turret_l1" : [[24, 13], [20, 12], [21, 12], [22, 12], [23, 12]]
        }
        MID_GAME_EXTRA_SHIELD = \
        {"support_l2" : []
        ,"support_l1" : [[13, 3], [14, 3], [13, 2], [14, 2]]
        }
        MID_GAME_DEFENCE =\
        {"inters_left" : [[2, 11]]
        ,"inters_right" :[[24,10], [22,8]]
        }

        LATE_GAME_LEFT = \
        {"wall_l2": []
        ,"turret_l1" : []
        ,"turret_l2" : MID_GAME_MAP["turret_l1"] + MID_GAME_EXTRA_LEFT["turret_l1"]
        }
        LATE_GAME_RIGHT = \
        {"wall_l2": [[19, 8], [18, 7], [21, 7], [20, 6]]
        ,"turret_l1" : [[26, 12], [25, 11], [19, 9], [18, 8]]
        ,"turret_l2" : [[24, 12], [24, 11], [20, 11], [19, 11]]
        }
        LATE_GAME_SHIELD = \
        {"shield_l2": [[11, 5], [12, 5], [13, 5], [14, 5], [15, 5], [16, 5], [12, 4], [15, 4]]
        ,"wall_l2" : [[11, 6],[16, 6]]
        }

        SINGLE_SPAWNS = \
        {"spawn": [[13, 0], [14, 0], [21, 7]]
        }
        # HYBRID_SPAWNS = \
        # {"spawn_scout" : [[18, 4], [17, 3], [10, 3], [9, 4]]
        # ,"spawn_demos" : [[17, 3], [18, 4], [9, 4], [10, 3]]
        # }
        RIGHT_ROUTE_SPAWNS = \
        {"spawn_scout" : [[13, 0], [14, 0]]
        ,"spawn_demos" : [[14, 0], [15, 1]]
        }
        LEFT_ROUTE_SPAWNS = \
        {"spawn_scout" : [[14, 0], [13, 0]]
        ,"spawn_demos" : [[13, 0], [12, 1]]
        }
        ALL_LAYOUTS = [EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_FORTIFICATION, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, MID_GAME_EXTRA_SHIELD, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD] + \
        [SINGLE_SPAWNS, RIGHT_ROUTE_SPAWNS,LEFT_ROUTE_SPAWNS]


        global STRUCTURECOSTS, STRUCTUREKEYS, TYPETOKEYS
        STRUCTURECOSTS = {"wall_l1": 0.5, "wall_l2": 2, "turret_l1": 6, "turret_l2": 12,"support_l1": 4, "support_l2": 6}
        STRUCTUREKEYS = ["wall_l1", "wall_l2", "turret_l1", "turret_l2", "support_l1", "support_l2"]
        TYPETOKEYS = {TURRET:"turret_l", WALL:"wall_l", SUPPORT:"support_l"}

        for layout in ALL_LAYOUTS:
            self.fill_keys(layout)

        global LEFT_ROUTE, RIGHT_ROUTE, LEFT_LINE, RIGHT_LINE, BREACH_LEFT, BREACH_RIGHT, NO_BREACH
        RIGHT_ROUTE = [[26, 13], [27, 13], [25, 12], [26, 12], [24, 11], [25, 11], [23, 10], [24, 10], [22, 9], [23, 9], [21, 8], [22, 8], [20, 7], [21, 7], [19, 6], [20, 6], [18, 5], [19, 5], [17, 4], [18, 4], [16, 3], [17, 3], [15, 2], [16, 2], [14, 1], [15, 1], [13, 0], [14, 0]]
        LEFT_ROUTE = [[0, 13], [1, 13], [1, 12], [2, 12], [2, 11], [3, 11], [3, 10], [4, 10], [4, 9], [5, 9], [5, 8], [6, 8], [6, 7], [7, 7], [7, 6], [8, 6], [8, 5], [9, 5], [9, 4], [10, 4], [10, 3], [11, 3], [11, 2], [12, 2], [12, 1], [13, 1], [13, 0], [14, 0]]
        RIGHT_LINE = [[25, 13], [24, 12], [23, 11], [22, 10], [21, 9], [20, 8], [19, 7], [18, 6], [17, 5], [13, 4], [14, 4], [16, 4], [12, 3], [15, 3], [11, 2]]
        LEFT_LINE = [[2, 13], [3, 12], [4, 11], [5, 10], [6, 9], [7, 8], [8, 7], [9, 6], [10, 5], [11, 4], [13, 4], [14, 4], [12, 3], [15, 3], [16, 2]]
        NO_BREACH = 0
        BREACH_LEFT = 1
        BREACH_RIGHT = 2

        self.damage_taken_tracker = deque()
        self.damage_tracker_memory = 5

        self.early_game = True
        self.last_attack = -1
        self.target_stats = [0,1,0,0]
        self.predicted_stats = [0,0,0,0]
        self.predicted_breach_stats = [0,0,0,0]
        self.enemy_last_health = 30
        self.last_stats = [0,0,0,0]

        self.period = 4
        self.min_period = 4
        self.max_period = 7
        self.breach = NO_BREACH
        self.breach_config = {}
        self.mid_game_threshold = 100
        self.late_game_threshold = 500

        self.left_risk, self.right_risk = 0, 0
        self.total_left_risk, self.total_right_risk = 0, 0
        self.enemy_total_spending = [0, 0]
        self.enemy_total_income = [0, 0]
        self.enemy_last_resources = [35, 0]
        self.enemy_last_spending = [0, 0]
        self.enemy_last_income = [0, 0]
        
        self.current_structures = []
        self.current_layout = {}
        self.destroying = []

        self.mirrored = False
        # self.print_layout(MID_GAME_MAP)
        # self.flip_all_layouts()
        # self.print_layout(MID_GAME_MAP)

        self.enemy_spawns_x = {x:0 for x in range(28)}
        self.enemy_breach_intention = [False, False]
        self.enemy_frontline_gap_x = {x:0 for x in range(28)}

    """
    ====================================
    """

    # left or right depends if mirrored is on
    def on_action_frame(self, turn_string):
        action_frame = json.loads(turn_string)
        events = action_frame["events"]
        damage_events = events['damage']
        left, right = 0,0

        # Format: [loc(i,i), dmg(f), unittype(i), id(s), p_no(i)]
        for e in damage_events:
            if e[4] == 1 and e[0][1] <= 13: #owner is us, on our side of the map
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
                if e[0][0] <= 8:
                    left += e[1]*100
                elif e[0][0] >= 19:
                    right += e[1]*100
                else:
                    left += e[1]*100
                    right += e[1]*100
                self.enemy_last_income[SP] += 1
        
        if self.mirrored:
            self.damage_taken_tracker[-1][0] += right
            self.damage_taken_tracker[-1][1] += left
        else:
            self.damage_taken_tracker[-1][0] += left
            self.damage_taken_tracker[-1][1] += right
        # gamelib.debug_write(f"ACTION FRAME: {left} {right} number of events {len(damage_events)}")

        if not self.early_game:
            self.detect_breach_strategy(action_frame)
            self.detect_front_safespot(action_frame)
    
    
    def detect_breach_strategy(self, action_frame):
        events = action_frame["events"]
        self_destruct_events = events["selfDestruct"]
        death_events = events["death"]
        # either there is a self-destruct near the wall (failed breach) 

        if not self.mirrored:
            li = 0
            ri = 1
        else:
            li = 1
            ri = 0

        for sd in self_destruct_events:
            if sd[5] == 2 and sd[0][1] <= 15 and sd[0][1] >= 12 and sd[3] in [3, 4]:
                if sd[0][0] <= 2:
                    self.enemy_breach_intention[li] = True
                elif sd[0][0] >= 26:
                    self.enemy_breach_intention[ri] = True

        # or the walls are broken
        for d in death_events:
            if d[2] in [0, 1, 2] and d[0] not in self.destroying:
                if d[0] in [[0, 13], [1, 13]]:
                    self.enemy_breach_intention[li] = True
                elif d[0] in [[26, 13], [27, 13]]:
                    self.enemy_breach_intention[ri] = True


    def detect_front_safespot(self, action_frame):
        turninfo = action_frame["turnInfo"]
        if not (turninfo[0] == 1 and turninfo[2] == 0):
            return

        p2_units = action_frame["p2Units"]
        for x in range(28):
            self.enemy_frontline_gap_x[x] += 1

        for uty in [0, 1, 2]:
            for unit in p2_units[uty]:
                if unit[1] == 14:
                    self.enemy_frontline_gap_x[unit[0]] -= 1
    

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

    def fill_keys(self, layout):
        for key in STRUCTUREKEYS:
            if key not in layout.keys():
                layout[key] = []





 
    def starter_strategy(self, game_state:gamelib.GameState):
        self.reflect(game_state)
        if game_state.turn_number > 0:
            self.switch_to_mid_game(game_state)


        if self.early_game:
            self.early_game_plan(game_state)
        else:
            if self.breach == NO_BREACH:
                self.plan_breach(game_state)
            else:
                self.execute_breach(game_state)
            
            ok = self.build_defences(game_state)
        # if not self.early_game:
        #     self.plan_attack(game_state)


    def compute_total_cost_of_layout(self, layout):
        total = 0
        for key, cost in STRUCTURECOSTS:
            if key in layout:
                total += len(layout[key])*cost
        return total


    def compute_total_cost_of_layout_transition(self, before_layout, after_layout):
        total = 0
        paired_keys = [[STRUCTUREKEYS[2*i], STRUCTUREKEYS[2*i+1]] for i in range(3)]
        for k1, k2 in paired_keys:
            for loc in after_layout[k2]:
                if loc not in before_layout[k2]:
                    if loc not in before_layout[k1]:
                        total += STRUCTURECOSTS[k2]
                    else:
                        total += STRUCTURECOSTS[k2] - STRUCTURECOSTS[k1]
            for loc in after_layout[k1]:
                if loc not in before_layout[k1] + before_layout[k2]:
                    total += STRUCTURECOSTS[k1]
        return total


    def flip_all_layouts(self):
        for layout in ALL_LAYOUTS:
            for k, ls in layout.items():
                for n in range(len(ls)):
                    ls[n] = [27 - ls[n][0], ls[n][1]]
                layout[k] = deepcopy(ls)
                

    def compute_current_structures(self, game_state:gamelib.GameState):
        self.current_structures = []
        for x,y  in game_state.game_map:
            if y > 13 or not game_state.game_map[x, y]:
                continue
            unit = game_state.game_map[x, y][0]
            self.current_structures.append({"loc":[x,y], "ty":unit.unit_type, "hp": unit.health, "maxhp":unit.max_health, "upg": unit.upgraded})

        self.current_layout = {}
        self.fill_keys(self.current_layout)
        for structure in self.current_structures:
            key = ""
            if structure["ty"] == TURRET:
                key += "turret_l"
            elif structure["ty"] == WALL:
                key += "wall_l"
            else:
                key += "support_l"
            if structure["upg"]:
                key += "2"
            else:
                key += "1"
            self.current_layout[key].append(structure["loc"])


    def attempt_spawn(self, game_state:gamelib.GameState, loc_list, type, layout=None, store_layout=True):
        if not layout:
            layout = self.current_layout
        total = 0
        for loc in loc_list:
            if loc in self.destroying:
                continue
            n = game_state.attempt_spawn(type, loc)
            if n and store_layout:
                # gamelib.debug_write("spawn", type, loc, n)
                layout[TYPETOKEYS[type]+"1"].append(loc)
            total += 1
        return total

    def attempt_upgrade(self, game_state:gamelib.GameState,loc_list, type, layout=None, store_layout=True):
        if not layout:
            layout = self.current_layout
        total = 0
        for loc in loc_list:
            if loc in self.destroying:
                continue
            # a different structure exists here currently
            if not loc in self.current_layout[TYPETOKEYS[type]+"1"]:
                continue
            n = game_state.attempt_upgrade(loc)
            if n and store_layout:
                # gamelib.debug_write("upgrade", type, loc, n)
                self.current_layout[TYPETOKEYS[type]+"2"].append(loc)
                self.current_layout[TYPETOKEYS[type]+"1"].remove(loc)
            total += 1
        return total

    def attempt_remove_one(self, game_state:gamelib.GameState, loc):
        game_state.attempt_remove(loc)
        # key = TYPETOKEYS[struct["ty"]]+("2" if struct["upg"] else "1")
        # self.current_layout[key].append(loc)
        # self.current_layout[key].remove(loc)
        self.destroying.append(loc)
        return 1

    def rush_l2(self, game_state:gamelib.GameState, loc_list, type):
        n = 0
        up = 0
        for loc in loc_list:
            n += self.attempt_spawn(game_state, [loc], type)
            up += self.attempt_upgrade(game_state, [loc], type)
        return n, up


    def reflect(self, game_state:gamelib.GameState):
        # recompute stats
        self.last_stats[0] = self.enemy_last_health - game_state.enemy_health
        self.enemy_last_health = game_state.enemy_health

        self.left_risk, self.right_risk = self.damage_taken(game_state)
        self.total_left_risk += self.left_risk
        self.total_right_risk += self.right_risk

        self.enemy_last_income[SP] += 5 
        enemy_no_spend_sp = self.enemy_last_resources[SP] + self.enemy_last_income[SP]
        enemy_now_sp = game_state.get_resource(SP, 1)
        # gamelib.debug_write(f"no: {enemy_no_spend_sp}, now: {enemy_now_sp}")

        self.enemy_last_spending[SP] = enemy_no_spend_sp - enemy_now_sp
        self.enemy_total_spending[SP]  += self.enemy_last_spending[SP]
        # gamelib.debug_write(f"Spent: {self.enemy_total_spending[SP]}")

        self.compute_current_structures(game_state)
        self.destroying = []
        # gamelib.debug_write("ON REFLECTION\n", game_state.turn_number, self.current_layout)

        self.reflect_on_attack(game_state)
        self.analyse_enemy_plan(game_state)

        self.enemy_last_income[SP] = 0
        self.enemy_last_resources[SP] = enemy_now_sp



    def reflect_on_attack(self, game_state:gamelib.GameState):
        if not game_state.turn_number-1 == self.last_attack:
            return


        if self.predicted_stats[0] >= 2* self.last_stats[0] or self.predicted_stats[1] >= 2* self.last_stats[1]:
            self.period = min(self.max_period, self.period+1)

        if self.last_stats[0] > 0:
            self.period = max(self.min_period, self.period // 2)

        gamelib.debug_write(f"after reflection: period = {self.period}. predicted {self.predicted_stats} got {self.last_stats}")


    def damage_taken(self, game_state:gamelib.GameState):
        weights = [0.6, 0.6, 0.6, 0.8, 1]
        tot_left, tot_right = 0, 0

        for t in range(min(game_state.turn_number, self.damage_tracker_memory)):
            left, right = self.damage_taken_tracker.popleft()
            tot_left += left * weights[t]
            tot_right += right * weights[t]
            self.damage_taken_tracker.append([left, right])
        return tot_left, tot_right


    def analyse_enemy_plan(self, game_state:gamelib.GameState):

        # gamelib.debug_write(f"TURN {game_state.turn_number}:\n Enemy frontline {self.enemy_frontline_gap_x}")
        return



    """ Defence
    """



    def early_game_plan(self, game_state:gamelib.GameState):
        
        self.attempt_spawn(game_state, EARLY_GAME_MAP["wall_l1"], WALL)
        self.rush_l2(game_state, EARLY_GAME_MAP["wall_l2"], WALL)
        game_state.attempt_spawn(INTERCEPTOR, EARLY_GAME_MAP["inters"], 1)
        

    def switch_to_mid_game(self, game_state:gamelib.GameState):
        if not self.early_game:
            return
        sp_avail = game_state.get_resource(SP)
        cost = self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_MAP)
        enough_to_switch = sp_avail >= cost
        enemy_position_chosen = self.enemy_total_spending[SP] >= 60
        mp_gain = 5 + int(game_state.turn_number/5)
        major_wave_released = True # game_state.get_resource(MP, 1) < mp_gain+1
        gamelib.debug_write(f"Cost: {cost} {enough_to_switch} {enemy_position_chosen} {major_wave_released} {game_state.get_resource(MP, 1)}")
        if (not (enough_to_switch and enemy_position_chosen and major_wave_released)) and game_state.turn_number < 15:
            return

        self.early_game = False
        self.decide_orientation(game_state)
        self.attempt_remove_one(game_state, MID_GAME_MAP["remove"])



    def decide_orientation(self, game_state:gamelib.GameState):
        gamelib.debug_write("DECIDING ORIENTATION")
        spawn_location_options = [[13, 27], [14, 27]]
        mp = 25
        cloned_game_state = gamelib.GameState(self.config, TURN_STATE)
        cloned_game_state._player_resources[0]["SP"] = 1000
        self.mid_game_plan(cloned_game_state, store_layout=False)
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
        self.flip_all_layouts()
        cloned_game_state = gamelib.GameState(self.config, TURN_STATE)
        cloned_game_state._player_resources[0]["SP"] = 1000
        self.mid_game_plan(cloned_game_state, store_layout=False)
        for loc in spawn_location_options:
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
        self.print_layout(MID_GAME_MAP)
        gamelib.debug_write("default better:", default_is_safer, best_stats_default, best_stats_mirror)
        if default_is_safer:
            self.flip_all_layouts()
        else:
            self.mirrored = True

        self.print_layout(MID_GAME_MAP)
        return 

        

    def build_defences(self, game_state:gamelib.GameState):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download


        b = self.mid_game_plan(game_state)
        if not b:
            return b
        self.mid_game_shields(game_state)

        # gamelib.debug_write(f"Damage: {self.left_risk}, {self.right_risk}")
        if self.left_risk > self.right_risk:
            extra_second = MID_GAME_EXTRA_RIGHT
            b = self.mid_game_left_extra(game_state)
        else:
            extra_second = MID_GAME_EXTRA_LEFT
            b = self.mid_game_right_extra(game_state)

        if not b:
            return b

        self.destroy_damaged(game_state)

        if extra_second == MID_GAME_EXTRA_RIGHT:
            b = self.mid_game_right_extra(game_state)
        else:
            b = self.mid_game_left_extra(game_state)


        late_game_threshold = 500
        # if self.right_risk > late_game_threshold:
        #     b = self.late_game_right(game_state)
        if self.left_risk > late_game_threshold:
            b = self.late_game_left(game_state)

        if not b:
            return b

        self.late_game_shields(game_state)
        

        return True


    def destroy_damaged(self, game_state:gamelib.GameState):
        threshold = 0.6
        # gamelib.debug_write("ABOUT TO DESTROY\n", game_state.turn_number, self.current_layout)
        for structure in self.current_structures:
            if structure["hp"]/structure["maxhp"] < threshold:
                self.attempt_remove_one(game_state, structure["loc"])



    def mid_game_plan(self, game_state:gamelib.GameState, store_layout=True):
        cost = self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_MAP)
        # gamelib.debug_write(cost, "!!!", game_state.get_resource(SP) )
        # self.print_layout_difference(self.current_layout, MID_GAME_MAP)
        game_state.attempt_spawn(INTERCEPTOR, MID_GAME_MAP["inters"], 1)
        # if cost >= game_state.get_resource(SP):
        #     gamelib.debug_write("cannot complete mid game plan", cost)
        #     return False 
        self.attempt_spawn(game_state, MID_GAME_MAP['wall_l1'], WALL, store_layout=store_layout)
        self.attempt_spawn(game_state, MID_GAME_MAP['wall_l2'], WALL, store_layout=store_layout)
        self.attempt_upgrade(game_state, MID_GAME_MAP['wall_l2'], WALL, store_layout=store_layout)
        self.attempt_spawn(game_state, MID_GAME_MAP['turret_l1'], TURRET, store_layout=store_layout)
        return True


    def mid_game_left_extra(self, game_state:gamelib.GameState):
        if self.total_left_risk < 10 * self.mid_game_threshold and self.left_risk < self.mid_game_threshold:
            return True
        MID_GAME_EXTRA_LEFT["wall_l2"].sort(key=lambda x: x[0])
        MID_GAME_EXTRA_LEFT["turret_l1"].sort(key=lambda x: -x[1])

        self.rush_l2(game_state, MID_GAME_EXTRA_LEFT["wall_l2"][:4], WALL)
        self.attempt_spawn(game_state, MID_GAME_EXTRA_LEFT["turret_l1"], TURRET)
        self.rush_l2(game_state, MID_GAME_EXTRA_LEFT["wall_l2"][4:], WALL)

        if self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_EXTRA_LEFT) > 0:
            gamelib.debug_write("cannot complete left extra")
            return game_state.turn_number<10
        return True


    def mid_game_right_extra(self, game_state:gamelib.GameState):
        if self.total_left_risk < 10 * self.mid_game_threshold and self.left_risk < self.mid_game_threshold:
            return True
        MID_GAME_EXTRA_RIGHT["wall_l2"].sort(key=lambda x: -x[1])
        MID_GAME_EXTRA_RIGHT["turret_l1"].sort(key=lambda x: -x[1])

        self.rush_l2(game_state, MID_GAME_EXTRA_RIGHT["wall_l2"], WALL)
        self.attempt_spawn(game_state, MID_GAME_EXTRA_RIGHT["turret_l1"], TURRET)

        if self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_EXTRA_RIGHT) > 0:
            # self.print_layout_difference(self.current_layout, MID_GAME_EXTRA_RIGHT)
            gamelib.debug_write("cannot complete right extra")
            return game_state.turn_number<10
        return True

    def mid_game_shields(self, game_state:gamelib.GameState):
        self.attempt_spawn(game_state, MID_GAME_EXTRA_SHIELD["support_l1"], SUPPORT)
        if self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_EXTRA_SHIELD) > 0:
            # self.print_layout_difference(self.current_layout, MID_GAME_EXTRA_RIGHT)
            gamelib.debug_write("cannot complete mid game shields")
            return False
        return True



    def late_game_right(self, game_state:gamelib.GameState):

        return True

    
    def late_game_left(self, game_state:gamelib.GameState):
        self.rush_l2(game_state, LATE_GAME_LEFT["wall_l2"], WALL)
        # self.attempt_spawn(game_state, LATE_GAME_LEFT["turret_l1"], TURRET)
        self.attempt_upgrade(game_state, LATE_GAME_LEFT["turret_l2"], TURRET)

        if self.compute_total_cost_of_layout_transition(self.current_layout, LATE_GAME_RIGHT) > 0:
            # self.print_layout_difference(self.current_layout, LATE_GAME_RIGHT)
            gamelib.debug_write("cannot complete right late game")
            return game_state.turn_number< 20
        return True

    
    def late_game_shields(self, game_state:gamelib.GameState):
        self.rush_l2(game_state, LATE_GAME_SHIELD["shield_l2"], SUPPORT)
        self.rush_l2(game_state, LATE_GAME_SHIELD["wall_l2"], WALL)
            
        if self.compute_total_cost_of_layout_transition(self.current_layout, LATE_GAME_SHIELD) > 0:
            gamelib.debug_write("cannot complete late game shields")
            return False
        return True


    



    """ Attack
    """


    # True if new is better
    def compare_stats(self, best_stats, best_locs, new_stats,new_locs):
        best_dmg, best_tur, best_strct, best_costdmg = best_stats
        dmg, tur, strct, costdmg = new_stats

        best_score = 50*best_dmg + 35*best_tur + best_costdmg
        score = 50*dmg + 35*tur + costdmg
        if score > best_score:
            return True, new_stats, new_locs
        return False, best_stats, best_locs


    def plan_breach(self, game_state:gamelib.GameState):
        if game_state.turn_number < self.last_attack + self.period:
            return

        mp = game_state.project_future_MP(1) -1
        

        max_demo = int(mp//3)
        min_demo = int(max_demo*(1/3)) *0
        gamelib.debug_write(f"Considering {min_demo} to {max_demo} demos")

        best_stats_left = self.target_stats
        best_stats_right = self.target_stats
        best_config_left = {"demos":min_demo,"scouts":0,"scout_loc":[13, 0],"demo_loc":[14, 0]}
        best_config_right = {"demos":min_demo,"scouts":0,"scout_loc":[13, 0],"demo_loc":[14, 0]}

        for n in range(2):
            if n == 0:
                line = RIGHT_LINE
                route = RIGHT_ROUTE
                spawn_options = [[RIGHT_ROUTE_SPAWNS["spawn_scout"][i], RIGHT_ROUTE_SPAWNS["spawn_demos"][i]] for i in range(len(RIGHT_ROUTE_SPAWNS["spawn_demos"]))]
                best_stats = best_stats_right
                best_config = best_config_right
            else:
                line = LEFT_LINE
                route = LEFT_ROUTE
                spawn_options = [[LEFT_ROUTE_SPAWNS["spawn_scout"][i], LEFT_ROUTE_SPAWNS["spawn_demos"][i]] for i in range(len(LEFT_ROUTE_SPAWNS["spawn_demos"]))]
                best_stats = best_stats_left
                best_config = best_config_left
            cloned_game_state = gamelib.GameState(self.config, TURN_STATE)
            cloned_game_state._player_resources[0]["SP"] = 1000
            cloned_game_state.attempt_spawn(WALL, line)
            for scout_loc, demo_loc in spawn_options:
                gamelib.debug_write(f"Trying scout @ {scout_loc} and demo at {demo_loc}")
                for demos in range(min_demo, max_demo+1, 2):
                    scouts = int(mp - 3*demos)
                    scenario = [[DEMOLISHER, demos, demo_loc], [SCOUT, scouts, scout_loc]]
                    sim = Simulator(self.config, cloned_game_state, clear=route)
                    sim.place_mobile_units(scenario)
                    stats = sim.simulate()
                    # gamelib.debug_write(f"Demos {demos}@{demo_loc} Scouts {scouts}@{scout_loc}", stats)
                    b, best_stats, _ = self.compare_stats(best_stats, None, stats, None)
                    if b:
                        best_config["demos"] = demos
                        best_config["scouts"] = scouts
                        best_config["scout_loc"] = scout_loc
                        best_config["demo_loc"] = demo_loc

            if n == 0:
                best_stats_right = best_stats
                best_config_right = best_config
            else:
                best_stats_left = best_stats
                best_config_left = best_config


        gamelib.debug_write("LEFT", best_config_left,best_stats_left)
        gamelib.debug_write("RIGHT", best_config_right,best_stats_right)

        right, stats, _ = self.compare_stats(best_stats_left, None, best_stats_right, None)
        
        # utter failure
        dont_attack, _, _ =self.compare_stats(best_stats, None, self.target_stats, None)
        if dont_attack:
            gamelib.debug_write(best_stats, self.target_stats, "WHY???")
            return

        self.predicted_breach_stats = best_stats
        self.last_stats = [0,0,0,0]
        self.last_attack = game_state.turn_number + 1

        if right:
            self.breach = BREACH_RIGHT
            self.breach_config = best_config_right
        else:
            self.breach = BREACH_LEFT
            self.breach_config = best_config_left

        self.prepare_breach(game_state)


    def prepare_breach(self, game_state:gamelib.GameState):
        line = LEFT_LINE if self.breach == BREACH_LEFT else RIGHT_LINE
        route = LEFT_ROUTE if self.breach == BREACH_LEFT else RIGHT_ROUTE

        for loc in route:
            self.attempt_remove_one(game_state, loc)
        return


    def execute_breach(self, game_state:gamelib.GameState):
        demos = self.breach_config["demos"]
        scouts = self.breach_config["scouts"]
        demo_loc = self.breach_config["demo_loc"]
        scout_loc = self.breach_config["scout_loc"]
        gamelib.debug_write("EXECUTING BREACH", self.breach, self.breach_config, game_state.turn_number, self.last_attack, self.period)
        game_state.attempt_spawn(DEMOLISHER, demo_loc, demos)
        game_state.attempt_spawn(SCOUT, scout_loc, scouts)
        self.prepare_breach(game_state)   

        line = LEFT_LINE if self.breach == BREACH_LEFT else RIGHT_LINE
        self.attempt_spawn(game_state, line, WALL)

        for loc in MID_GAME_MAP["remove"]:
            self.attempt_remove_one(game_state, loc)
        
        self.breach = NO_BREACH
        return


    def plan_attack(self, game_state:gamelib.GameState):
        if game_state.turn_number < self.last_attack + self.period:
            return

        return self.plan_breach(game_state)

        mp = game_state.get_resource(MP)
        spawn_location_options = SINGLE_SPAWNS["spawn"]
        # gamelib.debug_write(f"Turn {game_state.turn_number} {spawn_location_options}")
        attack = False
        # check demos first
        best_loc = spawn_location_options[-1]
        best_stats = self.target_stats
        for loc in spawn_location_options:
            if game_state.contains_stationary_unit(loc):
                continue
            sim = Simulator(self.config, game_state)
            scenario = [[DEMOLISHER, int(mp//3), loc]]
            sim.place_mobile_units(scenario)
            stats = sim.simulate()
            better, best_stats, best_loc = self.compare_stats(best_stats, best_loc, stats, loc)
            attack = attack or better

        # check if we should just sent scouts
        mode = DEMOLISHER
        if game_state.contains_stationary_unit(best_loc):
            pass
        else:
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
            for loc in locs:
                if game_state.contains_stationary_unit(loc):
                    continue
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

        # gamelib.debug_write(f"TURN {game_state.turn_number}: {best_stats}, {best_loc}, {better}, {best_hybrid_loc}")
        if not better:
            game_state.attempt_spawn(DEMOLISHER, best_hybrid_loc[0], demo_count)
            game_state.attempt_spawn(SCOUT, best_hybrid_loc[1], scout_count)

        else:
            n = game_state.attempt_spawn(mode, best_loc, 1000)
            # gamelib.debug_write(f"{best_loc}, {mode}, {n}")
        
        
    def print_layout_difference(self, ref, other):
        for key in STRUCTUREKEYS:
            refhas = [loc for loc in ref[key] if loc not in other[key]]
            otherhas = [loc for loc in other[key] if loc not in ref[key]]
            gamelib.debug_write(key, "ref has", refhas)
            gamelib.debug_write(key, "other has", otherhas)

    def print_layout(self, layout):
        for key in STRUCTUREKEYS:
            gamelib.debug_write(key,layout[key])


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
