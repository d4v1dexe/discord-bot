import os
from pathlib import Path

import discord
import random
from dotenv import load_dotenv
from joke import get_random_joke
import fishing

load_dotenv(Path(__file__).parent / '.env')


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

REROLL_EMOJI = '🔄'
JOKE_FETCH_FAILED = "Couldn't fetch a joke right now, try again later."

# Command name -> short description, used to build the $help output.
COMMANDS = {
    '$joke': 'Sends a random programming joke (react with 🔄 to reroll)',
    '$angeln': 'Wirft die Angel aus und fängt (vielleicht) einen Fisch',
    '$inventar': 'Zeigt deine gefangenen Fische',
    '$verkaufen': 'Verkauft alle Fische, oder $verkaufen <fisch> für einen bestimmten',
    '$shop': 'Zeigt die Rutenstufen und was sie kosten/freischalten',
    '$rute': 'Kauft das nächste Rutenupgrade, wenn genug Coins da sind',
    '$kontostand': 'Zeigt deinen Coins-Kontostand',
    '$michi': 'ist ein Idiot',
    '$lorenz': 'ist behindert',
    '$david': 'mag keine Frauen',
    '$help': 'Shows this list of commands',
}

# Message IDs of joke messages posted by the bot, so we know which
# messages are eligible to be rerolled via the 🔄 reaction.
joke_messages = set()


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
        fish, error = fishing.cast(message.author.id)
        if error:
            await message.channel.send(error)
            return
        await message.channel.send(
            f'{message.author.mention} hat einen **{fish["name"]}** {fish["emoji"]} gefangen! '
            f'(Wert: {fish["value"]} Coins, verkaufen mit `$verkaufen`)'
        )

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

    elif message.content.startswith('$kontostand'):
        await message.channel.send(
            f'{message.author.mention} hat {fishing.balance(message.author.id)} Coins.'
        )

    elif message.content.startswith('$michi'):
        await message.channel.send("ist ein Idiot")
    elif message.content.startswith('$lorenz'):
        await message.channel.send("ist behindert")
    elif message.content.startswith('$david'):
        await message.channel.send("mag keine Frauen")
    elif message.content.startswith('$help'):
        await message.channel.send(format_help())

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
