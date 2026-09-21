"""Angel-Minispiel.

Reine Spiellogik, kein discord-Import - damit das hier testbar bleibt und
bot.py nur die Discord-Seite macht.

Statt eines stumpfen Cooldowns gibt es jetzt einen Anbiss mit Aufgabe: wer
nicht rechtzeitig richtig antwortet, verliert den Fisch.
"""
import json
import random
import time
from datetime import date
from pathlib import Path

DATA_FILE = Path(__file__).parent / 'fishing_data.json'

# Nur noch ein kurzer Spam-Schutz, kein echter Wartecooldown mehr.
CAST_COOLDOWN = 3
DAILY_BONUS = 150
BAIT_COST = 40
BAIT_RARE_BOOST = 2.5

RODS = {
    1: {'name': 'Ast', 'cost': 0},
    2: {'name': 'Bambusrute', 'cost': 100},
    3: {'name': 'Karbonrute', 'cost': 300},
    4: {'name': 'Profirute', 'cost': 800},
    5: {'name': 'Stahlrute', 'cost': 2000},
    6: {'name': 'Tiefseerute', 'cost': 5000},
    7: {'name': 'Titanrute', 'cost': 12000},
    8: {'name': 'Legendäre Rute', 'cost': 30000},
    9: {'name': 'Poseidons Dreizack', 'cost': 75000},
}
MAX_ROD_LEVEL = max(RODS)

# value = Basiswert bei Durchschnittsgewicht. kg = (min, max).
FISH = [
    {'name': 'Anchovy',      'emoji': '🐟', 'value': 5,    'weight': 40,  'min_rod': 1, 'kg': (0.05, 0.3)},
    {'name': 'Hering',       'emoji': '🐠', 'value': 8,    'weight': 30,  'min_rod': 1, 'kg': (0.2, 0.8)},
    {'name': 'Forelle',      'emoji': '🐡', 'value': 15,   'weight': 20,  'min_rod': 2, 'kg': (0.4, 2.0)},
    {'name': 'Lachs',        'emoji': '🍣', 'value': 25,   'weight': 15,  'min_rod': 2, 'kg': (1.0, 6.0)},
    {'name': 'Thunfisch',    'emoji': '🐋', 'value': 45,   'weight': 10,  'min_rod': 3, 'kg': (10.0, 80.0)},
    {'name': 'Schwertfisch', 'emoji': '⚔️', 'value': 70,   'weight': 6,   'min_rod': 3, 'kg': (20.0, 120.0)},
    {'name': 'Hai',          'emoji': '🦈', 'value': 120,  'weight': 4,   'min_rod': 4, 'kg': (40.0, 300.0)},
    {'name': 'Oktopus',      'emoji': '🐙', 'value': 180,  'weight': 2,   'min_rod': 4, 'kg': (3.0, 25.0)},
    {'name': 'Rochen',       'emoji': '🥏', 'value': 260,  'weight': 2,   'min_rod': 5, 'kg': (15.0, 90.0)},
    {'name': 'Goldfisch',    'emoji': '✨', 'value': 400,  'weight': 1.5, 'min_rod': 5, 'kg': (0.1, 0.5)},
    {'name': 'Anglerfisch',  'emoji': '🎣', 'value': 700,  'weight': 1.2, 'min_rod': 6, 'kg': (5.0, 30.0)},
    {'name': 'Riesenkalmar', 'emoji': '🦑', 'value': 1100, 'weight': 0.8, 'min_rod': 6, 'kg': (50.0, 400.0)},
    {'name': 'Koboldhai',    'emoji': '👺', 'value': 1800, 'weight': 0.6, 'min_rod': 7, 'kg': (80.0, 210.0)},
    {'name': 'Eishai',       'emoji': '🧊', 'value': 2800, 'weight': 0.4, 'min_rod': 7, 'kg': (100.0, 600.0)},
    {'name': 'Kraken',       'emoji': '👑', 'value': 5000, 'weight': 0.25, 'min_rod': 8, 'kg': (200.0, 900.0)},
    {'name': 'Seeschlange',  'emoji': '🐉', 'value': 9000, 'weight': 0.15, 'min_rod': 9, 'kg': (300.0, 1500.0)},
    {'name': 'Leviathan',    'emoji': '🌊', 'value': 20000, 'weight': 0.05, 'min_rod': 9, 'kg': (800.0, 4000.0)},
]

