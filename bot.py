import asyncio
import os, re
from pathlib import Path

import discord
import random
from dotenv import load_dotenv
from joke import get_random_joke
from foid_detecter import name_gender_classifier
import fishing

load_dotenv(Path(__file__).parent / '.env')

# relativ zum Skript, nicht zum Arbeitsverzeichnis: sonst startet der Bot nur,
# wenn er aus genau diesem Ordner heraus aufgerufen wird
screenshot_path = Path(__file__).parent / 'pictures'

# fehlt der Ordner, soll $picture "keine Bilder gefunden" sagen - nicht der
# ganze Bot beim Import abstuerzen
screenshots = ([f.name for f in screenshot_path.iterdir() if f.is_file()]
               if screenshot_path.is_dir() else [])



intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def clean_username(raw_name: str) -> str:
    match = re.match(r"[A-Za-z]+", raw_name)
    return match.group(0) if match else raw_name
REROLL_EMOJI = '🔄'
JOKE_FETCH_FAILED = "Couldn't fetch a joke right now, try again later."

# Command name -> short description, used to build the $help output.
COMMANDS = {
    '$joke': 'Sends a random programming joke (react with 🔄 to reroll)',
    '$angeln': 'Wirft die Angel aus - beim Anbiss musst du eine Aufgabe lösen',
    '$inventar': 'Zeigt deine gefangenen Fische',
    '$verkaufen': 'Verkauft alle Fische, oder $verkaufen <fisch> für einen bestimmten',
    '$shop': 'Zeigt die Rutenstufen und was sie kosten/freischalten',
    '$rute': 'Kauft das nächste Rutenupgrade, wenn genug Coins da sind',
    '$köder': 'Kauft einen Köder - bessere Chance auf seltene Fische',
    '$kontostand': 'Zeigt deinen Coins-Kontostand',
    '$täglich': 'Holt den Tagesbonus ab',
    '$statistik': 'Zeigt deine Angel-Statistik',
    '$rekorde': 'Zeigt deine größten Fänge',
    '$rangliste': 'Wer hat am meisten verdient?',
    '$michi': 'ist ein Idiot',
    '$lorenz': 'ist behindert',
    '$david': 'mag keine Frauen',
    '$eva': 'Foid',
    '$gender': 'Rät dein Geschlecht anhand deines Anzeigenamens',
    '$smile': 'Spammt :)',
    '$help': 'Shows this list of commands',
}

# Message IDs of joke messages posted by the bot, so we know which
# messages are eligible to be rerolled via the 🔄 reaction.
joke_messages = set()

# User-IDs mit laufendem Wurf - verhindert, dass jemand fünf Angeln
# gleichzeitig auswirft und alle Aufgaben mit einer Antwort löst.
active_casts = set()


async def handle_fishing(message):
    """Ein kompletter Wurf: auswerfen, warten, Anbiss, Aufgabe, Fang."""
    user_id = message.author.id
    if user_id in active_casts:
        await message.channel.send('Du hast schon eine Angel im Wasser!')
        return

    result, error = fishing.start_cast(user_id)
    if error:
        await message.channel.send(error)
        return

    active_casts.add(user_id)
    try:
        koeder = ' (mit Köder 🪱)' if result.get('bait_used') else ''
        await message.channel.send(
            f'{message.author.mention} wirft die Angel aus{koeder}... 🎣'
        )
        await asyncio.sleep(random.uniform(2.0, 5.0))

        if result['kind'] == 'schrott':
            junk = result['junk']
            await message.channel.send(
                f'Du ziehst... **{junk["name"]}** {junk["emoji"]} aus dem Wasser. Grandios.'
            )
            return

        if result['kind'] == 'schatz':
            await message.channel.send(
                f'💰 Eine **Schatztruhe**! Darin: **{result["coins"]} Coins**.'
            )
            return

        fish = result['fish']
        challenge = result['challenge']
        await message.channel.send(
            f'❗ **ANBISS!** Etwas Schweres hängt dran!\n'
            f'{challenge["prompt"]}\n'
            f'*(du hast {challenge["timeout"]} Sekunden)*'
        )

        def check(m):
            return m.author.id == user_id and m.channel.id == message.channel.id

        try:
            answer = await client.wait_for('message', check=check, timeout=challenge['timeout'])
        except asyncio.TimeoutError:
            fishing.record_escape(user_id)
            await message.channel.send(
                f'Zu langsam! Der **{fish["name"]}** {fish["emoji"]} reißt sich los und ist weg. 💨'
            )
            return

        if not fishing.check_answer(challenge, answer.content):
            fishing.record_escape(user_id)
            await message.channel.send(
                f'Falsch! Die Leine reißt, der **{fish["name"]}** {fish["emoji"]} entkommt. 💨\n'
                f'*(richtig wäre gewesen: {challenge["answer"]})*'
            )
            return

        wert, ist_rekord = fishing.land_fish(user_id, fish, result['kg'])
        text = (
            f'🎉 {message.author.mention} landet einen **{fish["name"]}** {fish["emoji"]}!\n'
            f'Gewicht: **{result["kg"]} kg** — Wert: **{wert} Coins**'
        )
        if ist_rekord:
            text += '\n🏆 **Neuer persönlicher Rekord!**'
        await message.channel.send(text)
    finally:
        active_casts.discard(user_id)


