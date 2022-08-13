from calendar import c
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
        {"wall_l2" : [[2, 13], [25, 13], [20, 12], [17, 9]]
        ,"wall_l1" : []
        ,"turret_l1" : [[4, 11], [24, 12], [20, 11]]
        ,"support_l2": [[25, 12]]
        ,"support_l1": [[19, 10], [18, 9]]
        ,"scouts": [[21, 7]]
        ,"demos": []
        ,"inters" : []# [[7, 6]]
        }
        MID_GAME_MAP = \
        {"wall_l2" : [[23, 11], [23, 10]] + EARLY_GAME_MAP["wall_l2"]
        ,"turret_l1" : EARLY_GAME_MAP["turret_l1"][1:]
        ,"wall_l1" : [[0, 13], [1, 13], [19, 13], [26, 13], [27, 13], [2, 12], [2, 11], [3, 10], [4, 9], [23, 9], [5, 8], [16, 8], [6, 7], [15, 7], [7, 6], [14, 6], [8, 5], [13, 5], [9, 4], [12, 4], [10, 3], [11, 3]]
        ,"support_l2": EARLY_GAME_MAP["support_l2"]
        ,"support_l1": [[19, 10], [18, 9]]
        }
        MID_GAME_FORTIFICATION = \
        {"wall_l2" : [[26, 13], [27, 13], [23, 12], [19, 11], [18, 10]]
        ,"wall_l1" : []
        ,"turret_l1" : []
        }

        MID_GAME_EXTRA_LEFT = \
        {"wall_l2" : [[0, 13], [2, 13], [2, 12], [2, 11], [3, 11], [3, 10], [4, 10], [5, 9]]
        ,"turret_l1" : [[1, 12]]
        }
        MID_GAME_EXTRA_RIGHT = \
        {"wall_l2": [[24, 13], [19, 12], [21, 12], [21, 10], [23, 9], [22, 8]]
        ,"turret_l1" : [[21, 11], [24, 11], [20, 10], [24, 10], [20, 9]]
        }
        MID_GAME_EXTRA_SHIELD = \
        {"support_l2" : EARLY_GAME_MAP["support_l1"] + [[17, 8]]
        ,"support_l1" : [[16, 7], [17, 7]]
        }
        MID_GAME_DEFENCE =\
        {"inters_left" : [[2, 11]]
        ,"inters_right" :[[24,10], [22,8]]
        }

        LATE_GAME_LEFT = \
        {"wall_l2": []
        ,"turret_l1" : []
        }
        LATE_GAME_RIGHT = \
        {"wall_l2": [[19, 8], [18, 7], [21, 7], [20, 6]]
        ,"turret_l1" : [[26, 12], [25, 11], [19, 9], [18, 8]]
        ,"turret_l2" : [[24, 12], [24, 11], [20, 11], [19, 11]]
        }
        LATE_GAME_SHIELD = \
        {"shield_l2": [[16, 10], [17, 10], [15, 9], [16, 9], [14, 8], [15, 8]]
        ,"wall_l2" : [[16, 11], [17, 11], [15, 10]]
        }

        SINGLE_SPAWNS = \
        {"spawn": [[13, 0], [14, 0], [21, 7]]
        }
        # HYBRID_SPAWNS = \
        # {"spawn_scout" : [[18, 4], [17, 3], [10, 3], [9, 4]]
        # ,"spawn_demos" : [[17, 3], [18, 4], [9, 4], [10, 3]]
        # }
        HYBRID_SPAWNS = \
        {"spawn_scout" : [[13, 0], [14, 0]]
        ,"spawn_demos" : [[14, 0], [13, 0]]
        }
        ALL_LAYOUTS = [EARLY_GAME_MAP, MID_GAME_MAP, MID_GAME_FORTIFICATION, MID_GAME_EXTRA_LEFT, MID_GAME_EXTRA_RIGHT, MID_GAME_EXTRA_SHIELD, MID_GAME_DEFENCE, LATE_GAME_LEFT, LATE_GAME_RIGHT, LATE_GAME_SHIELD] + \
        [SINGLE_SPAWNS, HYBRID_SPAWNS]


        global STRUCTURECOSTS, STRUCTUREKEYS, TYPETOKEYS
        STRUCTURECOSTS = {"wall_l1": 0.5, "wall_l2": 2, "turret_l1": 6, "turret_l2": 12,"support_l1": 4, "support_l2": 6}
        STRUCTUREKEYS = ["wall_l1", "wall_l2", "turret_l1", "turret_l2", "support_l1", "support_l2"]
        TYPETOKEYS = {TURRET:"turret_l", WALL:"wall_l", SUPPORT:"support_l"}

        for layout in ALL_LAYOUTS:
            self.fill_keys(layout)

        self.damage_taken_tracker = deque()
        self.damage_tracker_memory = 5

        self.last_attack = -1
        self.target_stats = [0,1,0,0]
        self.predicted_stats = [0,0,0,0]
        self.enemy_last_health = 30
        self.last_stats = [0,0,0,0]

        self.period = 2
        self.min_period = 1
        self.max_period = 6
        self.stable_mid_game = False
        self.will_breach = False
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
            ok = self.build_defences(game_state)
            if not ok:
                self.interceptor_defence(game_state)
        if game_state.turn_number > 0:
            self.plan_attack(game_state)


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

    def attempt_spawn(self, game_state:gamelib.GameState, loc_list, type):
        total = 0
        for loc in loc_list:
            if loc in self.destroying:
                continue
            n = game_state.attempt_spawn(type, loc)
            if n:
                self.current_layout[TYPETOKEYS[type]+"1"].append(loc)
            total += 1
        return total

    def attempt_upgrade(self, game_state:gamelib.GameState,loc_list, type):
        total = 0
        for loc in loc_list:
            if loc in self.destroying:
                continue
            n = game_state.attempt_upgrade(loc)
            if n:
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
        # gamelib.debug_write(self.current_layout)

        self.reflect_on_attack(game_state)

        self.enemy_last_income[SP] = 0
        self.enemy_last_resources[SP] = enemy_now_sp



    def reflect_on_attack(self, game_state:gamelib.GameState):
        if not game_state.turn_number-1 == self.last_attack:
            return


        if self.predicted_stats[0] >= 2* self.last_stats[0] or self.predicted_stats[1] >= 2* self.last_stats[1]:
            self.period = min(self.max_period, self.period+1)

        if self.last_stats[0] > 0:
            self.period = max(self.min_period, self.period // 2)

        # gamelib.debug_write(f"after reflection: period = {self.period}. predicted {self.predicted_stats} got {self.last_stats}")


    def early_game_plan(self, game_state:gamelib.GameState):
        
        game_state.attempt_spawn(TURRET, EARLY_GAME_MAP["turret_l1"])
        self.rush_l2(game_state, EARLY_GAME_MAP["wall_l2"], WALL)
        self.rush_l2(game_state, EARLY_GAME_MAP["support_l2"], SUPPORT)
        game_state.attempt_spawn(SUPPORT, EARLY_GAME_MAP["support_l1"])
        # if game_state.turn_number == 0:
        #     game_state.attempt_spawn(SCOUT, EARLY_GAME_MAP["scouts"], 5)
        # else:
        #     game_state.attempt_spawn(INTERCEPTOR, EARLY_GAME_MAP["inters"], 1)
        

    def switch_to_mid_game(self, game_state:gamelib.GameState):
        if not self.early_game:
            return
        sp_avail = game_state.get_resource(SP)
        cost = self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_MAP)
        # gamelib.debug_write(f"COST {cost}")
        # if (sp_avail >= cost or self.enemy_total_spending[SP] >= 50) or sp_avail >= cost + 5:
        if sp_avail >= cost:
            self.early_game = False
            SINGLE_SPAWNS["spawn"].pop()
            # self.decide_orientation(game_state)





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
        return
        mp = game_state.get_resource(MP)
        if self.left_risk > self.right_risk:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_left"], int(mp/3))
        else:
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][0], 1)
            game_state.attempt_spawn(INTERCEPTOR, MID_GAME_DEFENCE["inters_right"][1], int(mp/3))


    

    # this doesnt work
    def replace_if_different(self, game_state:gamelib.GameState, loc_list, type):
        n = 0
        for loc in loc_list:
            

            if game_state.contains_stationary_unit(loc) and not game_state.game_map[loc][0].unit_type == type:
                # gamelib.debug_write(f"{loc} occupied by {game_state.game_map[loc][0].unit_type} want {type}")
                game_state.attempt_remove(loc)
            n += game_state.attempt_spawn(type, loc)
        return n


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
        # gamelib.debug_write(f"Damage: {self.left_risk}, {self.right_risk}")

        if self.left_risk > self.right_risk:
            extra_first = MID_GAME_EXTRA_LEFT
            extra_second = MID_GAME_EXTRA_RIGHT
            b = self.mid_game_left_extra(game_state)
        else:
            extra_first = MID_GAME_EXTRA_RIGHT
            extra_second = MID_GAME_EXTRA_LEFT
            b = self.mid_game_right_extra(game_state)

        if not b:
            return b

        self.destroy_damaged(game_state)
        if self.left_risk < self.mid_game_threshold or self.right_risk < self.mid_game_threshold:
            self.rush_l2(game_state, MID_GAME_EXTRA_SHIELD["support_l2"], SUPPORT)
            self.attempt_spawn(game_state, MID_GAME_EXTRA_SHIELD["support_l1"], SUPPORT)

        self.attempt_spawn(game_state, extra_second["turret_l1"], TURRET)
        self.rush_l2(game_state, extra_second["wall_l2"], WALL)

        late_game_threshold = 500
        if self.right_risk > late_game_threshold:
            b = self.late_game_right(game_state)

        if not b:
            return b

        self.late_game_shields(game_state)
        

        return True


    def destroy_damaged(self, game_state:gamelib.GameState):
        threshold = 0.4
        for structure in self.current_structures:
            if structure["hp"]/structure["maxhp"] < threshold:
                self.attempt_remove_one(game_state, structure["loc"])



    def mid_game_plan(self, game_state:gamelib.GameState):
        cost = self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_MAP)
        # gamelib.debug_write(cost, "!!!", game_state.get_resource(SP) )
        # self.print_layout_difference(self.current_layout, MID_GAME_MAP)
        if cost >= game_state.get_resource(SP):
            gamelib.debug_write("cannot complete mid fort")
            return False 


        self.attempt_spawn(game_state, MID_GAME_MAP['wall_l1'], WALL)
        self.attempt_spawn(game_state, MID_GAME_MAP['wall_l2'], WALL)
        self.attempt_spawn(game_state, MID_GAME_MAP['support_l1'], SUPPORT)
        self.attempt_spawn(game_state, MID_GAME_MAP['support_l2'], SUPPORT)
        self.attempt_upgrade(game_state, MID_GAME_MAP['support_l2'], SUPPORT)
        self.attempt_upgrade(game_state, MID_GAME_MAP['wall_l2'], WALL)
        self.attempt_spawn(game_state, MID_GAME_MAP['turret_l1'], TURRET)
        
        # Phase 1 done
        self.attempt_spawn(game_state, MID_GAME_FORTIFICATION['turret_l1'], TURRET)
        self.attempt_spawn(game_state, MID_GAME_FORTIFICATION['wall_l1'], WALL)

        n, up = self.rush_l2(game_state, MID_GAME_FORTIFICATION["wall_l2"], WALL)
        if self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_FORTIFICATION) > 0:
            gamelib.debug_write("cannot complete mid fort")
            return game_state.turn_number < 6
        # Phase 1.5 done
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
        MID_GAME_EXTRA_RIGHT["wall_l2"].sort(key=lambda x: -x[1])
        MID_GAME_EXTRA_RIGHT["turret_l1"].sort(key=lambda x: -x[1])

        n, up = self.rush_l2(game_state, MID_GAME_EXTRA_RIGHT["wall_l2"][:4], WALL)
        n += self.attempt_spawn(game_state, MID_GAME_EXTRA_RIGHT["turret_l1"][:3], TURRET)
        self.rush_l2(game_state, MID_GAME_EXTRA_RIGHT["wall_l2"][4:], WALL)
        self.attempt_spawn(game_state, MID_GAME_EXTRA_RIGHT["turret_l1"][3:], TURRET)

        if self.compute_total_cost_of_layout_transition(self.current_layout, MID_GAME_EXTRA_RIGHT) > 0:
            # self.print_layout_difference(self.current_layout, MID_GAME_EXTRA_RIGHT)
            # gamelib.debug_write("cannot complete right extra")
            return game_state.turn_number<10
        return True


    def late_game_right(self, game_state:gamelib.GameState):
        self.rush_l2(game_state, LATE_GAME_RIGHT["wall_l2"], WALL)
        self.attempt_spawn(game_state, LATE_GAME_RIGHT["turret_l1"], TURRET)
        self.attempt_upgrade(game_state, LATE_GAME_RIGHT["turret_l2"], TURRET)

        if self.compute_total_cost_of_layout_transition(self.current_layout, LATE_GAME_RIGHT) > 0:
            # self.print_layout_difference(self.current_layout, LATE_GAME_RIGHT)
            # gamelib.debug_write("cannot complete right late game")
            return game_state.turn_number< 22
        return True

    
    def late_game_shields(self, game_state:gamelib.GameState):
        for n in range (len(LATE_GAME_SHIELD["wall_l2"])):
            set = (LATE_GAME_SHIELD["wall_l2"][n], LATE_GAME_SHIELD["shield_l2"][2*n],  LATE_GAME_SHIELD["shield_l2"][2*n+1])
            done = game_state.contains_stationary_unit(set[2])
            self.rush_l2(game_state, [set[0]], WALL)
            self.rush_l2(game_state, [set[1]], SUPPORT)
            n, up = self.rush_l2(game_state, [set[2]], SUPPORT)
            
        if self.compute_total_cost_of_layout_transition(self.current_layout, LATE_GAME_SHIELD) > 0:
            gamelib.debug_write("cannot complete late game shields")
            return False
        return True


    def damage_taken(self, game_state:gamelib.GameState):
        weights = [0.6, 0.6, 0.6, 0.8, 1]
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

        best_score = 25*best_dmg + 35*best_tur + best_costdmg
        score = 25*dmg + 35*tur + costdmg
        if score > best_score:
            return True, new_stats, new_locs
        return False, best_stats, best_locs


    def plan_breach(self, game_state:gamelib.GameState):


        return False


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



if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
