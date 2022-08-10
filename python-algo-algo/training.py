import readline
import gamelib
import random
import math
import warnings
import os
from sys import maxsize
import json

class TrainingScenario:
    def __init__(self, before, after):
        self.before = before
        self.after = after
    
    def __str__(self):
        return self.before + " --> " + self.after

class TrainingDataset:
    def __init__(self):
        self.dataset = []

    def __str__(self):
        return "\n".join([str(sc) for sc in self.dataset])
    def add_data(self, before, after):
        self.dataset.append(TrainingScenario(before, after))
    
    


def load_replay(dataset, path):
    with open (path, 'r') as f:
        replay_lines = f.readlines()
    # lines 0-2 are useless

    for _ in range(3):
        replay_lines.pop(0)
    
    # print(replay_lines[0])

    for i in range(len(replay_lines)-1):
        before_json = json.loads(replay_lines[i])
        if before_json['turnInfo'][0] > 0:
            continue
        dataset.add_data(replay_lines[i], replay_lines[i+1])
        # print(before_json['turnInfo'])

def load_replay_from_folder(dataset, folder):
    files = os.listdir(folder)
    for file in files:
        load_replay(dataset, f"{folder}/{file}")


def main():
    dataset = TrainingDataset()
    load_replay_from_folder(dataset, '../replays')
    print(dataset)


if __name__ == "__main__":
    main()