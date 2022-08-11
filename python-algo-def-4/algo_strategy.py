import gamelib
import random
import math
import warnings
from sys import maxsize, stderr
import json
# import tensorflow
from simulator import Simulator, timer
import copy

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

    def starter_strategy(self, game_state:gamelib.GameState):
        gamelib.debug_write("opponent attack simulation")
        unique_spawn_points, scores, cross_map = self.opponent_attack_simulation(game_state)

        gamelib.debug_write("build_reactive_defenses based on simulation result:" + str(scores))
        self.build_reactive_defenses(game_state, unique_spawn_points, scores, cross_map)
        
        gamelib.debug_write("build_defenses")
        self.build_defences(game_state)
        gamelib.debug_write("maybe_spawn_interceptors")
        self.maybe_spawn_interceptors()

    def build_reactive_defenses(self, game_state, unique_spawn_points, scores, cross_map):
        pass

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
        def get_farthest_spawn_points(spawn_points):
            # if len(spawn_points) <= 3:
            #     return spawn_points
            
            # point_min = min(spawn_points)
            # point_max = max(spawn_points)
            # best_point_index, best_point_value = 0, 0
            # for point_index, point in enumerate(spawn_points):
            #     point_value = min(point[0] - point_min[0], point_max[0] - point[0])
            #     if point_value > best_point_value:
            #         best_point_value, best_point_index = point_value, point_index
            # point_mid = spawn_points[best_point_index]
            # return [point_min, point_mid, point_max]
            return spawn_points

        def simulate_damage(gs, unique_spawn_points):
            gamelib.debug_write(unique_spawn_points)
            scores = []
            
            for unique_spawn_point in unique_spawn_points:
                sim = Simulator(self.config, gs)
                gamelib.debug_write(type(unique_spawn_point))
                sim.place_mobile_units([[SCOUT, gs.number_affordable(SCOUT), list(unique_spawn_point)]])
                dmg, turrets, structures = sim.simulate()
                gamelib.debug_write(dmg, turrets, structures)
                score = dmg * 3 + turrets * 6 + structures
                if dmg > gs.my_health:
                    score = 1000
                scores.append((score, tuple(unique_spawn_point)))
            return sorted(scores, reverse = True)

        gs = self.flip_board_state(game_state)
        visited_points = set()
        unique_spawn_points = list()
        cross_map = dict()
        check_all_paths(gs, visited_points, unique_spawn_points, cross_map)
        unique_spawn_points = get_farthest_spawn_points(unique_spawn_points)
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

    def defense_priority_1(self, game_state):
        main_turrets_loc = [[3, 12], [24, 12]]
        main_turrets_walls_loc = [[3, 13], [24, 13]]
        back_walls_loc = [[5, 10], [22, 10]] + [[col, 9] for col in range(6, 22)]
        
        game_state.attempt_spawn(TURRET, main_turrets_loc)
        game_state.attempt_spawn(WALL, back_walls_loc)
        game_state.attempt_spawn(WALL, main_turrets_walls_loc)
        game_state.attempt_upgrade(main_turrets_walls_loc + main_turrets_loc)

    def defense_priority_2(self, game_state):
        other_turrets_loc = [[4, 11], [23, 11]]
        front_walls_loc = [[0, 13], [27, 13], [1, 13], [26, 13]]

        game_state.attempt_spawn(WALL, front_walls_loc)
        game_state.attempt_upgrade(front_walls_loc)
        game_state.attempt_spawn(TURRET, other_turrets_loc)
        game_state.attempt_upgrade(other_turrets_loc)

    def defense_priority_3(self, game_state):
        other_turrets_loc = [[1, 12], [26, 12]]

        game_state.attempt_spawn(TURRET, other_turrets_loc)
        game_state.attempt_upgrade(other_turrets_loc)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        self.defense_priority_1(game_state)
        self.defense_priority_2(game_state)
        self.defense_priority_3(game_state)

        

    def maybe_spawn_interceptors(self):
        return


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