# Schrott: kein Wert, aber Stimmung.
JUNK = [
    {'name': 'Alter Schuh', 'emoji': '👟'},
    {'name': 'Blechdose', 'emoji': '🥫'},
    {'name': 'Nasse Socke', 'emoji': '🧦'},
    {'name': 'Plastiktüte', 'emoji': '🛍️'},
    {'name': 'Einkaufswagen', 'emoji': '🛒'},
]
JUNK_CHANCE = 0.12
TREASURE_CHANCE = 0.04
TREASURE_COINS = (80, 600)

_last_cast = {}

_DEFAULT_STATS = {'casts': 0, 'caught': 0, 'escaped': 0, 'earned': 0, 'junk': 0, 'treasure': 0}


# --------------------------------------------------------------------------- Daten

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
    """Holt den Spieler und ergänzt fehlende Felder, damit alte Spielstände
    nach einem Update nicht kaputtgehen."""
    key = str(user_id)
    player = data.setdefault(key, {})
    player.setdefault('balance', 0)
    player.setdefault('rod', 1)
    player.setdefault('inventory', {})
    player.setdefault('bait', 0)
    player.setdefault('records', {})
    player.setdefault('last_daily', None)
    stats = player.setdefault('stats', {})
    for k, v in _DEFAULT_STATS.items():
        stats.setdefault(k, v)
    return player


def reset_player(user_id):
    data = _load()
    data.pop(str(user_id), None)
    _save(data)


def rod_name(level):
    return RODS.get(level, RODS[MAX_ROD_LEVEL])['name']


def cooldown_remaining(user_id):
    last = _last_cast.get(user_id)
    if last is None:
        return 0
    return max(0, CAST_COOLDOWN - (time.monotonic() - last))


# --------------------------------------------------------------------------- Anbiss

def _difficulty_for(fish):
    """Seltener Fisch -> schwerere Aufgabe."""
    if fish['weight'] >= 15:
        return 'leicht'
    if fish['weight'] >= 4:
        return 'mittel'
    return 'schwer'


_WORDS = ['angel', 'koeder', 'flosse', 'schuppe', 'harpune', 'netz', 'boot',
          'kescher', 'leine', 'haken', 'welle', 'tiefe', 'strom', 'anker']


def make_challenge(fish):
    """Baut die Aufgabe für den Anbiss.

    Gibt ein dict zurück: prompt (Text), answer (erwartete Antwort, lowercase),
    timeout (Sekunden).
    """
    level = _difficulty_for(fish)

    if level == 'leicht':
        kind = random.choice(['tippen', 'plus'])
        timeout = 12
    elif level == 'mittel':
        kind = random.choice(['mal', 'dreher'])
        timeout = 11
    else:
        kind = random.choice(['dreher', 'folge', 'mal'])
        timeout = 9

    if kind == 'tippen':
        wort = random.choice(_WORDS)
        return {'prompt': f'Schreib schnell **{wort}**!', 'answer': wort, 'timeout': timeout}

    if kind == 'plus':
        a, b = random.randint(3, 19), random.randint(3, 19)
        return {'prompt': f'Schnell: **{a} + {b} = ?**', 'answer': str(a + b), 'timeout': timeout}

    if kind == 'mal':
        a, b = random.randint(3, 12), random.randint(3, 12)
        return {'prompt': f'Schnell: **{a} × {b} = ?**', 'answer': str(a * b), 'timeout': timeout}

    if kind == 'dreher':
        wort = random.choice([w for w in _WORDS if len(w) >= 5])
        scrambled = list(wort)
        while ''.join(scrambled) == wort:
            random.shuffle(scrambled)
        return {'prompt': f'Entwirre das Wort: **{"".join(scrambled)}**',
                'answer': wort, 'timeout': timeout + 3}

    folge = ''.join(random.choice('abcdefgh') for _ in range(random.randint(4, 6)))
    return {'prompt': f'Tippe rückwärts: **{folge}**', 'answer': folge[::-1], 'timeout': timeout + 4}


def check_answer(challenge, text):
    return text.strip().lower() == challenge['answer'].lower()


# --------------------------------------------------------------------------- Angeln

