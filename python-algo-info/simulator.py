from pathlib import Path
import readline
import gamelib
from gamelib import debug_write as printd
import random
import math
import warnings
import os
from sys import maxsize
import json
from typing import List
from copy import copy, deepcopy
from collections import deque

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
        self.health = unit.health*count

    def set_target_edge(self, tid):
        self.target_edge = tid

    def update_path(self, path):
        self.path = deque(deepcopy(path))
        # for p in path:
            # self.path.append(p)


class Simulator:
    def __init__(self, config, cloned_game_state : gamelib.GameState):
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        self.static_changed = True
        self.game_state = cloned_game_state
        self.our_scouts:List[Simunit] = []
        self.our_demos:List[Simunit] = []
        self.our_inters:List[Simunit] = []
        self.their_turrets:List[Simunit] = []

        self.graveyard:List[Simunit] = []

        self.tick = 0
        self.damage = 0
        self.pather = self.game_state._shortest_path_finder

        self.pather.initialize_map(self.game_state)
        self.pather.initialize_blocked()

        for cell in cloned_game_state.game_map:
            state = cloned_game_state.game_map[cell]
            if state:
                unit:gamelib.GameUnit = state[0]
                if unit.unit_type == TURRET:
                    self.their_turrets.append(unit)

        printd(self.their_turrets)

    # Units = list of [type, [x,y]]
    def place_mobile_units(self, units):
        self.our_scouts = []
        self.our_demos = []
        self.our_inters = []
        for unit in units:
            type = unit[0]
            x = unit[1][0]
            y = unit[1][1]
            gameunit = gamelib.GameUnit(type, self.game_state.config, 0, None, x, y)
            simunit = Simunit(gameunit)
            simunit.set_target_edge(self.game_state.get_target_edge(unit[1]))
            if type == SCOUT:
                self.our_scouts.append(simunit)
            elif type == DEMOLISHER:
                self.our_demos.append(simunit)
            else:
                self.our_inters.append(simunit)
            
            if not gameunit.stationary:
                self.game_state.game_map[x, y].append(gameunit)
            else:
                self.game_state.game_map[x, y] = [gameunit]
        
        printd(self.our_scouts)

            
    # True = dies
    def move_unit(self, simunit:Simunit):
        x,y = simunit.unit.x, simunit.unit.y

        if simunit.repath:
            path = self.pather.navigate_multiple_endpoints([x,y], 
                self.game_state.game_map.edges[simunit.target_edge], 
                self.game_state)
            simunit.update_path(path)
            simunit.repath = False


        # TODO: Self-destruct (but probably not necessary for attack sim)
        if len(simunit.path) == 0:
            self.graveyard.append(simunit)
            self.resolve_end_of_path([x,y])
            return True# But this unit has to be removed at the end of the round

        self.game_state.game_map[x, y].remove(simunit.unit)
        x,y = simunit.path.pop()
        self.game_state.game_map[x, y].append(simunit.unit)
        simunit.unit.set_position(x,y)
        return False


    #def can be optimized
    def resolve_end_of_path(self, loc):
        if loc in self.game_state.game_map.edges:
            self.damage += 1


    def toggle_blocked(self, coords):
        for coord in coords:
            self.pather.game_map[coord[0]][coord[1]].blocked \
                = not self.pather.game_map[coord[0]][coord[1]].blocked


    def mark_recompute_paths(self):
        for simunit in self.our_scouts:
            simunit.repath = True
        for simunit in self.our_demos:
            simunit.repath = True
        for simunit in self.our_inters:
            simunit.repath = True


    def simulate(self):
        while self.our_demos or self.our_scouts or self.our_inters:
            printd(f"Simulating tick {self.tick}")
            self.simulate_tick()
        return self.damage

    def simulate_tick(self):
        # 1. TODO: support granting shields

        # 2. Each unit attempts to move
        for simunit in self.our_scouts:
            self.move_unit(simunit)
        for simunit in self.our_demos:
            self.move_unit(simunit)
        if self.tick %4 == 0:
            for simunit in self.our_inters:
                self.move_unit(simunit)
        
        # 3. Each unit attacks
        struct_destroyed = False
        # BIG TODO - first iteration can probably use the get_target function from game_state
        # We would iterate through all the elements in the our/their lists and calculate the attack
        # If an enemy structure is destroyed, we must set struct_destroyed to True to trigger repathing



        # 4. Remove 0 health units
        for simunit in self.graveyard:
            if simunit.unit.unit_type == SCOUT:
                self.our_scouts.remove(simunit)
            elif simunit.unit.unit_type == DEMOLISHER:
                self.our_demos.remove(simunit)
            elif simunit.unit.unit_type == INTERCEPTOR:
                self.our_inters.remove(simunit)
            elif simunit.unit.unit_type == TURRET:
                self.their_turrets.remove(simunit)

        self.tick += 1

        if struct_destroyed:
            self.mark_recompute_paths()
        return