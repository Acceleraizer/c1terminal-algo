from pathlib import Path
import readline
import gamelib
import random
import math
import warnings
import os
from sys import maxsize
import json
from typing import List
from queue import Queue

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
class PathedUnit:
    path : Queue

    def __init__(self, unit:gamelib.GameUnit):
        self.unit = unit

    def update_path(self, path):
        self.path = Queue(path)

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
        self.our_scouts = []
        self.our_demos = []
        self.our_inters = []
        self.their_turrets = []

        self.tick = 0
        self.pather = self.game_state._shortest_path_finder

        self.pather.initialize_map(self.game_state)
        self.pather.initialize_blocked()

        for cell in cloned_game_state.game_map:
            state = cloned_game_state.game_map[cell]
            if state:
                unit:gamelib.GameUnit = state[0]
                if unit.unit_type == TURRET:
                    self.their_turrets.append(unit)

        gamelib.debug_write(self.their_turrets)

    # Units = list of [type, [x,y]]
    def place_mobile_units(self, units):
        self.our_scouts = []
        self.our_demos = []
        self.our_inters = []
        for unit in units:
            type = unit[0]
            x = unit[1][0]
            y = unit[1][1]
            gameunit = gamelib.GameUnit(type, self.config, 0, None, x, y)
            pathedunit = PathedUnit(gameunit)
            if type == SCOUT:
                self.our_scouts.append(pathedunit)
            elif type == DEMOLISHER:
                self.our_demos.append(pathedunit)
            else:
                self.our_inters.append(pathedunit)
            

    def move_unit(self, pathedunit:PathedUnit, next):
        x,y = pathedunit.unit.x, pathedunit.unit.y
        self.game_state.game_map[x, y].remove(pathedunit.unit)
        x,y = pathedunit.path.pop()
        self.game_state.game_map[x, y]


    def toogle_blocked(self, coords):
        for coord in coords:
            self.pather.game_map[coord[0]][coord[1]].blocked \
                = not self.pather.game_map[coord[0]][coord[1]].blocked

    def compute_paths(self):

        self.static_changed = False


    def simulate(self):
        while self.our_demos or self.our_scouts or self.our_inters:
            self.simulate_tick()
            

    def simulate_tick(self):
        
        
        
        
        self.tick += 1

        return
        # if destroyed:
        #     self.static_changed = True