def start_cast(user_id):
    """Beginnt einen Wurf. Gibt (ergebnis, fehler) zurück.

    ergebnis ist ein dict mit 'kind': 'fisch' | 'schrott' | 'schatz'.
    Bei 'fisch' liegt zusätzlich 'fish', 'kg' und 'challenge' dabei - der Fang
    zählt aber erst nach land_fish().
    """
    remaining = cooldown_remaining(user_id)
    if remaining > 0:
        return None, f'Ruhig Blut - noch {remaining:.0f}s, dann kannst du wieder auswerfen.'

    data = _load()
    player = _get_player(data, user_id)
    player['stats']['casts'] += 1
    rod_level = player['rod']
    bait = player['bait'] > 0
    if bait:
        player['bait'] -= 1
    _save(data)
    _last_cast[user_id] = time.monotonic()

    roll = random.random()
    if roll < JUNK_CHANCE:
        junk = random.choice(JUNK)
        data = _load()
        _get_player(data, user_id)['stats']['junk'] += 1
        _save(data)
        return {'kind': 'schrott', 'junk': junk, 'bait_used': bait}, None

    if roll < JUNK_CHANCE + TREASURE_CHANCE:
        coins = random.randint(*TREASURE_COINS)
        data = _load()
        p = _get_player(data, user_id)
        p['balance'] += coins
        p['stats']['treasure'] += 1
        p['stats']['earned'] += coins
        _save(data)
        return {'kind': 'schatz', 'coins': coins, 'bait_used': bait}, None

    pool = [f for f in FISH if f['min_rod'] <= rod_level]
    weights = []
    for f in pool:
        w = f['weight']
        if bait and f['weight'] < 4:
            w *= BAIT_RARE_BOOST
        weights.append(w)
    fish = random.choices(pool, weights=weights, k=1)[0]

    lo, hi = fish['kg']
    kg = round(random.uniform(lo, hi), 2)

    return {
        'kind': 'fisch',
        'fish': fish,
        'kg': kg,
        'bait_used': bait,
        'challenge': make_challenge(fish),
    }, None


def value_for(fish, kg):
    """Wert skaliert mit dem Gewicht: Durchschnitt = Basiswert."""
    lo, hi = fish['kg']
    mid = (lo + hi) / 2
    factor = kg / mid if mid else 1
    return max(1, round(fish['value'] * factor))


def land_fish(user_id, fish, kg):
    """Fisch wirklich einsacken. Gibt (wert, ist_rekord) zurück."""
    data = _load()
    player = _get_player(data, user_id)
    inv = player['inventory']
    inv[fish['name']] = inv.get(fish['name'], 0) + 1
    player['stats']['caught'] += 1

    record = False
    best = player['records'].get(fish['name'])
    if best is None or kg > best:
        player['records'][fish['name']] = kg
        record = best is not None

    _save(data)
    return value_for(fish, kg), record


def record_escape(user_id):
    data = _load()
    _get_player(data, user_id)['stats']['escaped'] += 1
    _save(data)


# --------------------------------------------------------------------------- Rest

def inventory_text(user_id):
    data = _load()
    player = _get_player(data, user_id)
    inv = player['inventory']
    if not inv:
        return 'Dein Inventar ist leer. Zeit zum Angeln! (`$angeln`)'
    lookup = {f['name']: f for f in FISH}
    lines = []
    total = 0
    for name, count in sorted(inv.items(), key=lambda kv: -lookup.get(kv[0], {}).get('value', 0)):
        fish = lookup.get(name)
        emoji = fish['emoji'] if fish else '🐟'
        wert = (fish['value'] if fish else 0) * count
        total += wert
        lines.append(f'{emoji} {name} x{count} ({wert} Coins)')
    lines.append('')
    lines.append(f'Grundwert gesamt: ~{total} Coins')
    return 'Dein Inventar:\n' + '\n'.join(lines)


def sell(user_id, fish_name=None):
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
        player['stats']['earned'] += earned
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
    player['stats']['earned'] += earned
    _save(data)
    return earned, [f'{match} x{count} -> {earned} Coins']


def balance(user_id):
    return _get_player(_load(), user_id)['balance']


def shop_text(user_id):
    data = _load()
    player = _get_player(data, user_id)
    current = player['rod']
    lines = [
        f'Aktuelle Rute: **{rod_name(current)}** (Level {current})',
        f'Guthaben: {player["balance"]} Coins | Köder: {player["bait"]}',
        '',
    ]
    for level, info in RODS.items():
        if level < current:
            lines.append(f'~~Level {level}: {info["name"]}~~')
        elif level == current:
            lines.append(f'**Level {level}: {info["name"]} (aktuell)**')
        else:
            unlocks = [f['name'] for f in FISH if f['min_rod'] == level]
            extra = f' — neu: {", ".join(unlocks)}' if unlocks else ''
            lines.append(f'Level {level}: {info["name"]} — {info["cost"]} Coins{extra}')
    lines += ['', f'`$rute` = nächstes Upgrade | `$köder` = Köder kaufen ({BAIT_COST} Coins)']
    return '\n'.join(lines)


