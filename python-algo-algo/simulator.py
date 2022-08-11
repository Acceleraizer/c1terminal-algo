from pathlib import Path
import readline
import gamelib
from gamelib import debug_write as printd
import random
import math
import warnings
import os
from sys import maxsize, stderr
import json
from typing import List
from copy import copy, deepcopy
from collections import deque
from gamelib.util import timer


edge_locations = [[0, 13], [27, 13], [1, 12], [26, 12], [2, 11], 
                  [25, 11], [3, 10], [24, 10], [4, 9], [23, 9], 
                  [5, 8], [22, 8], [6, 7], [21, 7], [7, 6], [20, 6], 
                  [8, 5], [19, 5], [9, 4], [18, 4], [10, 3], [17, 3], 
                  [16, 2], [12, 1], [15, 1], [13, 0], [14, 0]]

# target_offsets = [[1, [0, 1], [0,-1], [1,0], [-1,0]],
#                   [2, [1,1], [1,-1], [-1,1], [1,1]],
#                   [4, [0,2], [0,-2], [2,0], [-2,0]],
#                   [5, [1,2], [-1,2], [1,-2],[-1,-2], [2,1], [2,-1], [-2,1], [-2,-1]],
#                   [8, [2,2], [2,-2], [-2,2], [-2,-2]]]




class Simunit:
    path : deque
    repath = True
    target_edge = -1

    def __init__(self, unit:gamelib.GameUnit, count=1):
        self.unit = unit
        # Will use these to optimize later on
        self.count = count
        self.basecount = count
        self.health = unit.health
        self.base_health = unit.health
        self.attack_m = unit.damage_i
        self.attack_s = unit.damage_f

        self.count_to_fire = count
        self.graved = False

    def set_target_edge(self, tid):
        self.target_edge = tid

    def update_path(self, path):
        self.path = deque(deepcopy(path))
        # for p in path:
            # self.path.append(p)

    def __str__(self):
        return f"{'Enemy' if self.unit.player_index else 'Our' } {self.unit.unit_type} {self.count}x, [{self.unit.x},{self.unit.y}]"

