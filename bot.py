import os, re
from pathlib import Path

import discord
import random
from dotenv import load_dotenv
from joke import get_random_joke
from foid_detecter import name_gender_classifier

load_dotenv(Path(__file__).parent / '.env')


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def clean_username(raw_name: str) -> str:
    match = re.match(r"[A-Za-z]+", raw_name)
    return match.group(0) if match else raw_name

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
        if joke['type'] == 'twopart':
            await message.channel.send(f"{joke['setup']}\n||{joke['delivery']}||")
        else:
            await message.channel.send(joke['joke'])

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
    
client.run(os.environ["DISCORD_TOKEN"])
