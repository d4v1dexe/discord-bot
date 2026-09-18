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

@client.event
async def on_ready():
    await client.user.edit(username='bottiger bot')
    print(f'logged in as{client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$michi'):
        #michi ding
        return

@client.event
async def on_message(message):
    if message.author == client.user:
        return 
    if message.content.startswith('$joke'):
        joke = get_random_joke()
        await message.channel.send(f"{joke['setup']}\n||{joke['punchline']}||")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('$michi'):
        await message.channel.send("ist ein Idiot")

client.run(os.environ["DISCORD_TOKEN"])
