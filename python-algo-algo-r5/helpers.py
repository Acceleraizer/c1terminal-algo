import gamelib


def compute_refund(game_state:gamelib.GameState, loc):
    unit_list = game_state.game_map[loc]
    if not unit_list:
        return 0
    unit = unit_list[0]
    cost = unit.cost[0]
    if unit.upgraded:
        cost += unit.upgrade.cost[0]

    return unit.health/unit.max_health * cost