import os
from pathlib import Path

import discord
import random
from dotenv import load_dotenv
from joke import get_random_joke

load_dotenv(Path(__file__).parent / '.env')


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

REROLL_EMOJI = '🔄'
JOKE_FETCH_FAILED = "Couldn't fetch a joke right now, try again later."

# Message IDs of joke messages posted by the bot, so we know which
# messages are eligible to be rerolled via the 🔄 reaction.
joke_messages = set()


def format_joke(joke):
    if joke['type'] == 'twopart':
        return f"{joke['setup']}\n||{joke['delivery']}||"
    return joke['joke']


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

    elif message.content.startswith('$michi'):
        await message.channel.send("ist ein Idiot")
    elif message.content.startswith('$lorenz'):
        await message.channel.send("ist behindert")
    elif message.content.startswith('$david'):
        await message.channel.send("mag keine Frauen")    

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
