from enum import Enum

# 상위 카테고리: action_type
class ActionType(str, Enum):
    DAY_CYCLE = "DAY_CYCLE"
    TIME_EVENT = "TIME_EVENT"
    INVENTORY = "INVENTORY"
    FARMING = "FARMING"
    HOUSING = "HOUSING"
    COOKING = "COOKING"
    FISHING = "FISHING"
    TRADE = "TRADE"
    CRAFTING = "CRAFTING"

# 세부 액션: action_name
class ActionName(str, Enum):
    # DAY_CYCLE
    START_DAY = "start_day"
    SLEEP = "sleep"

    # TIME_EVENT
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"

    # INVENTORY
    PICKUP_ITEM = "pickup_item"
    DROP_ITEM = "drop_item"
    EQUIP_ITEM = "equip_item"

    # FARMING
    PLANT_CROP = "plant_crop"
    WATER_CROP = "water_crop"
    GROW_CROP = "grow_crop"
    HARVEST_CROP = "harvest_crop"

    # HOUSING
    PLACE_HOUSING = "place_housing"
    REMOVE_HOUSING = "remove_housing"

    # COOKING
    START_COOKING = "start_cooking"
    PROGRESS_COOKING = "progress_cooking"
    FINISH_COOKING = "finish_cooking"

    # FISHING
    CAST_BAIT = "cast_bait"
    HOOK_BITE = "hook_bite"
    FINISH_FISHING = "finish_fishing"

    # TRADE
    BUY_ITEM = "buy_item"
    SELL_ITEM = "sell_item"

    # CRAFTING
    CRAFT_ITEM = "craft_item"