def display_name_for(guild, user_id_str):
    """Für die Rangliste: ID -> Anzeigename, wenn der User im Server ist."""
    if guild is None:
        return None
    member = guild.get_member(int(user_id_str))
    return member.display_name if member else None


def format_joke(joke):
    if joke['type'] == 'twopart':
        return f"{joke['setup']}\n||{joke['delivery']}||"
    return joke['joke']


def format_help():
    lines = [f'{name} - {description}' for name, description in COMMANDS.items()]
    return 'Available commands:\n' + '\n'.join(lines)


@client.event
async def on_ready():
    await client.user.edit(username='bottiger bot')
    print(f'logged in as{client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$joke'):
        joke = get_random_joke()
        if joke is None:
            await message.channel.send(JOKE_FETCH_FAILED)
            return
        sent = await message.channel.send(format_joke(joke))
        joke_messages.add(sent.id)
        await sent.add_reaction(REROLL_EMOJI)

    elif message.content.startswith('$angeln'):
        await handle_fishing(message)

    elif message.content.startswith('$inventar'):
        await message.channel.send(fishing.inventory_text(message.author.id))

    elif message.content.startswith('$verkaufen'):
        rest = message.content[len('$verkaufen'):].strip()
        fish_name = rest if rest else None
        earned, lines = fishing.sell(message.author.id, fish_name)
        if lines is None:
            if fish_name:
                await message.channel.send(f'Du hast keinen "{fish_name}" zum Verkaufen.')
            else:
                await message.channel.send('Du hast nichts zum Verkaufen. Erst angeln mit `$angeln`!')
            return
        await message.channel.send(
            'Verkauft:\n' + '\n'.join(lines) + f'\n\nGesamt: +{earned} Coins'
        )

    elif message.content.startswith('$shop'):
        await message.channel.send(fishing.shop_text(message.author.id))

    elif message.content.startswith('$rute'):
        success, text = fishing.upgrade_rod(message.author.id)
        await message.channel.send(text)

    elif message.content.startswith('$köder') or message.content.startswith('$koeder'):
        rest = message.content.split(maxsplit=1)
        try:
            amount = max(1, min(50, int(rest[1]))) if len(rest) > 1 else 1
        except ValueError:
            amount = 1
        _, text = fishing.buy_bait(message.author.id, amount)
        await message.channel.send(text)

    elif message.content.startswith('$kontostand'):
        await message.channel.send(
            f'{message.author.mention} hat {fishing.balance(message.author.id)} Coins.'
        )

    elif message.content.startswith('$täglich') or message.content.startswith('$taeglich'):
        _, text = fishing.daily(message.author.id)
        await message.channel.send(text)

    elif message.content.startswith('$statistik'):
        await message.channel.send(fishing.stats_text(message.author.id))

    elif message.content.startswith('$rekorde'):
        await message.channel.send(fishing.records_text(message.author.id))

    elif message.content.startswith('$rangliste'):
        await message.channel.send(
            fishing.leaderboard_text(lambda uid: display_name_for(message.guild, uid))
        )

    elif message.content.startswith('$michi'):
        await message.channel.send("ist ein Idiot")
    elif message.content.startswith('$lorenz'):
        await message.channel.send("ist behindert")
    elif message.content.startswith('$david'):
        await message.channel.send("mag keine Frauen")
    elif message.content.startswith('$eva'):
        for _ in range(10):
            await message.channel.send("Foid! Foid! Foid!")
    elif message.content.startswith('$gender'):
        raw_name = message.author.display_name
        name = clean_username(raw_name)
        gender = name_gender_classifier(name)

        if gender == "female":
            await message.channel.send("Scheiß Foid")
        else:
            await message.channel.send("Geiler Typ")

        await message.channel.send("mag keine Frauen")
    elif message.content.startswith('$help'):
        await message.channel.send(format_help())
    elif message.content.startswith('$picture'):
        if screenshots:
            random_screenshot = random.choice(screenshots)

            path_screenshot = screenshot_path / random_screenshot
            screenshot = discord.File(path_screenshot)
            await message.channel.send(file=screenshot)
        else:
            await message.channel.send('keine Bilder gefunden')

    elif message.content.startswith("$smile"):
        for i in range(10):
            await message.channel.send(":)")


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return

    if str(reaction.emoji) != REROLL_EMOJI:
        return

    message = reaction.message
    if message.author != client.user or message.id not in joke_messages:
        return

    joke = get_random_joke()
    if joke is None:
        try:
            await reaction.remove(user)
        except discord.HTTPException:
            pass
        return
    await message.edit(content=format_joke(joke))
    try:
        await reaction.remove(user)
    except discord.HTTPException:
        pass

client.run(os.environ["DISCORD_TOKEN"])
