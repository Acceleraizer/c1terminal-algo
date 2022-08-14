from cgi import print_directory
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
from gamelib.navigation import ShortestPathFinder


edge_locations = [[0, 13], [27, 13], [1, 12], [26, 12], [2, 11], 
                  [25, 11], [3, 10], [24, 10], [4, 9], [23, 9], 
                  [5, 8], [22, 8], [6, 7], [21, 7], [7, 6], [20, 6], 
                  [8, 5], [19, 5], [9, 4], [18, 4], [10, 3], [17, 3], 
                  [16, 2], [12, 1], [15, 1], [13, 0], [14, 0]]



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
    def __init__(self, config, game_state : gamelib.GameState, perspective=0, clear=[], ignore_remove=False):
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, REMOVE, UPGRADE
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        REMOVE = config["unitInformation"][6]["shorthand"]
        UPGRADE = config["unitInformation"][7]["shorthand"]
        MP = 1
        SP = 0

        self.our_scouts:List[Simunit] = []
        self.our_demos:List[Simunit] = []
        self.our_inters:List[Simunit] = []
        self.our_supports:List[Simunit] = []
        self.their_turrets:List[Simunit] = []

        self.our_unit_support_pairs = deque()
        self.graveyard:List[Simunit] = []
        self.config = config

        self.game_state:gamelib.GameState = self.clone_game(game_state, perspective, clear, ignore_remove)

        self.tick = 0
        self.damage = 0
        self.turrets = 0
        self.structures = 0
        self.cost_damage = 0
        self.pather = ShortestPathFinder()

        self.pather.initialize_map(self.game_state)
        # printd("at init", self.pather.game_map[19][6])
        self.pather.initialize_blocked_alt()
        # printd("at init  blocked", self.pather.game_map[19][6])

        # printd(f"Turrets: {self.their_turrets}")

    # if perspective==1 we swap all structure player alignments
    def clone_game(self, game_state:gamelib.GameState, perspective, clear, ignore_remove):
        clone = gamelib.GameState.__new__(gamelib.GameState)
        clone.game_map = gamelib.GameMap(game_state.config)
        # convert units to simunits
        for y in range(28):
            for x in range(28):
                if clone.game_map.in_arena_bounds([x,y]):
                    if game_state.game_map[x,y]:
                        clone.game_map[x,y] = []
                        if [x,y] in clear:
                            # printd("IGNORING UNIT AT ", (x,y))
                            continue
                        for unit in game_state.game_map[x,y]:
                            if not unit.stationary or (unit.pending_removal and not ignore_remove): 
                                continue
                            
                            clonedunit = deepcopy(unit)
                            if perspective == 1:
                                if clonedunit.player_index == 0:
                                    clonedunit.player_index = 1
                                else:
                                    clonedunit.player_index = 0
                            simunit = Simunit(clonedunit)
                            clone.game_map[x,y].append(simunit)
                            # printd(simunit, clone.game_map[x,y][0] ,id(simunit), id(clone.game_map[x,y][0]), id(unit), id(clonedunit))
                            if clonedunit.unit_type == TURRET and clonedunit.player_index == 1:
                                # printd(simunit, "!!")
                                self.their_turrets.append(simunit)
                            if clonedunit.unit_type == SUPPORT and clonedunit.player_index == 0:
                                self.our_supports.append(simunit)
        # perform our build stack

        for type, x, y in game_state._build_stack:
            # printd("BUILD STACK ",type, (x,y))
            if type == UPGRADE:
                clone.game_map[x,y][0].unit.upgrade()
                continue
            elif type == REMOVE:
                continue # removes only take place the subsequent turn
            elif type in [TURRET, SUPPORT, WALL]:
                clonedunit = gamelib.GameUnit(type, game_state.config, 0,None, x, y)

                simunit = Simunit(clonedunit)
                if perspective == 1:
                    clonedunit.player_index = 1 - clonedunit.player_index
                clone.game_map[x,y].append(simunit)
                if type == TURRET and clonedunit.player_index == 1:
                    # printd(simunit, "!!")
                    self.their_turrets.append(simunit)
                if type == SUPPORT and clonedunit.player_index == 0:
                    self.our_supports.append(simunit)
                # printd(simunit)
                continue
        
        # clone._shortest_path_finder = game_state._shortest_path_finder
        clone._shortest_path_finder = gamelib.navigation.ShortestPathFinder()
        clone.turn_number = game_state.turn_number
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
            for support in self.our_supports:
                self.our_unit_support_pairs.append([simunit ,support])

        
        # printd(self.our_scouts)
            

    def compute_path(self, simunit:Simunit):
        x,y = simunit.unit.x, simunit.unit.y
        path = self.pather.navigate_multiple_endpoints([x,y], 
            self.game_state.game_map.edges[simunit.target_edge], 
            self.game_state)
        simunit.update_path(path)
        simunit.repath = False


    def sq_dist(self, location_1, location_2):
        x1, y1 = location_1
        x2, y2 = location_2

        return (x1 - x2)**2 + (y1 - y2)**2
    
    # returns a list of ticks where the unit will be in the blast radius
    # by default enemy controls interceptor (so should use perspective=1)
    def simulate_interceptor_blast(self, blast_loc, start_loc):
        gameunit = gamelib.GameUnit(SCOUT, self.config, 2, x=start_loc[0], y=start_loc[1])
        self.place_mobile_units(gameunit)
        list_in_range = []
        tick = 0
        max_health = 0
        if self.sq_dist(blast_loc, start_loc) <= 81:
            list_in_range.append(tick)

        while len(self.our_scouts) > 0:
            tick += 1
            self.apply_shielding()
            max_health = max(max_health, self.our_scouts[0].base_health)
            self.move_all_units()
            loc = [gameunit.x, gameunit.y]
            if self.sq_dist(blast_loc, loc) <= 81:
                list_in_range.append(tick)
            self.clean_graveyard()

        return list_in_range, max_health
            
    # use perspective=1
    def simulate_enemy_attack_path(self, start_loc):
        for simunit in self.game_state.game_map[start_loc]:
            if simunit.unit.stationary:
                return -1

        gameunit = gamelib.GameUnit(SCOUT, self.config, 2, x=start_loc[0], y=start_loc[1])
        simunit = Simunit(gameunit)
        simunit.set_target_edge(self.game_state.get_target_edge(start_loc))
        self.compute_path(simunit)
        # printd(start_loc)
        # self.print_path(simunit)

        #compute crossing point
        dq = simunit.path
        x = 13.5
        while len(dq) > 0:
            x, y = dq.popleft()
            if y == 13:
                break
        if x < 13.5:
            return 0
        elif x > 13.5:
            return 1
        else:
            return -1


    # True = dies
    # @timer
    def move_unit(self, simunit:Simunit):
        x,y = simunit.unit.x, simunit.unit.y

        if simunit.repath:
            self.compute_path(simunit)
            # self.pather.print_map()
            # if self.game_state.turn_number == 14:
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

    # @timer
    def simulate(self):
        while self.our_demos or self.our_scouts or self.our_inters:
            self.simulate_tick()
        return self.damage, self.turrets, self.structures, self.cost_damage


    def simulate_tick(self):
        # printd(f"Begin tick #{self.tick}")
        # printd(self.game_state.game_map[19, 6], self.pather.game_map[19][6].blocked)
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
        n = len(self.our_unit_support_pairs)
        for _ in range(n):
            unit, supp = self.our_unit_support_pairs.popleft()
            xu, yu = unit.unit.x, unit.unit.y
            xs, ys = supp.unit.x, supp.unit.y
            if (xu-xs)**2 + (yu-ys)**2 <= 3.5**2:
                if supp.unit.upgraded:
                    unit.base_health += 2 + 0.34*yu
                else:
                    unit.base_health += 3
            else:
                self.our_unit_support_pairs.append([unit, supp])



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
                if not target:
                    break
                # printd(f"<{simunit}> attacks <{target} {id(target)}>")
                ko, ko_structure = self.resolve_battle(simunit, target)
                if ko:
                    # printd(target, "KO")
                    self.graveyard.append(target)
                struct_destroyed = struct_destroyed or ko_structure

        return struct_destroyed

    def resolve_battle(self, attacker:Simunit, defender:Simunit):
        if defender.unit.stationary:
            atk = attacker.attack_s
        else:
            atk = attacker.attack_m
        ko, ko_structure = False, False
        # TODO make the loop less dumb
        while attacker.count_to_fire > 0:
            attacker.count_to_fire -= 1
            defender.health -= atk
            # printd(f"<{attacker.unit}> deals {atk} damage to <{defender.unit}>! Remaning: {defender.health},{defender.count}x. To fire: {attacker.count_to_fire}")
            if defender.health <= 0:
                defender.health = defender.base_health
                defender.count -= 1
                if defender.count == 0 and (not defender.graved):
                    # self.graveyard.append(defender)
                    ko = True
                    defender.graved = True
                    if defender.unit.stationary:
                        ko_structure = True
                        self.structures += 1
                        self.cost_damage += defender.unit.cost[0]
                        if defender.unit.upgraded:
                            if defender.unit.unit_type == TURRET:
                                self.cost_damage += 6
                            elif defender.unit.unit_type == SUPPORT:
                                self.cost_damage += 2
                            else:
                                self.cost_damage += 1.5
                        if defender.unit.unit_type == TURRET:
                            self.turrets +=1
                break

        return ko, ko_structure
    

    def clean_graveyard(self):
        n = len(self.graveyard)
        for _ in range(n):
            simunit = self.graveyard.pop()
            # printd(f"Goodbye <{simunit}> ")
            if simunit.unit.unit_type == SCOUT:
                self.our_scouts.remove(simunit)
            elif simunit.unit.unit_type == DEMOLISHER:
                self.our_demos.remove(simunit)
            elif simunit.unit.unit_type == INTERCEPTOR:
                self.our_inters.remove(simunit)
            elif simunit.unit.unit_type == TURRET:
                self.their_turrets.remove(simunit)
            
            x,y = simunit.unit.x, simunit.unit.y
            # printd(f"Goodbye <{simunit}>, {self.game_state.game_map[x,y]} ")
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