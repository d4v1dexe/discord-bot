import json
import random
import time
from pathlib import Path

DATA_FILE = Path(__file__).parent / 'fishing_data.json'
CATCH_COOLDOWN = 15  # seconds between casts, per user

# Rod levels: level -> name, cost to upgrade INTO that level.
RODS = {
    1: {'name': 'Ast', 'cost': 0},
    2: {'name': 'Bambusrute', 'cost': 100},
    3: {'name': 'Karbonrute', 'cost': 300},
    4: {'name': 'Profirute', 'cost': 800},
    5: {'name': 'Legendäre Rute', 'cost': 2000},
}
MAX_ROD_LEVEL = max(RODS)

# Fish: value in Coins, rarity weight (higher = more common), minimum rod
# level required to be able to catch it at all.
FISH = [
    {'name': 'Anchovy', 'emoji': '🐟', 'value': 5, 'weight': 40, 'min_rod': 1},
    {'name': 'Hering', 'emoji': '🐠', 'value': 8, 'weight': 30, 'min_rod': 1},
    {'name': 'Forelle', 'emoji': '🐡', 'value': 15, 'weight': 20, 'min_rod': 2},
    {'name': 'Lachs', 'emoji': '🍣', 'value': 25, 'weight': 15, 'min_rod': 2},
    {'name': 'Thunfisch', 'emoji': '🐋', 'value': 45, 'weight': 10, 'min_rod': 3},
    {'name': 'Schwertfisch', 'emoji': '⚔️', 'value': 70, 'weight': 6, 'min_rod': 3},
    {'name': 'Hai', 'emoji': '🦈', 'value': 120, 'weight': 4, 'min_rod': 4},
    {'name': 'Oktopus', 'emoji': '🐙', 'value': 180, 'weight': 2, 'min_rod': 4},
    {'name': 'Goldfisch', 'emoji': '✨', 'value': 300, 'weight': 1, 'min_rod': 5},
    {'name': 'Kraken', 'emoji': '👑', 'value': 500, 'weight': 0.5, 'min_rod': 5},
]

_last_cast = {}  # user_id -> monotonic timestamp of the last cast, in-memory only


def _load():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    try:
        DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    except OSError as e:
        print(f'Failed to save fishing data: {e}')


def _get_player(data, user_id):
    key = str(user_id)
    if key not in data:
        data[key] = {'balance': 0, 'rod': 1, 'inventory': {}}
    return data[key]


def rod_name(level):
    return RODS.get(level, RODS[MAX_ROD_LEVEL])['name']


def cooldown_remaining(user_id):
    last = _last_cast.get(user_id)
    if last is None:
        return 0
    remaining = CATCH_COOLDOWN - (time.monotonic() - last)
    return max(0, remaining)


def cast(user_id):
    """Attempt a catch. Returns (fish_dict, None) on success, or (None, message) if on cooldown."""
    remaining = cooldown_remaining(user_id)
    if remaining > 0:
        return None, f'Die Angel braucht noch {remaining:.0f}s Ruhe, bevor du wieder auswerfen kannst.'

    data = _load()
    player = _get_player(data, user_id)
    rod_level = player['rod']

    pool = [f for f in FISH if f['min_rod'] <= rod_level]
    fish = random.choices(pool, weights=[f['weight'] for f in pool], k=1)[0]

    inv = player['inventory']
    inv[fish['name']] = inv.get(fish['name'], 0) + 1
    _save(data)
    _last_cast[user_id] = time.monotonic()
    return fish, None


def inventory_text(user_id):
    data = _load()
    player = _get_player(data, user_id)
    inv = player['inventory']
    if not inv:
        return 'Dein Inventar ist leer. Zeit zum Angeln! (`$angeln`)'
    lines = []
    for name, count in inv.items():
        fish = next((f for f in FISH if f['name'] == name), None)
        emoji = fish['emoji'] if fish else '🐟'
        lines.append(f'{emoji} {name} x{count}')
    return 'Dein Inventar:\n' + '\n'.join(lines)


def sell(user_id, fish_name=None):
    """Sell one fish type (fish_name), or everything if fish_name is None.
    Returns (earned, sold_lines); sold_lines is None if there was nothing to sell."""
    data = _load()
    player = _get_player(data, user_id)
    inv = player['inventory']

    if not inv:
        return 0, None

    lookup = {f['name'].lower(): f for f in FISH}

    if fish_name is None:
        earned = 0
        lines = []
        for name, count in list(inv.items()):
            fish = lookup.get(name.lower())
            value = fish['value'] if fish else 0
            earned += value * count
            lines.append(f'{name} x{count} -> {value * count} Coins')
        inv.clear()
        player['balance'] += earned
        _save(data)
        return earned, lines

    key = fish_name.lower()
    match = next((name for name in inv if name.lower() == key), None)
    if match is None:
        return 0, None

    count = inv.pop(match)
    fish = lookup.get(key)
    value = fish['value'] if fish else 0
    earned = value * count
    player['balance'] += earned
    _save(data)
    return earned, [f'{match} x{count} -> {earned} Coins']


def balance(user_id):
    data = _load()
    return _get_player(data, user_id)['balance']


def shop_text(user_id):
    data = _load()
    player = _get_player(data, user_id)
    current = player['rod']
    lines = [
        f'Aktuelle Rute: {rod_name(current)} (Level {current}), Guthaben: {player["balance"]} Coins',
        '',
    ]
    for level, info in RODS.items():
        if level <= current:
            marker = ' (aktuell)' if level == current else ''
            lines.append(f'Level {level}: {info["name"]}{marker}')
        else:
            unlocks = [f['name'] for f in FISH if f['min_rod'] == level]
            unlock_text = f' -- schaltet frei: {", ".join(unlocks)}' if unlocks else ''
            lines.append(f'Level {level}: {info["name"]} -- {info["cost"]} Coins{unlock_text}')
    lines.append('')
    lines.append('Kauf mit `$rute`')
    return '\n'.join(lines)


def upgrade_rod(user_id):
    """Returns (success, message)."""
    data = _load()
    player = _get_player(data, user_id)
    current = player['rod']

    if current >= MAX_ROD_LEVEL:
        return False, f'Du hast schon die beste Rute ({rod_name(current)}).'

    next_level = current + 1
    cost = RODS[next_level]['cost']
    if player['balance'] < cost:
        missing = cost - player['balance']
        return False, f'Die {RODS[next_level]["name"]} kostet {cost} Coins, dir fehlen noch {missing}.'

    player['balance'] -= cost
    player['rod'] = next_level
    _save(data)
    return True, f'Glückwunsch! Du angelst jetzt mit der {RODS[next_level]["name"]} (Level {next_level}).'