def upgrade_rod(user_id):
    data = _load()
    player = _get_player(data, user_id)
    current = player['rod']

    if current >= MAX_ROD_LEVEL:
        return False, f'Du hast schon die beste Rute ({rod_name(current)}).'

    next_level = current + 1
    cost = RODS[next_level]['cost']
    if player['balance'] < cost:
        return False, (f'Die {RODS[next_level]["name"]} kostet {cost} Coins, '
                       f'dir fehlen noch {cost - player["balance"]}.')

    player['balance'] -= cost
    player['rod'] = next_level
    _save(data)
    return True, f'Glückwunsch! Du angelst jetzt mit der **{RODS[next_level]["name"]}** (Level {next_level}).'


def buy_bait(user_id, amount=1):
    data = _load()
    player = _get_player(data, user_id)
    cost = BAIT_COST * amount
    if player['balance'] < cost:
        return False, f'{amount} Köder kosten {cost} Coins, du hast nur {player["balance"]}.'
    player['balance'] -= cost
    player['bait'] += amount
    _save(data)
    return True, (f'{amount} Köder gekauft ({cost} Coins). Vorrat: {player["bait"]}. '
                  'Köder erhöhen die Chance auf seltene Fische beim nächsten Wurf.')


def daily(user_id):
    data = _load()
    player = _get_player(data, user_id)
    today = date.today().isoformat()
    if player['last_daily'] == today:
        return False, 'Deinen Tagesbonus hast du heute schon abgeholt. Morgen wieder!'
    player['last_daily'] = today
    player['balance'] += DAILY_BONUS
    player['stats']['earned'] += DAILY_BONUS
    _save(data)
    return True, f'Tagesbonus: +{DAILY_BONUS} Coins. Guthaben: {player["balance"]}.'


def stats_text(user_id):
    player = _get_player(_load(), user_id)
    s = player['stats']
    versuche = s['caught'] + s['escaped']
    quote = f'{100 * s["caught"] / versuche:.0f}%' if versuche else '—'
    return '\n'.join([
        '**Deine Statistik**',
        f'Würfe: {s["casts"]}',
        f'Gefangen: {s["caught"]} | Entwischt: {s["escaped"]} (Trefferquote {quote})',
        f'Schrott: {s["junk"]} | Schätze: {s["treasure"]}',
        f'Insgesamt verdient: {s["earned"]} Coins',
        f'Rute: {rod_name(player["rod"])} (Level {player["rod"]})',
    ])


def records_text(user_id):
    player = _get_player(_load(), user_id)
    rec = player['records']
    if not rec:
        return 'Noch keine Rekorde. Fang erst mal was! (`$angeln`)'
    lookup = {f['name']: f for f in FISH}
    lines = []
    for name, kg in sorted(rec.items(), key=lambda kv: -kv[1]):
        emoji = lookup.get(name, {}).get('emoji', '🐟')
        lines.append(f'{emoji} {name}: **{kg} kg**')
    return '**Deine Rekorde**\n' + '\n'.join(lines)


def leaderboard_text(name_lookup, limit=10):
    """name_lookup: callable(user_id_str) -> Anzeigename oder None."""
    data = _load()
    rows = []
    for uid, player in data.items():
        stats = player.get('stats', {})
        rows.append((stats.get('earned', 0), player.get('balance', 0),
                     player.get('rod', 1), uid))
    if not rows:
        return 'Noch keine Angler unterwegs. Sei der Erste mit `$angeln`!'
    rows.sort(reverse=True)
    medals = ['🥇', '🥈', '🥉']
    lines = []
    for i, (earned, bal, rod, uid) in enumerate(rows[:limit]):
        who = name_lookup(uid) or f'Unbekannt ({uid})'
        prefix = medals[i] if i < len(medals) else f'{i + 1}.'
        lines.append(f'{prefix} **{who}** — {earned} Coins verdient, {rod_name(rod)}')
    return '**Rangliste**\n' + '\n'.join(lines)