class Simulator:
    def __init__(self, config, game_state : gamelib.GameState):
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        self.our_scouts:List[Simunit] = []
        self.our_demos:List[Simunit] = []
        self.our_inters:List[Simunit] = []
        self.their_turrets:List[Simunit] = []

        self.graveyard:List[Simunit] = []

        self.game_state:gamelib.GameState = self.clone_game(game_state)

        self.tick = 0
        self.damage = 0
        self.pather = self.game_state._shortest_path_finder

        self.pather.initialize_map(game_state)
        self.pather.initialize_blocked()

        # printd(f"Turrets: {self.their_turrets}")

    def clone_game(self, game_state:gamelib.GameState):
        clone = gamelib.GameState.__new__(gamelib.GameState)
        clone.game_map = gamelib.GameMap(game_state.config)
        # convert units to simunits
        for y in range(28):
            for x in range (28):
                if clone.game_map.in_arena_bounds([x,y]):
                    if game_state.game_map[x,y]:
                        clone.game_map[x,y] = []
                        for unit in game_state.game_map[x,y]:
                            # clonedunit = deepcopy(unit)
                            simunit = Simunit(unit)
                            clone.game_map[x,y].append(simunit)
                            if unit.unit_type == TURRET:
                                self.their_turrets.append(simunit)

        clone._shortest_path_finder = game_state._shortest_path_finder
        clone.ARENA_SIZE = game_state.ARENA_SIZE
        clone.HALF_ARENA = game_state.HALF_ARENA
        clone.config = game_state.config
        clone.game_map.edges = game_state.game_map.edges
        return clone


    # Units = list of [type, count, [x,y]]
    def place_mobile_units(self, units):
        self.our_scouts = []
        self.our_demos = []
        self.our_inters = []
        for unit in units:
            type = unit[0]
            x = unit[2][0]
            y = unit[2][1]
            gameunit = gamelib.GameUnit(type, self.game_state.config, 0, None, x, y)
            simunit = Simunit(gameunit, unit[1])
            simunit.set_target_edge(self.game_state.get_target_edge(unit[2]))
            if type == SCOUT:
                self.our_scouts.append(simunit)
            elif type == DEMOLISHER:
                self.our_demos.append(simunit)
            else:
                self.our_inters.append(simunit)
            
            self.game_state.game_map[x, y].append(simunit)

        
        # printd(self.our_scouts)

            
    # True = dies
    # @timer
    def move_unit(self, simunit:Simunit):
        x,y = simunit.unit.x, simunit.unit.y

        if simunit.repath:
            path = self.pather.navigate_multiple_endpoints([x,y], 
                self.game_state.game_map.edges[simunit.target_edge], 
                self.game_state)
            simunit.update_path(path)
            simunit.repath = False
            # self.pather.print_map()
            # self.print_path(simunit)

        # TODO: Self-destruct (but probably not necessary for attack sim)
        if len(simunit.path) == 0:
            self.graveyard.append(simunit)
            simunit.graved = True
            self.resolve_end_of_path(simunit)
            return True# But this unit has to be removed at the end of the round

        self.game_state.game_map[x, y].remove(simunit)
        x,y = simunit.path.popleft()
        self.game_state.game_map[x, y].append(simunit)
        simunit.unit.set_position(x,y)
        return False


    #def can be optimized
    def resolve_end_of_path(self, simunit:Simunit):
        loc = [simunit.unit.x, simunit.unit.y]
        if loc in self.game_state.game_map.edges[simunit.target_edge]:
            self.damage += simunit.count

    def get_target(self, attacking_unit:Simunit):
        attacker_location = [attacking_unit.unit.x, attacking_unit.unit.y]
        possible_locations = self.game_state.game_map.get_locations_in_range(attacker_location, attacking_unit.unit.attackRange)
        target = None
        target_stationary = True
        target_distance = maxsize
        target_health = maxsize
        target_y = self.game_state.ARENA_SIZE
        target_x_distance = 0

        for location in possible_locations:
            for simunit in self.game_state.game_map[location]:
                if simunit.count <= 0:
                    continue
                unit_stationary = simunit.unit.stationary
                if simunit.unit.player_index == attacking_unit.unit.player_index or (attacking_unit.unit.damage_f == 0 and unit_stationary) or (attacking_unit.unit.damage_i == 0 and not(unit_stationary)):
                    continue

                new_target = False
                unit_distance = self.game_state.game_map.sq_distance_between_locations(location, attacker_location)
                unit_health = simunit.health
                unit_y = simunit.unit.y
                unit_x_distance = abs(self.game_state.HALF_ARENA - 0.5 - simunit.unit.x)

                if target_stationary and not unit_stationary:
                    new_target = True
                elif not target_stationary and unit_stationary:
                    continue
                
                if target_distance > unit_distance:
                    new_target = True
                elif target_distance < unit_distance and not new_target:
                    continue

                if target_health > unit_health:
                    new_target = True
                elif target_health < unit_health and not new_target:
                    continue

                # Compare height heuristic relative to attacking unit's player index
                if attacking_unit.unit.player_index == 0:
                    if target_y > unit_y:
                        new_target = True
                    elif target_y < unit_y and not new_target:
                        continue
                else:
                    if target_y < unit_y:
                        new_target = True
                    elif target_y > unit_y and not new_target:
                        continue

                if target_x_distance < unit_x_distance:
                    new_target = True
                
                if new_target:
                    target = simunit
                    target_stationary = unit_stationary
                    target_distance = unit_distance
                    target_health = unit_health
                    target_y = unit_y
                    target_x_distance = unit_x_distance
        return target


    def mark_recompute_paths(self):
        for simunit in self.our_scouts:
            simunit.repath = True
        for simunit in self.our_demos:
            simunit.repath = True
        for simunit in self.our_inters:
            simunit.repath = True

    @timer
    def simulate(self):
        while self.our_demos or self.our_scouts or self.our_inters:
            self.simulate_tick()
        return self.damage

    def simulate_tick(self):
        # printd(f"Begin tick #{self.tick}, scouts = {self.our_scouts}")
        # 1. TODO: support granting shields
        self.apply_shielding()

        # 2. Each unit attempts to move
        self.move_all_units()
        
        # 3. Each unit attacks
        # first iteration can probably use the get_target function from game_state
        # We would iterate through all the elements in the our/their lists and calculate the attack
        # If an enemy structure is destroyed, we must set struct_destroyed to True to trigger repathing
        struct_destroyed =  self.resolve_attacks()

        # 4. Remove 0 health units
        self.clean_graveyard()
        self.update_counts()
        self.tick += 1

        if struct_destroyed:
            self.mark_recompute_paths()
        return

    def apply_shielding(self):
        
        return


    def move_all_units(self):
        for simunit in self.our_scouts:
            self.move_unit(simunit)
        for simunit in self.our_demos:
            self.move_unit(simunit)
        if self.tick %4 == 0:
            for simunit in self.our_inters:
                self.move_unit(simunit)

    def resolve_attacks(self):
        struct_destroyed = False
        struct_destroyed = self.resolve_attacks_per_list(self.our_scouts) or struct_destroyed
        struct_destroyed = self.resolve_attacks_per_list(self.our_demos) or struct_destroyed
        struct_destroyed = self.resolve_attacks_per_list(self.our_inters) or struct_destroyed
        struct_destroyed = self.resolve_attacks_per_list(self.their_turrets) or struct_destroyed
        return struct_destroyed


    def resolve_attacks_per_list(self, list):
        struct_destroyed = False
        for simunit in list:
            simunit.count_to_fire = simunit.basecount
            while simunit.count_to_fire > 0:
                target:Simunit = self.get_target(simunit)
                # printd(f"<{simunit}> attacks <{target if target else 'NONE'}>")
                if not target:
                    break
                ko = self.resolve_battle(simunit, target)

                struct_destroyed = struct_destroyed or (ko and target.unit.stationary)

        return struct_destroyed

    def resolve_battle(self, attacker:Simunit, defender:Simunit):
        if defender.unit.stationary:
            atk = attacker.attack_s
        else:
            atk = attacker.attack_m
        
        # TODO make the loop less dumb
        while attacker.count_to_fire > 0:
            attacker.count_to_fire -= 1
            defender.health -= atk
            # printd(f"<{attacker.unit}> deals {atk} damage to <{defender.unit}>! Remaning: {defender.health},{defender.count}x. To fire: {attacker.count_to_fire}")
            if defender.health <= 0:
                defender.health = defender.base_health
                defender.count -= 1
                if defender.count == 0 and (not defender.graved):
                    self.graveyard.append(defender)
                    return True

        return False
    

    def clean_graveyard(self):
        n = len(self.graveyard)
        for _ in range(n):
            simunit = self.graveyard.pop()
            printd(f"Goodbye <{simunit}>")
            if simunit.unit.unit_type == SCOUT:
                self.our_scouts.remove(simunit)
            elif simunit.unit.unit_type == DEMOLISHER:
                self.our_demos.remove(simunit)
            elif simunit.unit.unit_type == INTERCEPTOR:
                self.our_inters.remove(simunit)
            elif simunit.unit.unit_type == TURRET:
                self.their_turrets.remove(simunit)
            
            x,y = simunit.unit.x, simunit.unit.y
            self.game_state.game_map[x,y].remove(simunit)
            if simunit.unit.stationary:
                self.pather.game_map[x][y].blocked = False


    def update_counts(self):
        for simunit in self.our_scouts:
            simunit.basecount = simunit.count
        for simunit in self.our_demos:
            simunit.basecount = simunit.count
        for simunit in self.our_inters:
            simunit.basecount = simunit.count


    def print_path(self, simunit:Simunit):
        for y in range(27,0,-1):
            for x in range (28):
                if x+y<=12 or x+y >= 42 or y-x>=15 or y-x<=-15:
                    stderr.write("  ")
                    continue
                node = self.pather.game_map[x][y]
                if [x,y] in simunit.path:
                    stderr.write(" *")
                elif node.blocked:
                    stderr.write(" X")
                else:
                    stderr.write(" .")
            stderr.write("\n")