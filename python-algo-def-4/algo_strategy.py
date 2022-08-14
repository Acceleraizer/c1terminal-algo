import gamelib
import random
import math
from sys import maxsize, stderr
import json
# import tensorflow
from simulator import Simulator

import copy
import random

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
        
        def level_1(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(3), 11]])
            game_state.attempt_spawn(WALL, [[flip_side(3), 13]])
            game_state.attempt_upgrade([[flip_side(3), 13]])

        def level_2(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(0), 13], [flip_side(1), 13]])

        def level_3(game_state, flip_side):
            game_state.attempt_spawn(TURRET, [[flip_side(1), 12]])

        def level_4(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(1), 12]])         

        def level_5(game_state, flip_side):
            game_state.attempt_spawn(TURRET, [[flip_side(4), 12]])

        def level_6(game_state, flip_side):
            game_state.attempt_spawn(WALL, [[flip_side(4), 13]])
            game_state.attempt_upgrade([[flip_side(4), 13], [flip_side(4), 12]])
            
        def level_7(game_state, flip_side):
            four_eleven = game_state.contains_stationary_unit([flip_side(4), 11])
            if not four_eleven == False and four_eleven.unit_type == WALL:
                game_state.attempt_remove([[flip_side(4), 11]])
            game_state.attempt_spawn(TURRET, [[flip_side(4), 11]])
        
        def level_8(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(4), 11]])

        def level_9(game_state, flip_side):
            game_state.attempt_spawn(TURRET, [[flip_side(5), 11]])

        def level_10(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(5), 11]])

        def level_11(game_state, flip_side):
            game_state.attempt_spawn(TURRET, [[flip_side(5), 12]])

        def level_12(game_state, flip_side):
            game_state.attempt_spawn(WALL, [[flip_side(6), 12]])
            game_state.attempt_upgrade([[flip_side(6), 12]])

        def level_13(game_state, flip_side):
            game_state.attempt_upgrade([[flip_side(5), 12]])
            game_state.attempt_spawn(WALL, [[flip_side(5), 13]])
            game_state.attempt_upgrade([[flip_side(5), 13]])

        self.levels = [level_1, level_2, level_3, level_4, level_5, 
        level_6, level_7, level_8, level_9, level_10, level_11, level_12, level_13]
        
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
        self.next_attack_check = 5

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
        gamelib.debug_write("return")

        game_state.submit_turn()
        gamelib.debug_write("returned")

    def print_map(self, game_state):
        return
        # for y in range(game_state.game_map.ARENA_SIZE - 1, -1, -1):
        #     row = []
        #     for x in range(game_state.game_map.ARENA_SIZE):
        #         unit = game_state.contains_stationary_unit([x, y])
        #         if unit == False:
        #             row.append('.')
        #             continue
                
        #         if unit.unit_type == WALL:
        #             row.append('~')
        #             continue

        #         if unit.unit_type == TURRET:
        #             row.append('*')
        #             continue
                
        #         if unit.unit_type == SUPPORT:
        #             row.append('#')
        #             continue
        #     gamelib.debug_write(' '.join(row))

    def starter_strategy(self, game_state:gamelib.GameState):
        
        def level_0(game_state):
            game_state.attempt_spawn(TURRET, [[3, 12], [24, 12]])
            back_walls_loc = [[4, 11], [23, 11], [5, 10], [22, 10]] + [[col, 9] for col in range(6, 22)]
            front_walls_loc = [[col , 13] for col in [0, 27, 1, 26]]
            game_state.attempt_spawn(WALL, back_walls_loc + front_walls_loc)
        
        best_spawn, best_config, dmg, score = self.attack_simulation(game_state)

        if not dmg == None:

            if dmg >= game_state.enemy_health:
                self.support(game_state)

            level_0(game_state)

            if game_state.get_resources(1)[1] < 5:
                self.support(game_state)


        gamelib.debug_write("opponent attack simulation")
        unique_spawn_points, scores, cross_map = self.opponent_attack_simulation(game_state)
        priority_left, priority_right = self.guage_defense(unique_spawn_points, scores, cross_map)

        gamelib.debug_write("build_reactive_defenses based on simulation result:" + str(priority_left) + " " + str(priority_right))
        self.build_reactive_defenses(game_state, priority_left, priority_right)
        
        self.support(game_state)
        self.attack(game_state, best_spawn, best_config, score)


        
    def attack_simulation(self, game_state):
        best_config = None
        best_spawn = None
        best_score = -float('inf')
        best_dmg = None
        
        configs = [[[SCOUT, game_state.number_affordable(SCOUT)]], 
        [[DEMOLISHER, game_state.number_affordable(DEMOLISHER)]],
        [[SCOUT, game_state.number_affordable(SCOUT) // 2], [DEMOLISHER, game_state.number_affordable(DEMOLISHER) // 2]]] 

        for unique_spawn_point in [[12, 1], [15, 1]]:
            for config in configs:
                sim = Simulator(self.config, game_state)
                for unit in config:
                    gamelib.debug_write([unit + [unique_spawn_point]])
                    sim.place_mobile_units([unit + [unique_spawn_point]])
                dmg, turrets, structures = sim.simulate()
                score =  7 * dmg  + 11 * turrets - 3 * game_state.number_affordable(SCOUT)
                gamelib.debug_write('attack sim:', dmg, turrets, structures, game_state.number_affordable(SCOUT), score)

                if dmg == None:
                    dmg = 0

                if turrets == None:
                    turrets = 0  

                if structures == None:
                    score = 0

                if score >= best_score:
                    best_score = score
                    best_config = config
                    best_spawn = unique_spawn_point
                    best_dmg = dmg

        return best_spawn, best_config, best_dmg, best_score

    def attack(self, game_state, best_spawn, best_config, score):
        if score > 0:
            for unit in best_config:
                game_state.attempt_spawn(unit[0], best_spawn, unit[1])


    def support(self, game_state):
        support_loc = []
        for i in [13, 14]:
            for j in [0, 1, 2, 3]:
                support_loc.append([i, j])
        
        if game_state.get_resources(1)[1] <= 5:
            game_state.attempt_spawn(SUPPORT, support_loc)

    def guage_defense(self, unique_spawn_points, scores, cross_map):
        left = 0
        right = 0
        if len(scores) == 0:
            return (50, 50)
        else:
            for s in scores:
                score, spawn_point = s
                cross_x = cross_map[spawn_point][0]
                if cross_x < 14:
                    left += score
                else:
                    right += score
            return (left, right)

    def build_reactive_defenses(self, game_state, priority_left, priority_right):
        flip_left = lambda num : num
        flip_right = lambda num : 27 - num
        allocate = lambda total, left, right : ((total * left) / (left + right), (total * right) / (left + right))


        # Allocate resources to the left and right
        res_right, res_left = 0, 0
        if priority_left + priority_right < 1:
            res_left, res_right = game_state.get_resource(0) / 2, game_state.get_resource(0) / 2
        else:
            res_left, res_right = allocate(game_state.get_resource(0), priority_left, priority_right) 

        for level, level_func in enumerate(self.levels):
            # Build up to right
            if res_right >= 6:
                self.print_map(game_state)

                before = game_state.get_resource(0)
                level_func(game_state, flip_right)
                used = before - game_state.get_resource(0)
                res_right -= used
            
            if res_left >= 6:
                self.print_map(game_state)

                before = game_state.get_resource(0)
                level_func(game_state, flip_left)
                used = before - game_state.get_resource(0)
                res_left -= used

        for level_func in self.levels:
            if game_state.get_resource(0) >= 6:
                if priority_left > priority_right:
                    level_func(game_state, flip_left)
                else:
                    level_func(game_state, flip_right)

    def opponent_attack_simulation(self, game_state):
        def check_all_paths(gs, visited_points, unique_spawn_points, cross_map):  
            def check_spawn_point(gs, spawn_point, unique_spawn_points, visited_points):
                
                if not gs.can_spawn(SCOUT, spawn_point):
                    return

                path = gs.find_path_to_edge(spawn_point)
                target_edge = gs.get_target_edge(spawn_point)
                
                max_y = spawn_point[1]
                for point in path:
                    if point[1] == 14:
                        cross_map[tuple(spawn_point)] = point
                    max_y = max(point[1], max_y)

                if max_y < 14:
                    return

                for point in path:
                    x, y, z = *point, target_edge
                    if y < 14:
                        if (x, y, z) in visited_points:
                            return
                        else:
                            visited_points.add((x, y, z))
                unique_spawn_points.append(tuple(spawn_point))  
            
            possible_spawn_points = gs.game_map.get_edge_locations(gs.game_map.BOTTOM_LEFT) + gs.game_map.get_edge_locations(gs.game_map.BOTTOM_RIGHT)
            for spawn_point in possible_spawn_points:
                check_spawn_point(gs, spawn_point, unique_spawn_points, visited_points)

        # Somehow sample so we don't do all the spawn points
        def filter_spawn_points(spawn_points):
            return random.sample(spawn_points, min(7, len(spawn_points)))

        def simulate_damage(gs, unique_spawn_points):
            # gamelib.debug_write(unique_spawn_points)
            scores = []
            
            for unique_spawn_point in unique_spawn_points:
                sim = Simulator(self.config, gs)
                sim.place_mobile_units([[SCOUT, gs.number_affordable(SCOUT), list(unique_spawn_point)]])
                dmg, turrets, structures = sim.simulate()
                # gamelib.debug_write('dmg, turrets, structures: ', dmg, turrets, structures)
                score = dmg * 6 + turrets * 6 + structures
                if dmg > gs.my_health:
                    score = 1000
                scores.append((score, tuple(unique_spawn_point)))
            return sorted(scores, reverse = True)

        gs = self.flip_board_state(game_state)
        visited_points = set()
        unique_spawn_points = list()
        cross_map = dict()
        check_all_paths(gs, visited_points, unique_spawn_points, cross_map)
        unique_spawn_points = filter_spawn_points(unique_spawn_points)
        scores = simulate_damage(gs, unique_spawn_points)
        return unique_spawn_points, scores, cross_map

    def flip_board_state(self, game_state):
        gs = copy.deepcopy(game_state)
        gs.my_health, gs.enemy_health, gs.my_time, gs.enemy_time = game_state.enemy_health, game_state.my_health, game_state.enemy_time, game_state.my_time
        gs.game_map = gamelib.game_map.GameMap(self.config)
        gs.HALF_ARENA, gs.ARENA_SIZE = gs.game_map.HALF_ARENA, gs.game_map.ARENA_SIZE
        size = gs.game_map.ARENA_SIZE

        for x in range(size):
            for y in range(size):
                player_at_xy = 0 if y < size // 2 else 1

                # Documentation is wrong, accessing game_map can return None
                unit_list_xy = game_state.game_map[x, size - y - 1]
                if unit_list_xy:
                    for unit in unit_list_xy:
                        gs.game_map.add_unit(unit.unit_type, [x, y], player_at_xy)
        return gs

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
